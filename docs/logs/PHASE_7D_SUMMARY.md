# Phase 7D: Context Engineering (Real)

**Status**: ✅ Completed
**Date**: June 7, 2026
**Goal**: Make the agent's context handling real — fill the summarization stub with an LLM call and harden grounding — building on the 7C agent and the 6B context structure. **Deliberately count-based, NOT token-based** (see decision below).

> **Result:** all of it verified E2E. A real session crossed `SUMMARIZE_AT=20` → compaction fired, `splice` kept the recent 10, and a cheap Haiku call produced an accurate rolling summary (user profile + top-3 jobs **with IDs** + conclusions). Crucially the summary is **consumed**: after the top-3 message was compacted out, the agent still answered "#2 = TikTok 2130" *from the summary*. Grounding (no fabrication, upload-then-retry) and **prompt caching** (`cache_read=2616/2725`, ~96% of input cached) also confirmed live. Only the summarizer-failure fault-injection is untested (fail-safe by inspection).

> **Scope simplification (decided):** trigger compaction on **message count**, not token usage. At our message sizes, 20 messages ≈ ~3K tokens typical / ~6K worst case (a full resume ≈ 1.4K) vs a **200K** context window — ~2–3%, zero truncation risk. Token accounting would be plumbing for no benefit. So 7D = **real summarization + grounding**, and drops the token-aware-triggering item.

---

## Overview

Phase 6B built the **structure** for context management (per-message Redis blob, recent-window + block-compaction hook, `summarizeOverflow` **stub**). Phase 7C added the **real agent** (ReAct loop, MCP tools, streaming) and, while wiring it, already laid some 7D groundwork. 7D fills in the real *policy*: actual LLM summarization of older turns and stronger grounding — with a **count-based** compaction trigger (token accounting deliberately skipped; see above).

**What 7A–7C already delivered (7D builds on / does NOT redo):**
- **Context structure** (6B): `{message_count, summary, messages[]}` Redis blob; block-compaction hook ([redis.js](../../chat/redis.js)); `summarizeOverflow` stub (no-op, guards empty input). (7D retunes the constants to `SUMMARIZE_AT=20` / `RECENT_KEEP=10` — see below.)
- **The summary→system split** (7C): `generateResponse` already pulls any `{role:'system'}` summary OUT of `messages` and folds it into the system prompt (Anthropic forbids `system` in messages). So the *consumption* side of summaries is done.
- **An anti-fabrication system prompt** (7C): `SYSTEM_PROMPT` already says "use tools for REAL data, never invent, say so when a tool returns nothing." 7D **strengthens** it (re-check-current-state rule); the *behavior* (does the model actually obey?) is unverified — measured in 7E.
- **Prompt caching** (7C): `cache_control: ephemeral` is **wired** on the system prefix ([anthropicClient.js](../../chat/anthropicClient.js)); actual cache **hits** (`usage.cache_read_input_tokens > 0`) are not yet confirmed — an Open Item.
- **Usage available if ever needed** (7C): the adapter's `finalMessage()` carries `.usage.input_tokens` — the hook for token-based triggering *if* we ever upgrade from count-based (we don't in 7D).

**Included in 7D**:
- Real `summarizeOverflow` (LLM summarization of the overflow block) — and the **sync→async** rework it forced.
- Grounding hardening + a "re-check current state, don't trust stale history" rule.
- Compaction stays count-based (20/10) and prompt-cache-friendly (block-batch, stable prefix).

**Excluded / dropped**:
- **Token-aware triggering** — dropped (see scope simplification above; count is sufficient at our sizes).
- Evaluation of grounding quality → 7E (Ragas measures it).

---

## Decisions (resolved)

### A. Where summarization runs → **inline await** ✅
`summarizeOverflow` was synchronous, called in `appendMessage` ([redis.js](../../chat/redis.js)) during `saveAssistantMessage` (turn `finally`). A real LLM call is async/slow, so `appendMessage` + `summarizeOverflow` are now **async**, awaited inline. It's infrequent (every `SUMMARIZE_AT - RECENT_KEEP` = 10 messages), so the occasional ~1–2s on a compaction turn is acceptable. On failure we keep the prior summary (drop the overflow) rather than break the turn. (Deferred/background is the future optimization if latency bites.)

### B. Summarizer model → **separate cheap call (Haiku)** ✅
A new [summarize.js](../../chat/summarize.js): a non-streaming `messages.create` on `claude-haiku-4-5`, low `max_tokens`, with a "preserve facts/decisions, be concise" prompt. Independent of the agent loop, keeps cost low.

### C. Trigger → **message count (20/10), NOT tokens** ✅
Dropped token accounting (scope simplification). The `splice` block-compaction is unchanged; only the constants moved to `SUMMARIZE_AT=20` / `RECENT_KEEP=10`. Rationale + estimate documented in [redis.js](../../chat/redis.js). Upgrade path noted there if ever needed.

---

## Key Achievements

### 1. Real summarization (fill the 6B stub) ✅
- [summarize.js](../../chat/summarize.js) `summarizeConversation(existingSummary, overflow)` — cheap Haiku call that folds the overflow block into the rolling summary. `summarizeOverflow` ([redis.js](../../chat/redis.js)) now delegates to it (async; keeps the empty-input guard).
- `renderMessage` flattens stored messages — including `tool_use` / `tool_result` blocks — into the transcript the summarizer reads.
- Block/batch (20/10) keeps it infrequent (~every 10 messages), cheap, and cache-friendly.

### 2. Grounding / anti-fabrication (harden the 7C prompt) ✅
- The 7C `SYSTEM_PROMPT` already forbade fabrication; 7D adds: **"rely on tools for CURRENT state — do NOT trust what an earlier turn said about the user's data; it may have changed; when in doubt, call the tool again"** ([generateResponse.js](../../chat/generateResponse.js)). Fixes the upload-then-retry case. Measured in 7E.

### 3. Prompt caching alignment ✅ (already in place)
- Stable prefix (system + tool schemas) is cacheable (7C); block-summarize means the summary (also in the prefix) mutates only every ~10 messages, so the prefix stays stable between compactions → cache hits hold.

---

## Highlights

### Block compaction beats per-turn sliding
Summarizing on every message past the limit would cost an LLM call per turn AND defeat prompt caching (per-turn prefix mutation). Accumulate to a high-water mark, compress a block once. (6B built the trigger; 7D fills the LLM summarization.)

### Why count, not tokens (the simplification)
Token-aware triggering exists to stop input crowding out the `max_tokens` output reservation. But at our sizes (20 msgs ≈ 3–6K) vs a 200K window, that can't happen — so count is a sufficient, far simpler proxy. The win is avoiding `usage`-plumbing through `callModel → runAgent → streamTurn` for a risk that doesn't exist here. (Documented in [redis.js](../../chat/redis.js) with the upgrade path.)

### Summarization is a SECOND, independent LLM use
The agent loop (7C) is one LLM use; summarization is a second one. Keeping it a separate cheap call (Haiku, non-streaming — not the chat model mid-loop) keeps the loop simple and the cost low.

---

## Testing & Validation

### Automated (offline) ✅
- [x] `renderMessage` flattens string / `tool_use` / `tool_result` / mixed blocks correctly ([summarize.test.js](../../chat/__tests__/summarize.test.js), 4 tests).
- [x] `summarizeOverflow([])` bypasses the LLM call (empty-input guard).
- [x] Full chat suite green (18 tests).

### Manual / E2E (needs key) ⏳
- [x] A long conversation (≥ `SUMMARIZE_AT`=20) summarizes the overflow — **verified E2E**: at message_count 20, compaction fired, `splice` kept the recent 10, and the Haiku summarizer produced an accurate summary (user profile, top-3 jobs **with IDs**, Walmart "none saved" conclusion).
- [x] **Summary is consumed, not just generated — verified E2E.** After the top-3 message was compacted OUT of the recent window, the agent still correctly answered "#2 = TikTok Privacy AI, ID 2130" — sourced from the rolling summary. Proves the summary is fed back into context and used to answer about compacted-away history (the whole point of context engineering).
- [x] Summarization runs async without breaking the turn's save/`finally` flow — verified E2E (the compaction turn completed normally, streamed its answer, and persisted the trimmed session + new summary). *(Fault-injection — forcing the summarizer to throw — still untested; the `try/catch` fail-safe is by inspection.)*
- [x] Answers stay grounded; agent refuses to fabricate — verified E2E (asked about a Walmart job, none saved → agent said so, did not invent one).
- [x] Upload-then-retry: after new data is added, the next turn reflects it (agent re-checks) — verified E2E.
- [x] **Prompt-cache hit rate stays high — VERIFIED ✅.** `usage` logging (`jbenode -d`/`-dd`) on a multi-turn session showed `cache_read_input_tokens=2616, 2725` — caching is working. Example turn: `in=92 cache_read=2616` → only ~3% of input billed at full rate, ~96% served from cache (1/10th cost). (My earlier "prefix too small <1024" worry was wrong: it counted only system + tool schemas (~630 tok) and forgot the **conversation history** is in the cached prefix too — with a resume + job descriptions in history, the prefix is ~2,600+ tok, well over the minimum.)

### Minor cosmetic note (accepted, not fixing)
- When the model emits narration ("Let me search…") in the SAME turn as a `tool_use` block, that preamble streams as tokens and can run into the next turn's answer text (observed: `…saved list!It looks like…`). Suppressing it would require buffering (losing live token streaming) or block-type plumbing — **not worth trading away live streaming** for a small cosmetic seam. Accepted as-is; revisit only if it bothers users. (Could also be nudged via the prompt: "don't narrate before calling tools.")

---

## Open Items
- **Verify summarization E2E** — drive a 20+ message conversation and inspect the rolling summary (use `jbenode -dd` to see the message list shrink + the summary appear).
- **Confirm prompt-cache hits** — check `usage.cache_read_input_tokens > 0` on the 2nd+ turn (mechanism is wired; effectiveness unproven).
- **Confirm grounding behavior** — observe the agent actually refusing to fabricate / re-checking after an upload (prompt is written; behavior measured in 7E).
- **Tune constants if needed** — 20/10 is aggressive (only ~2–3 recent exchanges verbatim); bump `RECENT_KEEP` if the agent "forgets" mid-chat.
- **`summarizeConversation` LLM call has no automated test** — `renderMessage` is tested; the call itself is manual/E2E (needs a key).

---

## Next Steps → Phase 7E

Measure grounding/relevance systematically with Ragas (offline eval).

---

## File Structure (as built)

```
chat/
├── summarize.js        # NEW — cheap Haiku summarizer (summarizeConversation, renderMessage)
├── redis.js            # summarizeOverflow → real async call; appendMessage async; SUMMARIZE_AT=20/RECENT_KEEP=10
├── generateResponse.js # SYSTEM_PROMPT hardened (re-check-current-state rule)
└── __tests__/summarize.test.js  # NEW — renderMessage block-flattening (4 tests)
```
(Not touched: `anthropicClient.js`, `agentLoop.js`, `streamTurn.js` — no token plumbing needed, since the trigger stayed count-based.)

---

## Key Learnings

- **Count is a fine compaction trigger when message sizes are bounded and the window is huge.** 20 msgs ≈ 2–3% of a 200K window → token accounting is unjustified plumbing. Match the mechanism to the actual risk, not the textbook.
- **Summarization is a second, independent LLM use** — a cheap non-streaming Haiku call, separate from the chat agent. Don't reach for the chat model where a small one does.
- **The sync→async ripple:** turning a stub into a real LLM call made `appendMessage` async and put a (rare) LLM call on the turn's `finally` path — a reminder that "fill the stub" can change the call's concurrency shape, not just its body.
- **Grounding is also a freshness rule, not just an anti-fabrication rule:** "don't trust stale history, re-check via tools" is what makes upload-then-retry work — and it's a prompt line, not a cache mechanism.

---

## References

- [Anthropic prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Anthropic Messages API — usage / token counts](https://docs.anthropic.com/en/api/messages)
- [vectors-rag-eval.md](../learning/vectors-rag-eval.md) — context/RAG concepts
- [PHASE_7C_SUMMARY.md](./PHASE_7C_SUMMARY.md) — the agent this builds on
