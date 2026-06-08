# Phase 7E: Evaluation (Offline)

**Status**: ✅ Completed
**Date**: June 8, 2026
**Goal**: Measure the chat agent's quality systematically — especially **faithfulness** (grounded vs. hallucinated) — turning the 7C/7D anti-fabrication promise into numbers. The HRT "developing evaluations" deliverable.

> **Result:** a working offline eval harness with **two independent judges that agree** — a hand-rolled LLM-as-judge AND Ragas, both scoring faithfulness **1.0** on the grounded cases, cross-validating each other. Plus: multi-dimensional scoring (faithfulness + answer_relevancy + warmth + conciseness via AspectCritic), an **adversarial self-test** (a planted hallucination correctly scores 0.0 → proves the detector bites), and LLM-judged refusal checks. Capture (Node, runs the real agent) is split from grade (Python). The build surfaced — and fixed — real eval gotchas (a Ragas markdown bug that mis-scored a grounded answer 0.000; the warmth-vs-faithfulness tension). Deep-dive captured in [vectors-rag-eval.md](../learning/vectors-rag-eval.md).

---

## Overview

7E adds **offline evaluation** of the chat agent using **Ragas** (LLM-as-judge RAG metrics). It runs as a separate suite — **NOT** in the live request path — scoring agent answers over a curated test set so quality is measurable and regressions are caught.

**Two-step harness (Node capture → Python grade)** — because the agent is Node and Ragas is Python:
1. **Capture (Node):** run the real agent over the test set; record `{question, answer, contexts}` per case to a JSON file. `contexts` = the tool results the agent actually saw (resume text, retrieved jobs) — captured by wrapping `buildTools().call` (the industry "trace the run" idea, scaled down; reuses the same instrumentation seam as `AGENT_DEBUG`).
2. **Grade (Python):** load the JSON, score with Ragas, assert thresholds.

This is the discipline the HRT JD names. It proves the grounding work from 7D with data, not claims.

**Included**:
- Node capture driver → `eval/cases.json` (the `(question, answer, contexts)` triples).
- A curated test set covering the real query types (from 7C/7D E2E traces) + a hallucination-bait case.
- Ragas **faithfulness** (primary, reference-free) + **answer relevancy**; assert thresholds.
- Pinned judge model (the measuring instrument) recorded in config.

**Excluded**:
- Admin-agent evaluation (deterministic + fixtures) → Phase 8 (different discipline; see notes).
- Eval *in the request path* — eval is always offline.
- Ground-truth "answer correctness" — deferred (expensive to curate; faithfulness needs no reference).

---

## Decisions (resolved in design)

### A. Capture entry point → wrap `buildTools().call`, run the real agent
The eval driver builds the tools surface via `buildTools(uid)` ([generateResponse.js](../../chat/generateResponse.js)) but **wraps `.call`** to record every tool result (the contexts), then runs `runAgent`. So contexts are captured **exactly** (not log-parsed). Multi-turn cases thread prior turns as `messages` directly (the driver controls the sequence), so summary/history behavior can be exercised when needed.

### B. Faithfulness is **reference-free** — no "predefined good answer"
Faithfulness scores *answer ↔ contexts* ("is every claim supported by what the tools returned?"), NOT *answer ↔ ideal answer*. So we do **not** hand-write expected answers (subjective + high-effort). We only need `(question, answer, contexts)`. (Ground-truth "answer correctness" is a separate, optional metric — deferred.)

### C. LLM-as-judge is a **regression signal**, not truth
Yes, this is "AI grading AI" — accepted because prose has no deterministic check (contrast Phase 8's structured output, which does). Mitigations: faithfulness **decomposes** the answer into atomic claims and judges each supported/not (binary, more stable than a holistic 0–1 vibe); low temperature; **aggregate over many cases** (one case's ±0.02 wobble is noise, the mean is the signal); thresholds set with margin (fail < 0.85, not "== 0.93").

### D. **Pin the judge model** (the measuring instrument)
Two models are in play: the **agent** model (under test — vary it freely) and the **judge** model (grades — keep fixed). Changing the judge recalibrates the scale and breaks comparability with history. So the judge model+version is recorded in the eval config; if ever changed, re-baseline the whole set. Pin the judge; vary the agent.

---

## Key Achievements

### 1. Capture → grade split ✅
- **Capture (Node, [capture.js](../../eval/capture.js)):** runs the REAL agent (`runAgent` + real MCP tools + real Claude) per case; records `{question, answer, contexts}`. Gets **contexts** by *externally wrapping `buildTools().call`* (decorator) — possible because tools are dependency-injected. Only external dep: the MCP server (no HTTP/auth/Redis).
- **Grade (Python):** two runners read the same `cases.captured.json`. Industry "trace then grade offline" pattern, scaled down.

### 2. Two judges, cross-validated ✅
- **Hand-rolled** ([run_eval.py](../../eval/run_eval.py)): a ~30-line LLM-as-judge — decompose answer → claims → judge each supported 1/0 → score = supported/total (1 combined LLM call). Plus LLM-judged refusal checks + adversarial self-test.
- **Ragas** ([run_eval_ragas.py](../../eval/run_eval_ragas.py)): the named tool — same algorithm in 2 calls (extract, then NLI judge). Anthropic judge + Voyage embeddings (NOT OpenAI).
- **Both score faithfulness 1.0** on grounded cases → cross-validation. Building both *found* a Ragas bug (below) and proved the agent faithful.

### 3. Multi-dimensional metrics ✅
- **faithfulness** (per-claim grounding, hard gate) · **answer_relevancy** (embeddings) · **warmth** + **conciseness** (Ragas `AspectCritic`, yes/no rubric → pass-rate, tracked signals not gates).
- Closes the blind spot where a cold-but-grounded answer scores faithfulness 1.0 yet is a worse product (warmth flagged the one terse follow-up).

### 4. Negative test (adversarial self-test) ✅
- A hand-authored answer with claims NOT in the context ([adversarial.json](../../eval/adversarial.json)) must score **low** (inverted assertion) → proves the detector bites (scores 0.0). A faithfulness metric that never sees a hallucination is unproven.

---

## Highlights

### LLM-as-judge = decompose → binary verdicts → arithmetic
The score is NOT a fuzzy "rate 0–1" — the LLM judges each *claim* 1/0, code computes `supported/total`. Stable (binary > holistic), reproducible (temp 0, pinned judge), explainable (per-claim). Granularity = claim count (clean small cases → exact 1.0, not 0.98).

### The metric serves the product, not vice versa
Off-the-shelf faithfulness penalized **warmth** ("Want me to dive deeper?" → counted as an unsupported "claim" → 0.76). Fix was NOT a robotic agent — it was **customizing the metric** (exclude conversational framing → 1.0) and measuring warmth *separately/positively*. Optimizing a proxy until it hurts UX is Goodhart's law.

### Found + fixed a real Ragas bug
Ragas scored a **fully grounded** markdown-table answer **0.000** — its sentence-segmenter garbled the table. Caught it by cross-validation (the other judge said 1.0) + feeding Ragas clean statements (all supported). Fixed by normalizing markdown → plain prose before grading. *A broken metric is worse than none — validate the eval against known cases before trusting numbers.*

---

## Testing & Validation

### Results (latest run)
- [x] **Faithfulness 1.0** on 4 grounded cases — both judges agree (hand-rolled + Ragas).
- [x] **Adversarial hallucination → 0.0** — detector self-test passes (inverted assertion).
- [x] **Refusals 3/3** (job-detail/Walmart/weather) — LLM-judged "declined", no fabrication.
- [x] **warmth 75% / conciseness 75%** — tracked; the one terse follow-up correctly flagged not-warm.
- [x] **Cross-validation** — two independent judges converge → trustworthy signal.

### Honest caveats
- Small test set (4 graded + 3 refusal + 1 adversarial) — proves the *harness*, not broad coverage; expand cases over time.
- `answer_relevancy` ~0.58 — diluted by conversational filler (expected); not a gate.
- Eval is **outcome-focused** (final answer + tool results), NOT **trajectory** (tool-selection/reasoning) — trajectory eval is a Phase 8 concern.

---

## Next Steps → Phase 8

Apply the same eval discipline to the admin agent — but with **deterministic**
checks (extracted title appears in source HTML, etc.) against `trials/{company}/`
golden fixtures, plus a confidence-gated harness. See [PHASE_8_NOTES.md](./PHASE_8_NOTES.md).

---

## File Structure (as built)

```
eval/                       # NEW
├── cases.js                # curated test set (questions, uid, [history], expectRefusal) + thresholds
├── adversarial.json        # hand-authored known-bad case (detector self-test — must score LOW)
├── capture.js              # NODE: runs the real agent per case; wraps buildTools().call to record
│                           #       contexts → writes cases.captured.json
├── run_eval.py             # PYTHON: hand-rolled LLM-as-judge (faithfulness + LLM refusal check
│                           #         + adversarial self-test). Just the anthropic SDK.
├── run_eval_ragas.py       # PYTHON: Ragas runner (faithfulness customized to ignore filler #1,
│                           #         answer_relevancy w/ Voyage, warmth+conciseness AspectCritic #2)
├── requirements.txt        # anthropic (hand-rolled side)
├── cases.captured.json     # generated (gitignored) — the {question, answer, contexts} triples
└── .venv-ragas/            # isolated venv (gitignored) — ragas 0.2.x pinned vs langchain-community 0.3.3
```
Run: `jbemcp-bg` → `node eval/capture.js` → `python eval/run_eval.py`
     and/or `eval/.venv-ragas/bin/python eval/run_eval_ragas.py` (needs ANTHROPIC_API_KEY + VOYAGE_API_KEY).

---

## Key Learnings

Full deep-dive in [vectors-rag-eval.md](../learning/vectors-rag-eval.md). Headlines:

- **LLM-as-judge = decompose + binary + arithmetic.** The LLM judges each claim 1/0; code computes the ratio. Never ask the LLM for the final number. Granularity = claim count (so clean small cases give exact 1.0, not 0.98).
- **Ragas == hand-rolled, internally.** Same slice→judge→ratio algorithm; Ragas just splits it into 2 LLM calls (extraction + NLI prompts). Cross-validating the two caught a bug and built trust.
- **Capture defines what you can grade.** Answer comes from the output stream; **contexts must be captured by instrumenting the agent** (external `tools.call` wrap — works because of dependency injection). Want to grade tool usage → capture tool calls too.
- **The metric serves the product.** When faithfulness penalized warmth, the fix was the *metric* (exclude filler) + a separate warmth metric — NOT a robotic agent. Goodhart's law.
- **Validate the eval itself.** A grounded answer scored 0.000 (Ragas markdown bug). A broken metric is worse than none — sanity-check against known cases, cross-validate judges, add an adversarial negative test.
- **Thresholds are calibrated, not inherited.** "0.85" is not an industry standard — calibrate to baseline + stakes; alert on regression. **Pin the judge model** (the measuring instrument).
- **Ops gotchas:** ragas 0.4.x broken vs langchain 1.x (pin 0.2.x + langchain-community 0.3.3, isolated venv); use Anthropic+Voyage not OpenAI; bump judge `max_tokens` (4096) to avoid `LLMDidNotFinishException`.

---

## References

- [Ragas](https://docs.ragas.io/)
- [DeepEval](https://github.com/confident-ai/deepeval) (alternative / Phase 8)
- [vectors-rag-eval.md](../learning/vectors-rag-eval.md) — eval concepts
