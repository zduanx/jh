# Phase 6C: Chatbox Frontend Widget (Mocked AI)

**Status**: ✅ Completed
**Date**: June 6, 2026
**Goal**: Build the floating chatbox widget on the Search page that renders the streaming backend (6A/6B), with sequential-turn input locking and refresh-safe history.

> **Result:** verified in the browser against the **deployed AWS** chat (Function URL + Upstash Redis) — streaming answer renders token-by-token (>30s turns), multi-turn history works, refresh restores history, the 🐛 debug button dumps the live Redis blob, and **CORS works for the streamed cross-origin response** (the deferred 6A CORS question — resolved: no extra headers needed).

---

## Overview

Phase 6C adds the **frontend** for the chatbox, consuming the streaming backend from 6A/6B. It's a floating widget (lower-right of the Search page) the user can open, minimize, and close. It streams via **`fetch` + `ReadableStream`** (NOT EventSource — chat is POST + Bearer auth, which EventSource can't do), renders a persisted **step log** then the streamed answer tokens, and re-fetches history from Redis on open/refresh.

The AI is still **mocked** (Phase 7 replaces it at the `generateResponse` seam — the widget is unchanged when real AI lands, since it consumes the same SSE events). 6C proves the full user-facing loop end-to-end: open → ask → watch steps → see the streamed answer → ask again (multi-turn) → refresh and recover history.

**Included in this phase**:
- Floating widget UI: pill launcher → open panel → minimized bar; **close-confirm** popup (ends chat → new session).
- **`fetch` + `ReadableStream`** SSE client (manual frame parsing) — supports POST + `Authorization: Bearer` ([chatStream.js](../../frontend/src/components/chat/chatStream.js)).
- Streaming render: unified **`step`** events accumulated into a per-message step log (persisted with the answer), then `token`s typed into the answer bubble.
- Sequential turns: input locked while streaming ([ADR-028](../architecture/DECISIONS.md#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts)).
- `sessionId` generation (tab-tied, `sessionStorage`), shown in the header ([ADR-026](../architecture/DECISIONS.md#adr-026-chat-session-lifetime--identity--per-tab-ephemeral)).
- History-on-open + refresh-safe: re-fetch from Redis via `GET /session` (backend is source of truth — [ADR-027](../architecture/DECISIONS.md#adr-027-chat-state-store--ephemeral-redis-upstash)); frontend renders only.
- Auto-growing input (up to ~4 lines, then scroll).
- **🐛 debug button**: dumps the live Redis session blob inline (reuses the authed `GET /session` endpoint).
- Config consistency: `REACT_APP_CHAT_URL` (local `8100` / prod Function URL), pushed to Vercel by `jpushvercel` (added to `FRONTEND_CHECK`).

**Explicitly excluded**:
- All AI logic → Phase 7 (widget talks to the mock; nothing in the UI changes when real AI lands).
- Markdown rendering, stop button, multiple conversations, typing animations → out of scope (low signal / wrong phase).
- Grounding / job-context indicators → Phase 7+.

---

## Key Achievements

### 1. Floating chatbox widget
- Lower-right of the Search page; pill launcher → open panel → minimized bar; state persisted to `sessionStorage`.
- **Close-confirm** popup (warns context will be lost) → ends chat → new session next open.
- CSS `chat-` prefixed per convention.

### 2. fetch + ReadableStream SSE client (NOT EventSource)
- Chat is POST + `Authorization: Bearer` — EventSource is GET-only / can't send headers, so we read `response.body` as a stream and parse SSE frames manually ([chatStream.js](../../frontend/src/components/chat/chatStream.js)). This is the industry approach for POST-based SSE (ChatGPT web / Vercel AI SDK / Anthropic+OpenAI JS SDKs).
- Renders unified `step` events (accumulated, persisted per-turn) then `token`s into the answer bubble; handles `done`/`error`/`interrupted`.

### 3. sessionId (tab-tied)
- `crypto.randomUUID()`, stored in `sessionStorage` (id only); shown in the panel header ([ADR-026](../architecture/DECISIONS.md#adr-026-chat-session-lifetime--identity--per-tab-ephemeral)).
- Close → reopen starts a new chat (new id).

### 4. Turn lifecycle (frontend aspects)
- Input locked while streaming (sequential turns); stream-closed-without-`done` → marked interrupted ([ADR-028](../architecture/DECISIONS.md#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts)).
- HTTP 200 ≠ success for a stream → success determined by receiving `done`.

### 5. Refresh-safe history (frontend renders only)
- On open/refresh, re-fetch history from Redis via `GET /session` (backend source of truth — [ADR-027](../architecture/DECISIONS.md#adr-027-chat-state-store--ephemeral-redis-upstash)). No history owned by the frontend → avoids the two-sources-of-truth anti-pattern.

### 6. 🐛 Debug button
- Dumps the live Redis session blob inline — **reuses** the authed `GET /session` endpoint (same one used by history-on-open and `jchat-test --debug`). Transient (not persisted, not re-sent to the model).

### 7. Config consistency + Vercel wiring
- `REACT_APP_CHAT_URL` mirrors `REACT_APP_API_URL` (local `8100` / prod Function URL); added to `dev.sh` `FRONTEND_CHECK` so `jpushvercel` pushes it to Vercel.

---

## Highlights

### Why fetch+ReadableStream, not EventSource
EventSource can't POST or send auth headers; chat needs both. So 6C parses SSE manually over a fetch stream — the same reason production chat clients don't use EventSource for the chat turn (they reserve it for GET/no-auth notifications, like this app's ingestion progress SSE).

### Persisted step log
`step` events are attached to each assistant message (not a transient state), so scrolling the conversation shows how each answer was produced. Note: steps persist in the **frontend view only** (not Redis — the backend stores user+assistant content); a refresh shows answers without steps. Acceptable (steps are ephemeral progress).

### CORS for streamed cross-origin responses — verified
The deferred 6A concern (does the Function URL's CORS apply to a *streamed* response?) is **resolved**: the deployed browser→Function URL streaming worked with no CORS error, so no in-handler `Access-Control-Allow-Origin` was needed. The Function URL's `Cors` config suffices.

---

## Testing & Validation

**Browser, against deployed AWS (Function URL + Upstash):**
- [x] Widget opens / minimizes / closes; state persists across refresh.
- [x] Asking a question streams `step` events then the answer tokens (>30s turns render fine).
- [x] Input locked while streaming; unlocks on `done` (sequential turns).
- [x] Multi-turn: turn 2 reflects turn 1's history (from Redis).
- [x] Refresh → history restored from Redis via `GET /session`.
- [x] 🐛 debug dumps the live Redis blob inline.
- [x] Close → confirm → reopen → new chat (new `sessionId`).
- [x] **CORS works** for the streamed cross-origin response (no extra headers needed).

**Automated:** future — component tests for the widget.

---

## Metrics

| Metric | Value |
|--------|-------|
| Streaming render | smooth token-by-token, >30s turns ✅ |
| Input lock during stream | enforced ✅ |
| Refresh restores history | yes (from Redis) ✅ |
| CORS (browser → deployed Function URL, streamed) | works, no extra headers ✅ |

---

## Next Steps → Phase 7

Substitute the **mock** with the **real AI backend** at the `generateResponse` seam: agent loop ([ADR-029](../architecture/DECISIONS.md#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk)), single standalone Python MCP server ([ADR-030](../architecture/DECISIONS.md#adr-030-single-standalone-python-mcp-server-multi-client)), real LLM streaming, grounding/anti-fabrication. **The frontend is unchanged** — it already renders the same SSE events. See [PHASE_7A_SUMMARY.md](./PHASE_7A_SUMMARY.md) (Phase 7 is split into 7A–7E).

---

## File Structure

```
frontend/src/
├── components/chat/
│   ├── ChatWidget.js     # floating widget: states, streaming render, history, debug, close-confirm
│   ├── ChatWidget.css    # chat- prefixed styles
│   └── chatStream.js     # fetch+ReadableStream SSE client + fetchSession
└── pages/search/SearchPage.js   # mounts <ChatWidget />

frontend/.env.local       # + REACT_APP_CHAT_URL (local 8100 / prod Function URL)
dev.sh                    # FRONTEND_CHECK includes REACT_APP_CHAT_URL (jpushvercel pushes it)
```

---

## Key Learnings

- **EventSource can't do POST + auth headers** → POST-based SSE chat needs `fetch` + `ReadableStream` with manual frame parsing. EventSource is for GET/no-auth notifications only.
- **Streaming CORS works via the Function URL `Cors` config** — the streamed response carried the CORS headers; no in-handler workaround needed (the 6A worry didn't materialize).
- **OPTIONS + GET is normal** — cross-origin authed requests trigger a CORS preflight (`OPTIONS`) before the real call; not a bug.
- **One endpoint, many consumers** — `GET /session` serves history-on-open, the 🐛 debug button, and the CLI `--debug`, all via the same authed production path (kept consistent for free).
- **The widget is AI-agnostic** — it renders SSE events; Phase 7 swaps the mock for a real agent with zero frontend change.

---

## References

**External Documentation**:
- [SSE EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [Web Storage API (sessionStorage)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API)

**Internal Documentation**:
- [ADR-026](../architecture/DECISIONS.md#adr-026-chat-session-lifetime--identity--per-tab-ephemeral) — session identity
- [ADR-028](../architecture/DECISIONS.md#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts) — sequential turns, partial-as-final
- [PHASE_6A_SUMMARY.md](./PHASE_6A_SUMMARY.md), [PHASE_6B_SUMMARY.md](./PHASE_6B_SUMMARY.md)
