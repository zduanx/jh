# Lambda Response Streaming & Client Disconnect

**Context**: Phase 6 chat runs on a Lambda Function URL with response streaming
(`RESPONSE_STREAM`). We wanted to abort a turn (and stop billing) when the user
disconnects mid-stream. It works locally but NOT on Lambda — this documents why
and the real options.

---

## The Symptom

| Environment | Interrupt mid-stream (kill client) | Result |
|-------------|-----------------------------------|--------|
| **Local Node server** | `res.on('close')` fires immediately | turn aborts, partial saved (`interrupted: true`) |
| **AWS Lambda Function URL** | nothing fires; `responseStream.write()` does NOT throw | turn runs to completion, full answer saved, **billed for full duration** |

**Measured (CloudWatch):** an interrupted ~45s turn billed **44,977 ms** — the
full turn ran even though the client left at ~47s.

---

## Why It Differs (the mechanism)

**Local:** the Node `res` (ServerResponse) is attached to the *real TCP socket*
to the client. Client disconnects → socket closes → `res.on('close')` fires.
Your code holds the actual client connection.

**Lambda:** your `responseStream` is NOT connected to the client. The path is:

```
client ──TCP──► AWS Function URL infra ──internal──► your Lambda's responseStream
```

`responseStream` writes into **AWS's buffering layer**, not the client socket.
When the client disconnects from *AWS*, AWS keeps accepting your writes (buffers/
discards them) and does **not** reliably propagate the disconnect back to your
function. So `write()` doesn't throw and `on('close')` doesn't fire — the
"client left" signal never reaches your code.

> Analogy: locally you're on the phone with the client (hang-up → dial tone).
> On Lambda you dictate to a secretary (AWS) who relays to the client; the client
> hangs up on the secretary, who keeps taking your dictation and never tells you.

---

## What AWS Officially Says

From the AWS docs on response streaming:

> "Streamed responses are not interrupted or stopped when the invoking client
> connection is broken, and customers will be billed for the full function
> duration."

So: **the function is NOT auto-interrupted on disconnect, and you pay for the
full run.** This is by design, not a bug.

Detection is *theoretically possible* — the low-level streaming primitive
(`send_data` in the Rust runtime) returns an error on client disconnect — but at
the Node `responseStream.write()` level it is **unreliable/lagging** (buffering
means the error may surface late, only on a later flush, or in a metric but not
in logs). Our test caught `write()` throwing; it never fired within the window.

---

## Options (honest)

| Approach | Reliable on Lambda? | Notes |
|----------|--------------------|-------|
| `responseStream.write()` throws | ⚠️ unreliable / lagging | AWS says write-error *can* signal it, but buffering makes it undependable (didn't fire in our test) |
| Lower-level `send_data` error | ⚠️ runtime-dependent | Clean in Rust runtime; Node's wrapper less so |
| **Explicit client-cancel API** | ✅ reliable | Client sends `POST /cancel`; the running turn polls a Redis flag and stops. **This is how ChatGPT's "stop" works** — it doesn't rely on disconnect detection. Handles *intentional* stop, not network drops/tab-close. |
| Shorter turn budget | ✅ (mitigation) | Caps wasted billing, doesn't detect disconnect |
| **Long-running server** (container) | ✅ reliable | Holds the real client socket → disconnect detected (the local behavior). The only way to get true socket-disconnect abort — but abandons serverless |

---

## Decision (Phase 6)

- **Accept the limitation.** On Lambda, an interrupted turn runs to completion;
  the **120s turn budget caps worst-case wasted billing**. At free-tier scale the
  cost is negligible.
- Keep the defensive `write()`-error check (it works locally and is harmless on
  Lambda), but do **not** rely on it for Lambda abort.
- **Reliable abort needs either** an explicit client-cancel API (the ChatGPT
  pattern — a candidate if interrupt-cost matters) **or** a long-running server.
- Documented as a deliberate trade of the serverless choice (see ADR-025/028).

---

## Key Takeaways

1. **On Lambda streaming your code talks to AWS infra, not the client** — so
   client disconnect is not surfaced reliably. Locally you hold the real socket,
   so it is.
2. **AWS bills the full function duration even if the client disconnected** —
   bound it with a conservative timeout / turn budget.
3. **Reliable "stop" in production chat is an explicit cancel signal**, not
   socket-disconnect detection. Disconnect-abort only works where you hold the
   real socket (a long-running server).

---

## References

- [Response streaming for Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html)
- [Invoking a response streaming function via Function URLs](https://docs.aws.amazon.com/lambda/latest/dg/config-rs-invoke-furls.html)
- [AWS re:Post — Node.js Lambda streaming, await after response stream error](https://repost.aws/questions/QUjJXBJ_xZTCGznExwX1gH8A/node-js-lambda-streaming-await-after-response-stream-error)
- [AWS re:Post — Lambda response stream error in metric but nothing in logs](https://repost.aws/questions/QU-KsAjAhERriMymeY2vYwgQ/lambda-with-response-stream-showing-an-error-in-metric-but-nothing-in-logs)
