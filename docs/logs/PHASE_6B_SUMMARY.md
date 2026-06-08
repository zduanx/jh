# Phase 6B: Redis + Session State (Mocked AI)

**Status**: ✅ Completed
**Date**: June 6, 2026
**Goal**: Enable ephemeral Redis, wire the session identity, and record the full conversation (user asks + assistant responses) per turn — proving multi-turn persistence with the mock.

> **Result:** verified on AWS (`jh-chat-stack`) — multi-turn history reads/writes through Upstash Redis (`message_count` 0→2→4 across turns, "loaded N prior messages"), keyed `chat:{uid}:{sessionId}` with uid from the JWT, user-first/assistant-later saves, 1h sliding TTL, block compaction (every ~10 messages), and `--debug` before/after snapshots via the real `/session` endpoint. One platform limitation surfaced and documented (see Highlights): **Lambda does not propagate client disconnect**, so interrupt-abort works locally but not on Lambda — accepted, not fixed forward.

---

## Overview

Phase 6B adds the **state layer** on top of 6A's streaming runtime. The mock from 6A stays; what changes is that the backend now **reads and writes conversation history in Redis** instead of using hardcoded messages. This proves the entire real data path — session-keyed history, multi-turn continuity, refresh-safety — **before any AI exists**.

The store is **Upstash Redis** (free tier, HTTP-accessible, no VPC), used as the **single ephemeral source of truth** for a session, keyed by `sessionId` with a sliding TTL. The frontend (6C) will render only; the backend assembles history from Redis and passes it to the `generateResponse(sessionId, history)` seam. The mock still ignores history when generating its fake answer, but it **receives** real history (keeping the seam honest for Phase 7) and **reports** what it loaded (so the plumbing is verifiable headless).

**Included in this phase**:
- Upstash Redis enabled + client wired into the Node service.
- Frontend-generated `sessionId` accepted and used as the Redis key.
- Per-turn flow: write user message → read full history → call `generateResponse` → write assistant (mock) response.
- Redis storage schema (single JSON blob per session, sliding TTL).
- `jready` extended to check the Redis endpoint.

**Explicitly excluded**:
- Frontend widget → Phase 6C.
- All AI logic → Phase 7 (the mock stays; only the store becomes real).
- Tool-result cache is a **placeholder** (no real tools until Phase 7).

---

## Key Achievements

### 1. Upstash Redis enabled
- Free tier, HTTP/REST access (`@upstash/redis`) → reachable from Lambda **without VPC** setup.
- Reference: [ADR-027](../architecture/DECISIONS.md#adr-027-chat-state-store--ephemeral-redis-upstash)

### 2. Session identity wired
- Frontend-generated `sessionId` ([ADR-026](../architecture/DECISIONS.md#adr-026-chat-session-lifetime--identity--per-tab-ephemeral)) combined with the JWT `uid` to form the Redis key `chat:{uid}:{sessionId}` (uid from the verified token, not client-supplied).

### 3. Full conversation recorded (user-first / assistant-later)
- User message persisted **immediately** at turn start (definite fact, survives early failure); assistant response saved at turn end. Per-message, role-tagged ([ADR-031](../architecture/DECISIONS.md#adr-031-conversation-storage-in-redis--per-message-entries-in-a-single-json-blob)). Industry pattern.
- Multi-turn proven on AWS: turn N reads turns 1..N-1 from Redis.

### 4. Single source of truth
- LLM/mock input is assembled **backend-side from Redis** — one clean assembly point; no history in the frontend ([ADR-027](../architecture/DECISIONS.md#adr-027-chat-state-store--ephemeral-redis-upstash)).

### 5. Block (batch) compaction
- Messages accumulate to a high-water mark (`SUMMARIZE_AT=30`), then the oldest block is compressed down to `RECENT_KEEP=20` in one batch — NOT per-turn sliding. Keeps summarization (Phase 7 LLM call) infrequent and the cached prompt prefix stable. `summarizeOverflow` is a no-op stub in 6B (Phase 7 fills it).

### 6. Shared SSE transport (adapter pattern)
- `sseTransport.js`: `runTurn(stream, params)` + `adaptNodeRes(res)`. Both transports run the **same** turn logic over a uniform `StreamLike` interface — AWS passes `responseStream`, local passes `adaptNodeRes(res)`. Cannot drift.

### 7. Debug introspection endpoint
- `GET /session?session_id=...` returns the stored Redis blob via the **real production path** (verify JWT → uid → `getSession`). `jchat-test --debug` snapshots Redis before + after a turn.

### 8. dev.sh tooling
- `jready` checks Upstash reachability + chat-inclusive quick-start; `jchat-test --debug` Redis snapshots; `jchat-token`.

---

## Changes Since 6A

| Area | 6A | 6B |
|------|----|----|
| History | hardcoded `[]` | read/write Redis (`chat:{uid}:{sessionId}`, per-message blob) |
| Save | none | user-first (turn start) + assistant-later (turn end), `interrupted` flag |
| Context | empty | built from summary + recent messages (`buildContext`) |
| Compaction | n/a | block/batch at high-water mark (no per-turn summarization) |
| Transport | inline write loop per file | shared `runTurn` + `adaptNodeRes` (sseTransport.js) |
| Disconnect abort | local only | local works; **Lambda limitation found + documented** (see Highlights) |
| Endpoints | `/health`, `/chat` | + `GET /session` (debug) |
| Deps | jsonwebtoken | + `@upstash/redis` |
| New files | — | `redis.js`, `sseTransport.js` |

---

## Database / Storage Schema (Redis)

**Per-message entries in a single JSON blob**, keyed by authenticated user + session — see [ADR-031](../architecture/DECISIONS.md#adr-031-conversation-storage-in-redis--per-message-entries-in-a-single-json-blob). 2 commands/turn (one read, one write-with-TTL).

```
Key:   chat:{uid}:{sessionId}        // uid from the verified JWT (not client-supplied)
Value: {
  "message_count": 0,                // monotonic counter (industry's sequence_number); summarization trigger (P7)
  "summary": "",                     // rolling summary of compressed-out messages (Phase 7 fills; 6B stub: stays "")
  "messages": [                      // per-message, role-tagged, in order (LLM API-native shape)
    {"role": "user",      "content": "...", "ts": <ms>, "interrupted": false},
    {"role": "assistant", "content": "...", "ts": <ms>, "interrupted": false}   // mock content in P6
  ],
  "created_at": <ms>,
  "updated_at": <ms>
}
Read:  GET chat:{uid}:{sessionId}
Write: SET chat:{uid}:{sessionId} <json> EX 3600     // write + refresh sliding TTL in ONE command
TTL:   1 hour, SLIDING (re-set on each write). Short TTL (~10–30 min) while testing.
```

**Partial-saving** ([ADR-028](../architecture/DECISIONS.md#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts)): the assistant message is accumulated as it streams and saved in a `finally` block. A clean turn saves `interrupted: false`; an interrupted turn (disconnect/stop) saves the partial with `interrupted: true` (the ChatGPT-style behavior — partials are real conversation context). Best-effort: `finally` runs for graceful exits (break/return/throw); a hard process kill (Lambda 300s timeout) may skip it — the 120s turn budget makes that rare.

**6B policy (simple):** keep recent messages, leave `summary = ""`. Token-based summarization (compress oldest until under a token target, with output headroom) is **Phase 7** — placeholder hook in `streamTurn`.

**Tool-result cache (placeholder — Phase 7):**
```
Key:   chat:{uid}:{sessionId}:cache:{tool}:{argsHash}
TTL:   ~5 min
```

**Free-tier notes** ([ADR-027](../architecture/DECISIONS.md#adr-027-chat-state-store--ephemeral-redis-upstash)): Upstash free tier limits **commands/day (~10k)** and **storage (~256MB)**, **not TTL**. A **command** = one Redis op (GET/SET/…), not one request; `SET ... EX` is one command. At ~2 commands/turn, single-user dev usage is a few % of the limit. Estimated blob size ≈ ~30 KB (bounded), far under limits.

---

## Highlights

### Mock stays, store becomes real
6B changes only *where messages come from* — Redis instead of hardcode. The mock's generation logic is unchanged. This isolates "does persistence/multi-turn work" from "does the AI work" (Phase 7).

### Sliding TTL
TTL is re-set on every write, so an active conversation expires 1h after **last** activity, not after it began — an in-use chat never expires mid-conversation.

### Placeholder functions matching the future AI infra
`streamTurn` is structured with the **read → generate → save** shape the real agent will use, via functions whose signatures match the eventual AI infra. Where real logic exists in 6B, it's filled in (Redis read/write); where it's Phase 7, it's a clearly-marked stub:
- `getSession(uid, sessionId)` / `saveUserMessage` / `saveAssistantMessage` → **real** (Redis).
- `buildContext(session)` → **real** assembly of summary + messages (summary empty in 6B).
- `summarizeOverflow(...)` → **stub** (no-op in 6B; LLM summarization in Phase 7).
- `generateResponse(sessionId, history)` → still the **mock** seam (real agent in Phase 7), now receiving real history.

This keeps the turn pipeline shaped like production so Phase 7 fills bodies without restructuring.

### Lambda does NOT propagate client disconnect (platform limitation, documented)
Interrupt-abort (ADR-028) works **locally** (`res.on('close')` fires — Node holds the real client socket) but **NOT on Lambda**: `responseStream` writes to AWS's buffering layer, not the client socket, so neither close events nor write-errors surface the disconnect. Measured via CloudWatch — an interrupted ~45s turn billed **44,977 ms** (ran to completion). AWS officially documents this ("streamed responses are not interrupted… billed for the full function duration").
- **Decision: accept, not fix-forward.** The 120s turn budget caps wasted billing (negligible at free-tier).
- **For real industry / production:** chat runs on a **long-running server** that holds the real socket — there `on('close')` (our local behavior) works, so reliable abort needs no extra mechanism. The limitation is specific to Lambda's buffered handoff.
- Reliable abort on serverless would instead use an **explicit client-cancel** API (the production "stop" pattern) — a Phase 7 candidate when real LLM tokens make a wasted turn costly.
- Full write-up: [docs/learning/lambda-streaming-disconnect.md](../learning/lambda-streaming-disconnect.md).

---

## Testing & Validation

**Local (`jchat-test --debug`):**
- [x] Multi-turn: same `session_id` → 2nd turn "loaded N prior messages"; `message_count` increments.
- [x] `--debug` before/after Redis snapshots via the real `/session` endpoint (uid from JWT).
- [x] User-first save: user message persisted at turn start (earlier `ts` than assistant).
- [x] Partial-save on interrupt: kill curl mid-token → partial assistant saved `interrupted: true` (local — `res.on('close')` fires).
- [x] `jready` reports Upstash reachable.

**AWS (`jchat-test --aws --debug` against `jh-chat-stack`):**
- [x] Clean turn: streams >30s, `message_count` 0→2, both `interrupted: false`.
- [x] Multi-turn: BEFORE shows prior messages, "loaded 2 prior messages", AFTER `message_count: 4`.
- [x] uid-namespaced key `chat:1:{sid}`.
- [⚠] Interrupt-abort: does NOT fire on Lambda — turn ran full (~45s billed, CloudWatch). **Documented limitation, accepted** (see Highlights / learning doc).

**Automated:** future — multi-turn smoke test asserting Redis contents.

---

## Metrics

| Metric | Value |
|--------|-------|
| Redis commands per turn | ~4 (read+write user, read+write assistant) |
| Redis TTL | 1h sliding |
| Block compaction | every (SUMMARIZE_AT − RECENT_KEEP) = 10 messages |
| Estimated blob size | ~30 KB (bounded) |
| Multi-turn history | turn N sees turns 1..N-1 ✅ |
| Interrupted turn billed (Lambda) | full ~45s (disconnect not propagated — documented) |

---

## Next Steps → Phase 6C

Build the **chatbox frontend widget**: floating UI, minimize/open, EventSource rendering of streaming + intermediate states, input lock (sequential turns), refresh re-fetch from Redis.

---

## File Structure

```
chat/ (Node.js service)
├── redis.js              # NEW — Upstash client: getSession, saveUserMessage,
│                         #   saveAssistantMessage, buildContext, summarizeOverflow(stub), ping
├── sseTransport.js       # NEW — runTurn(stream, params) + adaptNodeRes(res) (shared transport)
├── streamTurn.js         # read history → generate → save (user-first/assistant-later)
├── handler.js            # Lambda: runTurn(responseStream, …) + GET /session debug
├── local.js              # local: runTurn(adaptNodeRes(res), …) + GET /session debug
├── generateResponse.js   # mock seam (now receives real history)
├── .sam-config / .env.*  # + UPSTASH_REDIS_REST_URL/TOKEN (generators inject to Lambda env)
└── package.json          # + @upstash/redis

dev.sh                    # jready Redis check + chat quick-start; jchat-test --debug
```

---

## Key Learnings

- **Lambda doesn't propagate client disconnect** — interrupt-abort works locally (real socket) but not on Lambda (writes go to AWS's buffer, not the client). Measured: 44,977ms billed on an interrupted turn. Full write-up: [lambda-streaming-disconnect.md](../learning/lambda-streaming-disconnect.md).
- **Block compaction > per-turn sliding** — summarizing on *every* message past the limit would cost an LLM call per turn (Phase 7) and defeat prompt caching (per-turn prefix mutation). Accumulate to a high-water mark, compress a block once.
- **User-first / assistant-later** — persist the user message immediately (definite fact, survives early failure); save the assistant at turn end. Industry pattern.
- **Adapter pattern unifies transports** — `adaptNodeRes(res)` makes local look like Lambda's `responseStream`, so one `runTurn` serves both and they can't drift.
- **ESM env-load ordering** (carried from 6A) — read `process.env` at call-time, not module-load, so `.env.local` is loaded first.

---

## References

**External Documentation**:
- [Upstash Redis](https://upstash.com/docs/redis) — free-tier limits, REST/HTTP access
- [Redis EXPIRE / SET EX](https://redis.io/commands/set/) — TTL semantics

**Internal Documentation**:
- [ADR-026](../architecture/DECISIONS.md#adr-026-chat-session-lifetime--identity--per-tab-ephemeral) — session identity
- [ADR-027](../architecture/DECISIONS.md#adr-027-chat-state-store--ephemeral-redis-upstash) — ephemeral Redis store
- [PHASE_6A_SUMMARY.md](./PHASE_6A_SUMMARY.md), [PHASE_6C_SUMMARY.md](./PHASE_6C_SUMMARY.md)
