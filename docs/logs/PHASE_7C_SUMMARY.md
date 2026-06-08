# Phase 7C: Agent Loop (Node) — Replace the Mock

**Status**: ✅ Completed
**Date**: June 7, 2026
**Goal**: Replace the Phase 6 mock with a real, hand-written **ReAct** agent loop in the Node chat service that calls the Phase 7B MCP tools and streams a grounded answer from Claude — emitting the same SSE events so the transport and frontend are unchanged.

> **Result:** the real agent works end-to-end **locally**. A live turn (user 18, 550 embedded jobs + resume) streams a grounded answer: Claude → ReAct loop → MCP tool call (`search_jobs_semantic`) → streamed tokens citing real jobs. Built as 4 new SDK-isolated modules behind the unchanged seam; 14 offline tests pass (loop logic, uid-injection, MCP client, fail-closed). The mock is gone. **Not yet:** deployed to Lambda, frontend (`ChatWidget`) verified in-browser, per-call timeout wired — see Open Items.

---

## Overview

7C is the heart of the AI backend: the **agent loop**. The Node chat service becomes an **MCP client** to the Phase 7B Python MCP server and runs a **ReAct** (Reason→Act→Observe) loop against the raw Anthropic API. It slots in at the `generateResponse()` **seam** built in Phase 6 — emitting the same `step`/`token`/`done`/`error` events, so the 6C frontend and 6A transport need **no changes** (except threading `uid` through the seam — see below).

Built **directly** (no LangChain / Vercel AI SDK — [ADR-029](../architecture/DECISIONS.md#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk)) so the agent mechanics are owned and defensible.

**What 7A/7B already delivered (7C does NOT redo these):**
- The seam: [generateResponse.js](../../chat/generateResponse.js) — `async function*` yielding `step`/`token`/`done`.
- Turn loop, Redis history, save user/assistant, abort + turn-budget timeout — [streamTurn.js](../../chat/streamTurn.js) ([ADR-028](../architecture/DECISIONS.md)/[ADR-031](../architecture/DECISIONS.md#adr-031-conversation-storage-in-redis--per-message-entries-in-a-single-json-blob)).
- Frontend (6C) + SSE transport (6A) already consume those events.
- **MCP server deployed & tested** (7B): 4 tools, service-token auth ([ADR-033](../architecture/DECISIONS.md#adr-033-mcp-server-auth--service-to-service-token-not-cors)), `McpServerUrl` Function-URL output.
- Tools + embeddings (7A): `search_jobs_semantic`, `get_job`, `get_resume`, `score_against_jd`.

**Included in 7C**:
- Hand-written **ReAct** loop: `stop_reason` loop, bounded iterations, tool results fed back.
- Node = MCP **client** to the Python MCP server (7B).
- Thread the authenticated `uid` through the seam → into every tool call.
- Replace the mock at the seam; map agent steps → `step` events, stream final answer → `token`s.
- Anthropic API key (secret → Lambda env); prompt caching on the stable prefix.
- Per-LLM-call timeout (layer 2, within-turn).

**Explicitly excluded**:
- Real summarization / token-aware context mgmt → 7D.
- Evaluation harness → 7E.
- Plan-and-Act, step-level checkpointing, Pydantic/structured-output validation → not needed here; see Agent Architecture Decisions for why, and Phase 8 for where they fit.

---

## Agent Architecture Decisions

### ReAct (native tool-use loop), NOT Plan-and-Act
The native Anthropic loop — send messages + tool schemas → on `stop_reason: tool_use` run the tool, feed `tool_result` back, repeat; on `end_turn` it's the answer — **is ReAct** (Reason→Act→Observe). We do not add a separate "planner."
- **Why not Plan-and-Act:** chat tasks are short (typically 1–3 tool calls: search → maybe get_job → maybe score) and **conversational** (the user follows up / redirects). Upfront planning adds rigidity and cost with no payoff at this task length.
- **Where Plan-and-Act *would* fit:** the **Phase 8** autonomous extractor-generation agent — long, multi-step, non-conversational. Reconsider there, not here.

### No new checkpointing — Redis history IS the state
Step-level checkpointing (persist state between tool calls to pause/resume/recover) is unnecessary for 7C.
- **Within a turn:** a turn is one Lambda invocation; if it dies the user retries. Checkpointing a ~3-step loop is cost/complexity for no real recovery benefit.
- **Across turns:** the durable agent state **is** the message history in Redis ([ADR-031](../architecture/DECISIONS.md#adr-031-conversation-storage-in-redis--per-message-entries-in-a-single-json-blob)) — rebuilt each turn via `getSession`/`buildContext`. That's the checkpoint, at per-message granularity.
- **Where real checkpointing fits:** resumable long-running jobs in **Phase 8**.

### Validation boundary — schema-validated tools, optional Zod, no Pydantic
- **Tool boundary already validated (7B):** FastMCP auto-generates JSON Schemas from the Python tool signatures and validates `tools/call` args server-side — so the tool inputs are schema-checked for free.
- **Agent side (Node):** Pydantic is Python-only → N/A here. The analog is **Zod** for validating Claude's `tool_use` args before dispatch — optional polish (cleaner agent-side errors/retries); the MCP server is the real gate.
- **Where Pydantic belongs:** the Python phases — **7E** (typed eval cases/results) and especially **8** (structured generated-extractor specs + sandbox verdicts that gate automated next steps, with no human in the loop). Validation scales with autonomy.

---

## Key Achievements

### 1. The ReAct agent loop (raw Anthropic, no framework) ✅
- `messages` + tool schemas → Claude → if `stop_reason: tool_use`, emit a `step`, run the tool via MCP, append `tool_result`, loop; else (`end_turn`) stream the final answer. **Bounded max-iterations** (default 8, throws if exceeded). ([ADR-029](../architecture/DECISIONS.md#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk))

### 2. Node as MCP client (`chat/mcpClient.js`) ✅
- Connects to the MCP server (7B) over **streamable-http**, sending `Authorization: Bearer <MCP_SERVICE_TOKEN>` ([ADR-033](../architecture/DECISIONS.md#adr-033-mcp-server-auth--service-to-service-token-not-cors)).
- `listTools()` → schemas for Claude; `callTool(name, args)` → run a tool (unwraps FastMCP's `{result}`).
- **Decision (resolved):** use the **official `@modelcontextprotocol/sdk`** client. ADR-029's "build directly" is about the agent *loop* (the differentiator); the MCP transport (JSON-RPC framing, handshake, JSON-vs-SSE negotiation) is commodity plumbing not worth hand-rolling. The loop is hand-written; the wire is the SDK.

### 3. Thread `uid` through the seam (the one interface change) ✅
- The mock called `generateResponse(sessionId, history)` with **no `uid`** — but every MCP tool requires `user_id`, and `userMessage` wasn't passed either (the mock echoed history length).
- Seam is now `generateResponse(sessionId, history, { uid, userMessage })` ([streamTurn.js](../../chat/streamTurn.js) passes both). `uid` comes from the JWT; the agent injects it into every `callTool`.

### 4. Replace the mock at the seam ✅
- `generateResponse` body: mock → `yield* runAgent(...)`. Same event types out: agent steps → `step`; final answer tokens → `token`. Transport (6A) unchanged; frontend (6C) unchanged *by contract* (browser-verified is an Open Item).

### 5. Two-hop streaming relay ✅
- Hop 2: Anthropic SDK streams tokens → orchestrator (via `liveTextDeltas`). Hop 1: orchestrator relays → browser as `token` SSE frames. **Only the final turn's tokens** are forwarded; tool-use turns yield no text (just `step` events).

### 6. Secrets + caching + timeout
- `ANTHROPIC_API_KEY` as a secret (chat env + generators → Lambda env; metadata in [chat/.env.example](../../chat/.env.example)). ✅
- **Prompt caching** on the stable prefix (system + tool schemas) via `cache_control: ephemeral`. ✅
- **Per-LLM-call timeout** (layer-2, within-turn) — adapter SUPPORTS `perCallTimeoutMs` (`anthropicClient.js`), but `generateResponse` does not pass it yet. ⏳ (Open Item.)

### 7. Grounding / system prompt ✅
- `SYSTEM_PROMPT` ([generateResponse.js](../../chat/generateResponse.js)): what the app is, who the user is, use tools for REAL data, **never fabricate**, say so when a tool returns nothing. Goes in `system` (cacheable). (Heavier anti-fabrication pass is 7D.)

---

## Implementation (as built)

Four new SDK-isolated modules behind the unchanged seam. The split exists so the
ReAct logic is testable offline (it imports neither SDK):

| File | Role | Imports SDK? |
|------|------|--------------|
| [agentLoop.js](../../chat/agentLoop.js) | the **ReAct state machine** (`runAgent`) — pure logic; takes `callModel` + `tools` as params (dependency injection) | **No** |
| [anthropicClient.js](../../chat/anthropicClient.js) | `callModel` adapter — Claude streaming + tool use → the loop's contract; `toolsForAnthropic` schema bridge | Anthropic |
| [mcpClient.js](../../chat/mcpClient.js) | MCP **client** — `connect`/`listTools`/`callTool` over streamable-http + bearer | MCP |
| [generateResponse.js](../../chat/generateResponse.js) | the **seam** — wires `runAgent({ callModel, tools, system, messages })`; `buildTools` injects `uid` | — |

**Key decisions made while building (beyond the plan):**
- **Dependency injection** — `runAgent` imports no SDK; prod passes real `callModel`+MCP, tests pass stubs. → 8 loop tests run offline, $0.
- **`uid` injection is the security boundary** — `buildTools` calls `callTool(client, name, { ...args, user_id: uid })`. The authenticated uid is spread **last**, so a model that hallucinates `user_id: 999` can't override it ([ADR-033](../architecture/DECISIONS.md#adr-033-mcp-server-auth--service-to-service-token-not-cors)). Tested explicitly.
- **Live streaming via a producer/consumer queue** (`liveTextDeltas`) — bridges the SDK's `.on('text')` into an async generator drained live; the loop drains deltas **first**, then resolves `stopReason` (promise) → tool-use turns yield no text and fall through. True token-by-token, not buffer-then-dump.
- **System-role split** — `buildContext` may prepend a `{role:'system'}` summary; Anthropic forbids `system` inside `messages`, so `generateResponse` splits it out and folds it into the system prompt. (Latent until 7D adds summaries; fixed pre-emptively.)
- **FastMCP `{result:…}` unwrap** — list/`dict|None` tools return `structuredContent.result`; `mcpClient.callTool` unwraps it.
- **Debug tracing** — `AGENT_DEBUG` env: `1` = compact ReAct trace, `2` = also dump the full `messages` array sent to the model. **Off by default** (prod never logs user data); opt in via `jbenode -d` / `jbenode -dd`.

---

## Highlights

### The seam pays off
Because 6A/6B built a stable `generateResponse()` seam (mock behind it), 7C changes essentially only that function's body — plus the small `uid` signature addition. Streaming, Redis persistence, auth, and the frontend keep working untouched.

### Detecting the final turn
Stream tokens to the user only when the model is emitting the **final answer** (text), not when assembling a tool call. Intermediate reasoning → `step` events; final text → `token`s.

### Cost awareness (real LLM now)
Each turn costs LLM tokens. The Lambda-disconnect limitation ([learning/lambda-streaming-disconnect.md](../learning/lambda-streaming-disconnect.md)) now wastes *tokens* on an abandoned turn, not just compute — the turn budget caps it; explicit client-cancel is the roadmap fix.

---

## Testing & Validation

### Build & test order — outside-in, by risk and dependency
Build the two halves as **independently testable pieces, mock-first**, then integrate — so a failure is isolated to one layer:

1. **MCP client first** (the riskier, external piece — Node→Python network + bearer auth). Prove the boundary in isolation, no LLM.
2. **ReAct loop second**, against a **fake tool registry** + **stubbed model** — prove the control flow (termination, max-iter cap, `tool_result` feed-back, final-turn detection) offline and free.
3. **Integrate** — swap fake tools for the real MCP client. Both halves already proven → failures are wiring, not logic.
4. **Replace the mock at the seam** + thread `uid`.
5. **End-to-end** — thin happy-path + key failures on top.

### Test pyramid

| Layer | What it proves | LLM | MCP | Cost |
|-------|----------------|-----|-----|------|
| MCP client unit | connect / listTools / callTool / sends bearer (401 on bad token) | no | real 7B | fast |
| Loop logic unit | state machine, max-iter cap, step/token event mapping | **stub** | **stub** | instant, free |
| Loop + real LLM | real Claude actually emits `tool_use` for our schemas | real | fake tools | some cost — run sparingly |
| Integration | loop + real MCP client; `uid` flows to every call | stub/real | real | medium |
| E2E | browser→answer, multi-turn, timeout, frontend unchanged | real | real | slow — keep thin |

> **Node test harness** stood up (was none — `chat/` only had `@upstash/redis` + `jsonwebtoken`; pytest doesn't carry over). Uses built-in `node:test`, wired as `npm test` → `node --test`. **No new test deps.**

### Checklist — actual
- [x] **MCP client (isolation):** `listTools` returns all 4 + schemas; `callTool('get_resume')` round-trips; sends bearer; fails closed without config. ([mcpClient.test.js](../../chat/__tests__/mcpClient.test.js); live test auto-skips if server down.)
- [x] **Loop logic (stubbed):** `tool_use`→`end_turn` terminates; **always-`tool_use` stub stops at max-iterations**; `tool_result` fed back; tool error → `tool_result` (recovers); abort stops loop; step/token/done mapping. ([agentLoop.test.js](../../chat/__tests__/agentLoop.test.js), 8 tests.)
- [x] **`uid` flow:** uid injected as `user_id` on every call; **model-supplied `user_id` cannot override** it; schemas converted to Anthropic format. ([generateResponse.test.js](../../chat/__tests__/generateResponse.test.js), 3 tests.)
- [x] **E2E (manual, local):** real turn (user 18) — Claude → `search_jobs_semantic` → grounded streamed answer citing real jobs. Verified via `jchat-test` + `[agent]` trace.
- [ ] **Loop + real LLM as an automated test** — not added (needs a key in CI); covered manually by the E2E.
- [ ] **Browser E2E** — `ChatWidget` against the live agent (only `jchat-test`/curl so far).
- [ ] **Per-call timeout fires on a hang** — adapter supports it; not wired into `generateResponse` yet.

**Tally:** 14 offline tests pass (`npm test`); 1 live MCP test skips when the server is down. Live E2E verified manually.

---

## Open Items (carry-over)
- **Wire per-LLM-call timeout** — pass `perCallTimeoutMs` from `generateResponse` → `callModel`.
- **Browser verification** — confirm `ChatWidget` renders the real agent (the "frontend unchanged" claim) in-app, not just via curl.
- **`liveTextDeltas` has no automated test** — verified manually (tokens stream live); a real-key streaming test would lock it in.
- **Deploy** — set `MCP_SERVER_URL_PROD_VALUE` (real Function URL) + `AGENT_DEBUG=0` in the Lambda env, then `jpushchat`. (Generators already pick up the new vars — no script changes needed.)

---

## Next Steps → Phase 7D

Real context engineering: fill the summarization stub, token-aware triggering, grounding/anti-fabrication. (The `{role:'system'}` summary split in `generateResponse` is already in place for it.)

---

## File Structure (as built)

```
chat/
├── agentLoop.js          # NEW — ReAct state machine (SDK-free, DI); AGENT_DEBUG tracing
├── anthropicClient.js    # NEW — callModel adapter (Claude stream + tool use) + toolsForAnthropic
├── mcpClient.js          # NEW — MCP client (connect/listTools/callTool) + bearer auth
├── generateResponse.js   # mock → real agent wiring; SYSTEM_PROMPT; buildTools injects uid; sig += { uid, userMessage }
├── streamTurn.js         # passes { uid, userMessage } into the seam
├── package.json          # + @anthropic-ai/sdk, + @modelcontextprotocol/sdk, + "test" script
├── .env.example/.env.local # + ANTHROPIC_API_KEY, MCP_SERVER_URL, MCP_SERVICE_TOKEN (+ generator metadata)
└── __tests__/            # NEW — node:test: agentLoop / mcpClient / generateResponse (14 tests)

dev.sh                    # jbenode/-bg take -d (trace) / -dd (dump messages); jchat-token defaults to user 18
```

---

## Key Learnings

- **The native Anthropic tool-use loop IS ReAct.** No framework needed — `stop_reason: tool_use` → run tool → feed `tool_result` back → loop; `end_turn` → answer. ~90 lines, fully owned ([ADR-029](../architecture/DECISIONS.md#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk)).
- **The LLM is stateless — you are its memory.** Each iteration re-sends the whole growing `messages` array (question → assistant tool_use → tool_result → …). The `AGENT_DEBUG=2` dump makes this concrete.
- **Dependency injection makes an agent testable.** Keeping the loop SDK-free (inject `callModel`/`tools`) let 11 of the contract's behaviors be verified offline for $0 — including the max-iteration guard and the uid-override defense.
- **Inject identity last.** `{ ...modelArgs, user_id: uid }` — the trusted uid overrides anything the model supplies; the security boundary is one spread-order.
- **Tool errors are observations, not crashes.** Feeding `{error:…}` back as a `tool_result` lets the model recover (ReAct), instead of failing the turn.
- **`system` is separate from `messages`.** Anthropic rejects `system` role inside messages; the stable system prefix is also what prompt caching keys on — keep it out of the moving conversation.
- **ReAct, not Plan-and-Act, fits a short conversational task** (1–3 tools, user can redirect). Plan-and-Act is for long/autonomous tasks — revisit for the Phase 8 agent.

---

## References

- [Anthropic Messages API / streaming + tool use](https://docs.anthropic.com/en/api/messages)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [ADR-029](../architecture/DECISIONS.md#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk) · [ADR-030](../architecture/DECISIONS.md#adr-030-single-standalone-python-mcp-server-multi-client) · [ADR-033](../architecture/DECISIONS.md#adr-033-mcp-server-auth--service-to-service-token-not-cors)
