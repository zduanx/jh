# Phase 8E: Prompt / Context / Harness Engineering

**Status**: 📋 Planning (scope finalized — build harness items; context as backlog)
**Date**: June 9, 2026
**Goal**: Systematic improvement of the extractor-discovery agent across three dimensions — **prompt, context, harness**. 8C/8D proved the agent CAN do the task; 8E is about doing it *well* (fewer trials, leaner context, deeper understanding) and demonstrating the agent-engineering taxonomy explicitly.

> The framing itself is the value: most "I built an agent" work is one undifferentiated blob.
> Naming the three pillars — and knowing which technique lives where — is what separates
> *agent engineering* from *agent usage*.

---

## The three pillars (and which technique lives where)

The key conceptual move: **categorize a technique by what you MODIFY, not by what it benefits.** Several context *problems* are best solved by *harness* changes — prevention beats cleanup.

| Pillar | What you modify | Example techniques |
|---|---|---|
| **Prompt** | the instructions | failure-driven tuning, symptom→fix tables, shortcuts-over-explore |
| **Context** | what's IN the window | summarize-on-consume, retrieval, working memory |
| **Harness** | the machinery (tools, loop, gates) | sub-agents, tool granularity, scoped guards, grep tool |

---

## 1. Prompt engineering — DONE (covered in 8C/8D)

This pillar is already strong. Across 8C/8D the prompts were tuned **failure-driven**: watch a real run fail → diagnose the root cause from trial logs → encode a *targeted* fix → verify. Captured in [agent-discovery-prompts.md](../learning/agent-discovery-prompts.md):
- symptom→fix tables (HRT's `setting` param), shortcuts-over-"think-harder" (fetch-all-then-filter; /favicon.ico direct), the ATS discovery ladder, judgment-vs-control-flow split.
- The deeper skill shown: deciding **prompt-vs-harness boundary** — some "prompt problems" were correctly fixed in *code* (the `valid:false → stop` gate, verified-code propagation).

**No major new work here.** A `grep`/`search` tool (below, under harness) is the one addition — but its benefit is *context* (read less), not prompt.

---

## 2. Harness engineering — BUILD THIS (the headline)

### (a) Batch READ tool — `read_files([...])`  ← build
- Reading is fetching context; the agent often reads several files in separate turns (`write_extractor` did read hrt.py → read registry.py → ... = multiple round-trips).
- A `read_files([paths])` tool returns them in ONE call → fewer round-trips (each turn re-sends the whole conversation, so cutting turns helps).
- **Reads only — writes stay GRANULAR (one file per `write_file`).** This matches industry coding agents (Claude Code / Cursor / Aider): per-file writes preserve observability (`[step N]` UX), reviewability (git diff per file), the read-before-write guarantee, and error isolation. Batching writes trades those away; batching reads is low-risk (no side effects).

### (b) Sub-agent — `spawn_agent(task) -> summary`  ← build (the most impressive item)
- A sub-agent is a **nested agent loop** with its OWN fresh context. The parent calls it like a tool; the parent's context receives only the sub-agent's **summary result**, never its internal trials.
- **Why it matters:** it's the PREVENTIVE answer to context bloat — the heavy content never enters the parent context. (Contrast: summarize-on-consume is the *reactive* answer — clean up what's already there. Prevention > cleanup.) So a context problem is solved by a *harness* change.
- **Where it helps here:** the `fetch_jobs` site/JS-bundle exploration (HRT re-read the 23KB bundle 7× → context bloat). A sub-agent: *"explore this site + bundle, return {endpoint, action, required_params}"* → reads the bundle in ITS context, returns 3 facts. The main agent never holds the 23KB.
- **Why our architecture is ready:** `run_stage` is already a self-contained, isolated-context agent loop — a sub-agent in all but name (each stage starts with fresh `messages` + only prior *results*). Agents are naturally recursive; `run_stage` IS the recursive unit. Adding a sub-agent = let a stage spawn another stage-like loop as a tool.
- **Resume value:** building a working sub-agent (isolated context, summary-only return, the recursive loop) demonstrates the deepest understanding of agent architecture — the central pattern of modern multi-agent systems (Claude Code's Task tool, research agents).
- **⚠️ The handoff is where sub-agents DRIFT** (a known failure mode): when the parent passes a complex/vague requirement down, the sub-agent — lacking the parent's full context — produces omissions/imprecision. Mitigation: keep the delegated task **crisp + self-contained** with a **tight return schema** (e.g. "find the AJAX endpoint, action, and required params in this bundle" → `{endpoint, method, action, required_params}`), NOT "go figure out the jobs." Narrow task in, structured facts out.

### (c) ~~grep/search tool~~ — DROPPED
- The agent reads its OWN generated files + fetched web content, not a large codebase — there's nothing to grep. No real use here; cut.

### Note: harness depth scales INVERSELY with model strength
- A strong, large-context model (Opus, 1M) needs LESS harness — it can hold the whole task in one conversation. Weaker/cheaper models need MORE harness (sub-agents, compaction, gates) to compensate. So harness engineering is partly *compensating for model limits* — worth stating, and a reason the agent could run leaner on a stronger model.

---

## 3. Context engineering — partially BUILT (history caching) + backlog (summarization)

### ✅ BUILT: prompt-cache the conversation history (fixes the rate limit + cuts cost)
ReAct re-sends the whole growing conversation every turn, so on **Anthropic Tier-1 (Sonnet 30K input-tokens/min)** a run hit a **429 mid-`fetch_jobs`** (the large Greenhouse JSON re-sent each turn). Fix:
- Added a `cache_control` breakpoint on the **last message** each turn (we already cached the system prompt). Because we append-only, `[system + all prior messages]` is a stable prefix → cache hit next turn.
- The re-sent history then counts as **cache READS** — 0.1× cost AND **excluded from the per-minute input limit** ("excluding cache reads"). Rate-limited input = `input_tokens + cache_creation`; reads are free.
- **Measured:** roblox went from 429 → peak **13.5K/30K** in the rolling-60s window. ✅
- **Caveat:** cache *writes* still count, so a single huge payload's FIRST appearance can still spike — the deeper fix is to not pull more than needed (e.g. avoid fetching full job descriptions when only departments/offices are needed to filter). → backlog.
- Also added **token instrumentation**: per-call `[tokens] counted=… cache_read=… | ~X/30K in last 60s` (a sliding-60s window from `usage`) — so you SEE the per-minute accumulation + caching working. (Lesson: instrument before optimizing.)

### BACKLOG: summarize-on-consume (reduce tokens at the source)
Caching makes re-sends free, but the *first* arrival of a big result still counts. Summarize-on-consume reduces the *total*: after a tool result is consumed, compact it. Understood + a version is **already built in the chat agent** (the Redis history summarizer, Phase 7).

### Summarize-on-consume (the technique, with a concrete trace)

The insight: some tool results are needed only TRANSIENTLY — to *extract a fact*, then they're dead weight that keeps getting re-sent every turn. After the fact is extracted, REWRITE that result in history to a short summary (keep the conclusion, drop the bytes).

**Concrete message-history trace** (the HRT bundle case):

```
turn N    assistant → action: read_file("frontend-bundle.min.js")     # the request
turn N+1  user      → "<23 KB of minified JS>"                         # the big raw result
turn N+2  assistant → "Found the AJAX call: action='get_hrt_jobs_handler',
                       POST to admin-ajax.php, requires a `setting` param
                       (the data-filters-settings DOM blob)."          # CONSUMES the result
          ──► At this moment the HARNESS rewrites turn N+1 IN PLACE:
              messages[N+1].content =
                "[read_file frontend-bundle.min.js — summarized: AJAX action
                 'get_hrt_jobs_handler', POST admin-ajax.php, needs `setting`]"
turn N+3  user → next input.  The LLM is now sent history where turn N+1
                is the 30-token SUMMARY, NOT the 23 KB. All FUTURE turns
                re-send the summary, so context stops growing by 23 KB/turn.
```

**Why it must be summarize, NOT drop** (the lesson from the 8D trim that backfired): the failed 8D trim *dropped* large results → the agent could no longer see the bundle → it RE-FETCHED it (7× re-reads). The fix is to leave the **conclusion** behind so the agent doesn't need to re-derive it. *Compaction preserves knowledge; truncation destroys it and forces re-work.*

**Two ways to produce the summary:**
1. **Cheap (no extra LLM call):** use the assistant's OWN next `thought`/`summary` (turn N+2) as the replacement for turn N+1 — the model already stated what it learned. Zero added cost.
2. **Robust (extra call):** a small LLM summarization step (like the chat agent's summarizer) when results pile up.

**When to add it:** when a run gets long enough that re-sent context dominates the bill — i.e. if the agent gains more/longer stages, or sub-agents aren't enough. For the current 5-company scope, runs are short; this is backlog.

### Related context backlog
- **Working-memory scratchpad** — a compact running "what I know" note the agent maintains (endpoint, slug, params) so it re-reads the *note*, not the *files*.
- **Retrieval-not-preload** — index the codebase, retrieve only relevant snippets per step (the Cursor model). Overkill for this agent.

---

## Finalized scope for 8E

**Done:**
- ✅ **`read_files([...])` batch read** (writes stay granular) — harness. Saves a round-trip in write_extractor.
- ✅ **History caching** (cache_control breakpoint on the last message) + **token instrumentation** — context. Fixed the Tier-1 429; measured peak 13.5K/30K.

**Still to build:**
1. **`spawn_agent(task)` sub-agent** for site/bundle exploration in `fetch_jobs` — harness; THE headline (nested loop, isolated context, summary return). Keep the delegated task crisp + structured return (avoid the drift failure mode).

(grep/search dropped — the agent has no large codebase to navigate.)

**Backlog (documented, understood, partially built in the chat agent):**
- Summarize-on-consume context compaction (trace above) — add when runs get long.
- Working-memory scratchpad; retrieval-not-preload.
- Agent eval harness (5 companies as golden cases — regression-safe prompt iteration).
- Registry auto-discovery (fixes the parallel-write race + "forgot to register").

---

## The one-sentence framing (for interviews / resume)
> "I improved the agent across three pillars: **prompt** (failure-driven instruction tuning), **harness** (tool granularity — batch reads but granular writes like industry coding agents; a **sub-agent** for heavy exploration), and **context** (I prompt-cached the conversation history to fix a Tier-1 rate-limit 429 — append-only history is a stable prefix, so a cache breakpoint on the last message turns the re-sent history into free cache reads, 0.1× cost and excluded from the per-minute limit; plus token instrumentation to *see* it; summarize-on-consume is the next lever). The key insight: **context problems are often best solved in the harness** — prevent the bloat structurally (sub-agents, caching) rather than clean it up."

---

## Relation to other work
- Builds on [PHASE_8C_SUMMARY](PHASE_8C_SUMMARY.md) + [PHASE_8D_SUMMARY](PHASE_8D_SUMMARY.md); lessons in [agent-discovery-prompts.md](../learning/agent-discovery-prompts.md).
- Summarize-on-consume mirrors the chat agent's history summarizer (Phase 7, [redis.js]/summarize.js).
- The eval-harness backlog reuses the 7E "validate the validator" discipline ([vectors-rag-eval.md](../learning/vectors-rag-eval.md)).
