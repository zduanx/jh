# Phase 8 — Notes (Admin Autonomous Extractor-Generation Agent)

Design notes for Phase 8. Becomes a proper phase doc when built.
(Phase 7 is done across [PHASE_7A](./PHASE_7A_SUMMARY.md)–[PHASE_7E](./PHASE_7E_SUMMARY.md).)

---

## What Phase 8 is

An **autonomous agent** that, given a new company, drives:
**generate an extractor** (per `EXTRACTOR_PROMPT.md`) → **run it through a validation harness** → **iterate on failure** → **gate on pass**.

It's a fundamentally different agent from the Phase 7C chat agent:

| | 7C chat agent | Phase 8 admin agent |
|---|---|---|
| Shape | **conversational ReAct** (human in loop) | **autonomous, self-correcting** (no human per step) |
| Output | free-form prose | **structured data** (extractor spec, parsed jobs) |
| Task length | short (1–3 tool calls) | long, multi-step |
| Checking | offline eval (LLM-judge) | **inline validation gates** + offline fixtures |
| Language | Node | Python |

---

## Key design decisions (from the 7E deep-dive discussion)

### Agent pattern: ReAct vs Plan-and-Act
- 7C used **ReAct** (short, conversational). Phase 8 is **long + autonomous** → this is where **Plan-and-Act** earns its place (decide the steps up front, execute, re-plan on failure). In practice: an outer **plan** with **ReAct execution inside each step** + re-planning when a step fails (pure Plan-and-Act is brittle; plans go stale on contact with reality).

### Tools: probably NO MCP (it's local)
- MCP is justified only **across a boundary** (process / network / language). Phase 8's agent is **Python** and can call the tool functions (and reuse the existing `db/`/service layer) **in-process** → **just call them directly, no MCP**. (Contrast 7C: Node→Python boundary made MCP necessary.)
- It *could* reuse the 7B MCP server as a 2nd client ([ADR-030](../architecture/DECISIONS.md#adr-030-single-standalone-python-mcp-server-multi-client)) for the "build tools once, many clients" story — but that's a *choice* for consistency, not a necessity. Default: direct calls.
- **Exception:** if the sandbox runs in a separate process/container (it should), that boundary could be bridged with MCP **or** plain subprocess/RPC. Sandboxing creates the only real boundary in Phase 8.

### Framework: hand-roll vs PydanticAI
- **PydanticAI** = an agent framework from the Pydantic team — agent loop + tools + **Pydantic-validated structured outputs** in one package. Tempting for Phase 8 (Python + structured outputs).
- Tension with [ADR-029](../architecture/DECISIONS.md#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk) ("build the loop directly, own it"). Decide explicitly (ADR-worthy): hand-roll the Python loop (consistent with 7C) vs. PydanticAI (get validated structured outputs + loop free). Lean hand-roll for ownership unless the structured-output ergonomics clearly win.

### Pydantic: yes — this is its home
- The agent emits **structured artifacts** (extractor spec, parsed jobs, eval verdicts) that feed **automated next steps with no human watching**. Pydantic = define the schema, **validate the output, fail closed if malformed**. That IS the inline-validation layer.
- "**Validation scales with autonomy**": the human-in-loop chat (7C) needed little; the autonomous agent needs strict structured-output validation. (Note: the backend already uses Pydantic via FastAPI — same idea, different boundary.)

---

## The harness: validation ≠ evaluation (the core insight)

Phase 8 needs **two layers** — passing structural checks ≠ a *good* extraction.

### Layer 1 — Validation (inline gates, deterministic): "is it well-formed / not obviously wrong?"
- Boolean, cheap, **runs during the agent's run** (online) to gate the next step.
- Pydantic schema valid? · extracted `title` appears in source HTML? · `count > 0`? · URL well-formed?
- This is **online eval** — inline guardrails that stop a bad step (vs. 7E's offline-only chat eval).

### Layer 2 — Quality measurement: "is it actually GOOD?" (valid ≠ good)
Asserts catch *broken*, not *bad*. An extractor can pass every assert and still: grab 3 jobs of 50 (terrible recall), mangle a field, be brittle on the next page, or grab the wrong element that *happens* to be in the HTML. To measure GOOD you need **ground truth**:
- **(a) Golden fixtures** (`trials/{company}/`): known-correct expected output → compute **precision / recall / field-accuracy** vs. truth (offline regression). Primary quality measure.
- **(b) LLM-as-judge** for the un-checkable parts (e.g. "is this generated extractor *reasonable/maintainable*?") — borrow the 7E technique only where fixtures can't reach.

So Phase 8 eval = **deterministic where truth is known (fixtures), LLM-judge where it isn't.** Symmetry with 7E: chat has no single right answer → must use LLM-judge; extraction HAS a right answer → mostly deterministic.

### Trajectory eval (what 7E skipped)
7E was **outcome-focused** (final answer). A long multi-step agent also wants **trajectory eval**: right tools, sensible order, each intermediate step valid, efficiency (didn't loop needlessly). Industry pattern for complex agents: inline step gates + golden-trajectory regression + LLM-judge for fuzzy steps + step logging/observability. Failed prod runs become new offline fixtures.

---

## Sandboxing (the must-not-skip piece)

The agent runs **LLM-generated extractor code** → run it **isolated**, never `exec()` in-process with our credentials.
- Minimum: **subprocess + timeout** (no network/secrets). Ideal: a **container**.
- This is the one place a real **process boundary** exists in Phase 8 (see Tools decision).

---

## Scope cut (keep it focused)

Build the **generate→validate→iterate→gate loop + the real harness** against the *existing* extractor structure in a scratch/test path. Do **NOT** build: DB-driven scraping config, an admin UI, or wiring generated extractors into the live registry — describe those as roadmap.

Checkpointing / human-in-the-loop: a long, resumable agent with human escalation is where **agent-state checkpointing** genuinely helps (vs. short chat turns) — pause on novel cases, resume after human input. Worth it here; was *not* worth it in 7C.

---

## Confidence-gating
Auto-accept a strong pass / auto-retry a clear fail / **escalate genuinely-novel cases to a human**. The gate uses the harness scores (Layer 1 + Layer 2).

---

## Open questions to resolve when building
- Hand-roll the Python agent loop vs. PydanticAI? (ADR-worthy)
- Sandbox mechanism: subprocess+timeout vs. container? How does the agent talk to it (direct vs. MCP/RPC)?
- Plan-and-Act structure: how much up-front plan vs. reactive re-planning?
- Golden fixtures: which companies in `trials/` have clean expected-output to grade against?
