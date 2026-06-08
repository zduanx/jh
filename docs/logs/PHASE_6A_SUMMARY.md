# Phase 6A: Chat Streaming Runtime + >30s Proof (Mocked AI)

**Status**: ✅ Completed
**Date**: June 5, 2026
**Goal**: Stand up a Node.js Lambda Function URL that streams a ~50s mock turn, proving token streaming works for a request **>30s** — with no Redis and no AI.

> **Result:** proven on AWS — a single request streamed for **46s** through the deployed Function URL (`jh-chat-stack`), with events arriving incrementally **past the 30s mark, no cutoff**. This is exactly what API Gateway + Mangum cannot do (buffered burst). [ADR-025](../architecture/DECISIONS.md#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming) validated empirically.

---

## Overview

Phase 6A builds the **streaming runtime** for the chatbox and proves the riskiest assumption of the whole chat feature: that a serverless backend can stream a response for **longer than 30s**. The existing API Gateway + Mangum path cannot (it buffers the entire response and caps at 30s — see [ADR-025](../architecture/DECISIONS.md#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming) and the timestamped-curl evidence captured there).

The deliverable is a **Node.js Lambda behind a Function URL** in `RESPONSE_STREAM` mode that runs a **mock 50s turn**: it streams `thinking`/`intermediate` events for ~40s, then streams a hardcoded final answer token-by-token in the last ~10s. There is **no AI and no persistence** in 6A — messages are hardcoded. The point is the *pipe*, not the content.

6A is built and tested **headless** (no frontend): `curl -N` is the SSE client stand-in, and the mock is **observable** (it echoes what it received) so the plumbing is verifiable from the command line.

**Included in this phase**:
- Node.js Lambda + Function URL (`RESPONSE_STREAM`).
- Mock 50s turn streaming `step` events then token-streamed final answer (unified `step` protocol — includes the initial "thinking" state).
- The **SSE event protocol** (`step`/`token`/`done`/`error`; documented in [API_DESIGN.md](../architecture/API_DESIGN.md)).
- The **seam**: `generateResponse(sessionId, history) → async stream of events` (mock now, real agent in Phase 7).
- **JWT auth**: verify the backend's JWT (shared `SECRET_KEY`, HS256, `jsonwebtoken`) via `Authorization: Bearer` before streaming; 401 if missing/invalid. Function URL is `AuthType: NONE` (public), so the handler enforces auth itself.
- **Shared logic extraction**: `sse.js`, `generateResponse.js`, `streamTurn.js`, `auth.js` reused by both transports (`local.js`, `handler.js`).
- **Generator scripts** (`chat/scripts/generate_{template,samconfig}.py`) producing `template.yaml` + `samconfig.toml` from `.sam-config` + `.env.local` (mirrors backend; secrets stay out of git).
- **dev.sh tooling**: `jbenode`/`jbenode-bg`/`jkill-benode`, `jchat-health`, `jchat-token`, `jchat-test [--aws]` (auto-generates a JWT), `jpushchat` (own stack deploy), `jready`/`jstatus` updated.
- Backend interruption test ([ADR-028](../architecture/DECISIONS.md#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts)): client disconnect aborts the invocation.
- **2-minute turn budget**: graceful `error` event before the 5-min Lambda hard timeout.

**Explicitly excluded**:
- Redis / session / history → Phase 6B.
- Frontend widget → Phase 6C.
- All AI logic (agent loop, MCP, LLM, tools) → Phase 7.

---

## Key Achievements (planned)

### 1. Node.js Lambda Function URL (streaming)
- `RESPONSE_STREAM` invoke mode via `awslambda.streamifyResponse` (first-class Node streaming).
- Own JWT verification + CORS in the handler (bypasses API Gateway).
- Reference: [ADR-025](../architecture/DECISIONS.md#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming)

### 2. Mock 50s turn + observable mock
- Streams `thinking`/`intermediate` for ~40s (with sleeps), then token-streams a hardcoded answer for ~10s.
- Mock echoes received input (`thinking: "loaded N prior messages for session X"`) so plumbing is verifiable headless.

### 3. The `generateResponse` seam
- `generateResponse(sessionId, history) → async stream of {thinking|intermediate|token|done}`.
- Mock implements it in 6A; Phase 7's real agent implements the same signature.

### 4. SSE event protocol
- `thinking` / `intermediate` / `token` / `done` / `error`.
- Documented in [API_DESIGN.md](../architecture/API_DESIGN.md) (API contract, not an ADR).

### 5. dev.sh tooling
- Command(s) to run the Node chat service locally (mirroring `jbe`/`jbe-bg`), e.g. `jchat` / `jchat-bg`.
- (Optional) `jchat-test` running the timestamped multi-turn curl.

---

## API / Endpoints

`POST <function-url>/chat` (Function URL, streamed `text/event-stream`). Full contract: [API_DESIGN.md §15](../architecture/API_DESIGN.md). In 6A the request `message` is accepted but the response is a mock; `session_id` is accepted but not yet persisted (Phase 6B).

---

## Highlights

### The >30s proof (the whole point of 6A)
The decisive test is the **inverse** of the ingestion buffering finding: a timestamped `curl -N` should show events arriving **incrementally across ~50s** (NOT bunched in a burst at close), with **events past T+30s arriving normally** (no 504, no cutoff).

### Two-buffer awareness
A Function URL removes the API Gateway buffer; Node (not Mangum) removes the adapter buffer. Both are required for real streaming — Python/Mangum on a Function URL would still buffer. See [ADR-025](../architecture/DECISIONS.md#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming).

---

## Testing & Validation

**Local (verified via `jchat-test` / curl):**
- [x] Timestamped stream: `step` events spread across ~40s; `token`s in the last ~10s; `done` at ~50s. (Local proof; events flow past the 30s mark.)
- [x] Auth: no token → 401; valid JWT → streams; invalid token → 401; `/health` open.
- [x] Interruption: client disconnect mid-stream → server logs abort, stops producing ([ADR-028](../architecture/DECISIONS.md#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts)).
- [x] Turn budget: exceeding the budget emits a graceful `error` event and ends.
- [x] `jbenode` / `jchat-test` run the service locally and stream correctly.

**Deployed (verified via `jchat-test --aws` against `jh-chat-stack`):**
- [x] Timestamped stream: events arrived incrementally over **46s** — `step` events at T+0, +5, +10, +15, +20, +25, **+30, +35** (past 30s, no cutoff), `token`s T+40s, `done` T+44s. **The >30s proof through AWS.**
- [x] First event < 1s; auth enforced (token auto-generated + accepted; a 401 would have blocked the stream).
- [x] `jchat-test --aws` auto-resolved the Function URL from the stack output and auto-generated the JWT.

**Automated:** future — repeatable timestamped-curl smoke test.

---

## Metrics

| Metric | Target | Actual (AWS) |
|--------|--------|--------------|
| Time to first `step` event | < 1s | < 1s ✅ |
| Total mock turn duration | ~50s | 46s ✅ |
| Events past 30s | arrive normally (no cutoff) | streamed at T+30s, +35s, no cutoff ✅ |
| Final answer streamed in | last ~10s | T+40s → T+44s ✅ |
| Lambda timeout (hard) | — | 300s (5 min) |
| App turn budget (graceful) | — | 120s (2 min) |

**Deployed:** stack `jh-chat-stack` (us-east-1) · function `JobHuntChat` (Node.js 22) · Function URL (`RESPONSE_STREAM`, `AuthType: NONE` + in-handler JWT).

---

## Next Steps → Phase 6B

Add **Upstash Redis + session state**: replace 6A's hardcoded messages with real history read/write keyed by `sessionId`, recording the full conversation (user + mock assistant).

---

## File Structure

```
chat/ (new — Node.js service, own SAM stack: jh-chat-stack)
├── handler.js            # AWS transport: Function URL handler (streamifyResponse) + auth
├── local.js              # local-dev transport: Node http server + auth + .env.local loader
├── streamTurn.js         # SHARED turn loop: budget (2min) + abort + error handling
├── generateResponse.js   # SHARED the seam: mock 50s turn (real agent in Phase 7)
├── sse.js                # SHARED SSE frame formatting + sleep
├── auth.js               # SHARED JWT verify (jsonwebtoken, backend SECRET_KEY)
├── package.json          # deps: jsonwebtoken
├── template.yaml         # GENERATED — SAM (Function URL, RESPONSE_STREAM, Timeout 300s)
├── .sam-config           # committed — generator source (stack, runtime, CORS, static env)
├── .env.example          # committed — env var docs (backend .env.local format)
└── scripts/
    ├── generate_template.py    # .sam-config (+ .env.local) → template.yaml
    └── generate_samconfig.py   # .sam-config (+ .env.local secrets) → samconfig.toml

# gitignored: chat/samconfig.toml, chat/.env.local, chat/server.log, chat/node_modules/

dev.sh                    # jbenode(-bg), jkill-benode, jchat-health, jchat-token,
                          # jchat-test [--aws], jpushchat; jready/jstatus updated
docs/architecture/API_DESIGN.md   # /chat endpoint + SSE protocol (added)
```

---

## Key Learnings

- **Two buffers, not one.** Real streaming required removing *both* the API Gateway buffer (via Function URL) *and* the Mangum/adapter buffer (via Node `streamifyResponse`, not Python/Mangum). The 46s AWS proof is the empirical contrast to the buffered-burst ingestion SSE (Phase 2H).
- **ES module env-load ordering bug.** `auth.js` read `process.env.SECRET_KEY` at module-load time, but ESM imports are hoisted/evaluated *before* the importer's body — so it ran before `local.js`'s `loadEnvFile()`, capturing `undefined` (→ spurious 401). Fix: read env at **call time**. Caught by a failing valid-token test, isolated with a minimal repro.
- **Mock-behind-a-stable-seam.** Building the full transport + auth + streaming with a mock `generateResponse(sessionId, history)` proved the infra end-to-end before any AI. Phase 7 replaces only the seam's body.
- **Per-directory SAM isolation.** Separate `chat/` stack + generators (`cd chat` → `scripts/...`, scripts self-anchor via `__file__`) keep chat and backend deploys fully independent.

---

## References

**External Documentation**:
- [AWS Lambda response streaming](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html) — `RESPONSE_STREAM` / `streamifyResponse`
- [SSE EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

**Internal Documentation**:
- [ADR-025](../architecture/DECISIONS.md#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming) — runtime decision
- [ADR-028](../architecture/DECISIONS.md#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts) — interruption aborts invocation
- [PHASE_6B_SUMMARY.md](./PHASE_6B_SUMMARY.md), [PHASE_6C_SUMMARY.md](./PHASE_6C_SUMMARY.md)
