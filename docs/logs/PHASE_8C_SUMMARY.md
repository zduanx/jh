# Phase 8C: Logo Walking-Skeleton (the first agent slice)

**Status**: 📋 Planning
**Date**: June 8, 2026
**Goal**: The thinnest end-to-end agent slice — given a company + careers URL, the agent **discovers the company logo URL** through sandboxed trials and writes it into a generated extractor (uncommitted). The *task* is trivial; the point is to **wire every layer** (agent loop · structured terminal output · sandboxed trials · scoped file write · reporting) on an easy task before scaling to the hard one (8D).

> Walking-skeleton-first: prove the whole pipeline on "find the logo", then 8D makes
> the *task* harder ("list all jobs") through the *same* proven machinery.

---

## Folder model (resolved — see ADR-034)

```
extractors_v2_base/        ← the CONTRACT (baked into the Docker image): base.py, enums, config
                              trial code does `import extractors_v2_base`; NEVER changes with output
extractors_v2/             ← GENERATED extractors (the agent's OUTPUT): {company}.py
                              what production imports; written on the HOST; NEVER baked into the image
extractor_agent/           ← the agent (host-only brain + sandbox harness)
```
Generated code lives in `extractors_v2/` (outside the baked folder) so **sandbox rebuilds stay clean** — generated output never pollutes the contract image.

---

## What 8C builds

```
backend/extractor_agent/
├── discover.py    # the agent loop (host brain): structured LLM turn → run tool → observe → retry
├── prompts.py     # the logo-discovery system prompt
├── tools.py       # the tool implementations: run_trial(code), read_file(path)
├── apply.py       # scoped, create-only host file writer (write the generated {company}.py)
├── report.py      # structured terminal stepping + a record file (the audit)
└── generated/{company}/run.json   # record file (gitignored) — what the agent did
```

---

## Agent shape (resolved)

- **Plan-and-Execute (outer) + ReAct (inner).** The full Phase-8 task is multi-stage with a
  *knowable* plan (logo → discover fetch-all → validate a JD), but *within* each stage it's
  **ReAct** (trial → observe → retry — we don't know what a trial returns until we run it).
- **8C builds only the inner ReAct loop for ONE stage (logo).** The outer plan turn is deferred
  to 8D (where there are multiple stages). The system prompt may state the plan but is told it
  **can skip stages** that don't apply (8C = logo only).
- Same family as the 7C chat ReAct agent — reuse that understanding; the difference is the tools.

## Structured LLM output (the terminal UX)

Each LLM turn returns **structured JSON** (forced, like the eval judge) carrying both an internal
part and a terminal part — in ONE response (Claude returns reasoning + action together natively;
we just shape it):
```json
{
  "thought":  "internal reasoning (kept in context for the next turn)",
  "summary":  "checking og:image meta tag",          // printed to terminal with a step index
  "action":   { "tool": "run_trial", "args": {...} } // or {"tool": "done", "result": {...}}
}
```
The CLI prints `[step N] summary` per turn → the **observable step-by-step** the user wants.

## Tools (the schema)

Not just "run code" — the agent can also examine:
- **`run_trial(code)`** — execute discovery python in the Docker sandbox (8B), get JSON back. The "act".
- **`read_file(company)`** — show the current generated `extractors_v2/{company}.py` (examine before writing). (More relevant in 8D; included for completeness.)

---

## The flow

```
jcompany <company> <careers_url>     (root dev.sh)
Agent (host brain, autonomous, ReAct inner loop):
  - LLM turn → {thought, summary, action} → print "[step N] summary"
  - action run_trial(code): "fetch the page, find og:image / favicon / logo <img>"
       → Docker sandbox runs it → returns candidate logo URL(s)
  - observe → retry a different approach if needed (bounded iterations)
  - converge → action "done" with the logo URL
Validate:  URL reachable + is an image (a final run_trial HEAD/content-type check)
Apply (i2): write LOGO_URL into extractors_v2/{company}.py (HOST, uncommitted) via apply.py
Report:    terminal summary (url, confidence) + record file (the trial log)
Review:    human runs `git diff extractors_v2/{company}.py` → keep or `git checkout` to revert
Test:      elogo <company>   → prints the discovered LOGO_URL
```

### Build in two iterations
- **8C-i1 (first):** the ReAct loop + sandbox + structured terminal stepping → **PRINT** the discovered logo (no file write). Proves loop + Docker + structured output + terminal UX.
- **8C-i2 (then):** add the scoped create-only write (`apply.py` → `extractors_v2/{company}.py`) + record file + git-diff review. Proves the write + review path.

---

## `apply.py` — scoped create-only writer (reused in 8D)
- Writes **only** within `extractors_v2/` (path validated — refuse anything outside).
- **Create-only by default** (refuse to overwrite a filled value unless `--force`) — git is the safety net, but don't clobber silently.
- Built here, reused for the bigger `_fetch_all_jobs` write in 8D.

---

## Why logo first
- **Trivial discovery** (logo is in the page HTML — `og:image`/favicon) → ≤2 trials usually. Debug the *plumbing*, not a hard task.
- **Exercises every layer**: ReAct loop, Docker `run_trial`, structured output, scoped writer, reporting, dev.sh. If logo works end-to-end, 8D is "same pipeline, harder prompt + the outer plan".
- **No DB change**: no logo field exists in the schema — output is `LOGO_URL` in a generated class + a record file. No migration.

---

## Acceptance
- [ ] `jcompany <company> <url>` runs the full flow with **observable step-by-step** terminal output.
- [ ] Agent discovers a plausible logo URL via sandboxed trial(s).
- [ ] Validation confirms it's a reachable image.
- [ ] (i2) `LOGO_URL` written into `extractors_v2/{company}.py` (uncommitted) — visible in `git diff`.
- [ ] Terminal summary + record file produced.
- [ ] `elogo <company>` prints it.
- [ ] Bad/failed discovery → reported clearly (confidence: needs-review/failed), nothing garbage written.

---

## Decisions
| Decision | Choice |
|---|---|
| Agent shape | **ReAct inner** (8C); Plan-and-Execute outer added in 8D |
| LLM output | **Forced structured JSON** `{thought, summary, action}` — reason + action in one response |
| Tools | `run_trial(code)` + `read_file(company)` — run AND examine |
| Brain location | Host (has `ANTHROPIC_API_KEY`); only trial code in Docker |
| Output target | **`extractors_v2/{company}.py`** (generated; NOT `extractors_v2_base/`) — keeps the image clean (ADR-034) |
| File write | Scoped + create-only (`apply.py`) |
| Review | Git diff (uncommitted change) — no custom review UI |
| CLI | `jcompany` (root dev.sh, `j*`); `elogo`/`elist`/`ejd` are `e*` cli.sh verbs (auto-sourced) |
| Framework | Hand-rolled loop (ADR-029) unless PydanticAI clearly wins |
| Build order | i1 print-only → i2 add the file write |

---

## Next: 8D (list-all-jobs) — the hard discovery task + the outer Plan-and-Execute loop, on the same pipeline.
