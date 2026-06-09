# Phase 8E: Prompt / Context / Harness Engineering

**Status**: 📋 Planning (discuss before building)
**Date**: June 9, 2026
**Goal**: Turn the **ad-hoc agent fixes from 8C/8D into a deliberate, systematic methodology** for making the extractor-discovery agent more reliable, efficient, and observable. 8D worked, but every improvement was reactive (watch a run fail → patch the prompt). 8E is about making that *systematic*.

> Framing: 8C/8D proved the agent CAN do the task. 8E is about doing it *well* — fewer trials,
> fewer tokens, fewer silent failures, and a repeatable process for improving the agent.

---

## Three pillars

### 1. Prompt engineering — the agent's instructions
What we did ad-hoc; what to systematize:
- **Symptom→fix tables** (worked great for HRT's `setting` param) — generalize: a small library of "if you see X error, the fix is usually Y" per ATS / failure mode.
- **Shortcut-over-explore** — encode the efficient path explicitly (fetch-all-then-filter; /favicon.ico direct) so the agent doesn't rabbit-hole. **Open question:** how to detect/prevent NEW rabbit holes we haven't seen? (a meta-instruction: "if an approach fails twice, change strategy" — already added; is it enough?)
- **Few-shot examples?** — we currently give *patterns* (ATS URLs), not full worked examples. Would 1-2 complete worked traces (e.g. "here's how Greenhouse discovery looks end-to-end") reduce trials further? Tradeoff: token cost vs. fewer round-trips.
- **Prompt regression** — when we change a prompt to fix company X, does it break company Y? Right now we find out by re-running. **Idea:** a small eval suite (the 5 companies as golden cases) that re-runs after prompt changes and checks counts match (375/128/110/120/~10). This is the "validate the eval before trusting it" discipline (7E) applied to the agent.

### 2. Context engineering — what the agent sees each turn
The ~200K-tokens/run problem + the trim that backfired:
- **Summarize-don't-drop** — the trim failed because it removed content the agent re-examined. The right version: when a tool result is "consumed," replace the raw HTML/JS dump with a SHORT SUMMARY of what was learned ("found greenhouse slug=X, 3 decoy jobs"), keeping the conclusion, dropping the bytes. Needs an LLM summarization step (like the chat agent's history summarizer) or a structured "notes" the agent maintains.
- **Working memory / scratchpad** — instead of re-deriving facts from re-fetched pages, have the agent maintain a running "what I know" note (endpoint, action, params, slug) that persists compactly across turns. Reduces re-fetches (HRT re-read the JS bundle 7×).
- **Selective context** — does every turn need the FULL system prompt + all history? Caching handles the system prompt; the history is the cost. Per-turn context budgeting.
- **Measure first** — instrument token usage per stage/turn (we only have the Anthropic dashboard total now). Know where the 200K goes before optimizing.

### 3. Harness engineering — the deterministic scaffolding around the LLM
The "judgment vs. control flow" split + verification:
- **Verified-code propagation** (done in 8D) — generalize the principle: any stage that *fixes* code in a trial must emit the fixed version downstream. Audit other stages for the same divergence risk.
- **Structured gates** (done: `valid:false → stop`) — are there other places the harness should enforce a consequence the LLM might mis-route? (e.g. low-confidence results → flag for human, don't silently proceed.)
- **Retry / self-repair loops** — when a stage fails, should the harness auto-retry with the failure reason injected (a fresh attempt), vs. just escalating? Bounded self-repair.
- **Container concurrency cap** — a semaphore on `run_trial` (Docker is fine, but oversubscription throttles). Low priority.
- **Registry write safety** — the parallel-write race (8D). Options: file lock, or make the registry AUTO-DISCOVER `extractors_v2/*.py` instead of being edited (removes the shared-file write entirely). The auto-discover version also fixes "the agent forgot to register" failures.
- **Cost/step guards** — a hard token or step budget per *run* (not just per stage), with graceful escalation.

---

## Candidate concrete work items (to prioritize tomorrow)
1. **Agent eval harness** — the 5 companies as golden cases; re-run after prompt changes, assert counts. (Highest-value: makes prompt iteration safe + measurable.)
2. **Summarize-don't-drop context** — a working-memory note the agent maintains; cut the re-fetch loops + the 200K tokens.
3. **Registry auto-discovery** — scan `extractors_v2/*.py` instead of editing a shared file. Fixes the race AND the "forgot to register" class. (Also unblocks parallel runs.)
4. **Token/step instrumentation** — measure per-stage cost before optimizing.
5. **Symptom→fix library + retry-with-reason** — generalize the HRT-style fixes; bounded self-repair.

---

## Open questions for discussion
- Is the agent's job DONE at "discover + verify + write," or should 8E also cover the **runtime JD parsing** (LLM-parse a job page → structured JD) and **wiring into the backend** (registry → the `list_companies` endpoint, replacing v1's enum)? Those might be their own phase.
- How much to invest in token optimization vs. just accepting ~200K/run (it's a local admin tool run occasionally, not a hot path)?
- Few-shot worked examples vs. patterns — worth the token cost?
- Eval harness: assert exact counts (brittle as sites change) vs. "count in a sane range + JD validates" (robust but looser)?

---

## Relation to other work
- Builds directly on [PHASE_8C_SUMMARY](PHASE_8C_SUMMARY.md) + [PHASE_8D_SUMMARY](PHASE_8D_SUMMARY.md).
- The eval-harness idea reuses the 7E discipline ([vectors-rag-eval.md](../learning/vectors-rag-eval.md)) — "validate the validator," golden cases, pin the judge.
- Lessons captured in [agent-discovery-prompts.md](../learning/agent-discovery-prompts.md).
