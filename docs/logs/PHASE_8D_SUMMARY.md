# Phase 8D: List-All-Jobs Discovery (the hard task)

**Status**: 📋 Planning
**Date**: June 9, 2026
**Goal**: Scale the proven 8C agent to the **real, hard task**: autonomously discover a company's "list all jobs" mechanism (which API/endpoint, headers, pagination), produce a working `_fetch_all_jobs()` returning `list[dict]`, verify it, and have the agent write it into the company's extractor for human review.

> Same machinery as 8C (plan-execute · sandbox · read/write file tools · registry) — a much
> harder *task* requiring real trial-and-error discovery. **No new infrastructure** — new STAGES.

---

## What 8D adds (on top of 8A–8C)

8C already built the agent (plan-execute, sandboxed `run_trial`, `read_file`/`write_file` tools,
the registry, Pydantic validation, `jcompany`/`elogo`). 8D is mostly **two new stages** + their
prompts + two verification verbs.

### New stages (entries in `_STAGE_INSTRUCTIONS`)
- **`fetch_jobs`** — discover how to enumerate ALL jobs. The hard ReAct stage:
  ```
  hypothesize → write a TRIAL _fetch_all_jobs → run_trial() in Docker → observe
    (jobs returned? 403? empty? JS-only? paginated? partial?)
  ITERATE: rewrite the approach based on what failed   (the genuine coding loop)
  converge → working code returning list[dict] of {id,title,location,response_data}
  then write_file the real _fetch_all_jobs into extractors_v2/{company}.py
  ```
- **`validate_jd`** — confirm a sample job page fetches (`crawl_raw_info`) and **LLM-parses to a valid JD** (Pydantic). Proves the runtime-LLM parsing path (no per-company `extract_raw_info`).

So the plan grows from `["icon","write_extractor"]` to e.g. `["icon","fetch_jobs","validate_jd","write_extractor"]` (or `fetch_jobs` writes incrementally) — the LLM plans which stages the goal needs.

### Verification verbs (`elist` / `ejd`) — the agent's self-grading + human checks
- **`elist <company>`** — load the generated extractor (via the registry), run `_fetch_all_jobs` → print the job list + count. The "did it work?" check (mirrors `elogo`).
- **`ejd <company> <job_url>`** — fetch a job page + LLM-parse → print the JD. Verifies runtime parsing.
- The agent calls these (or their logic) to grade its own trials; they're also human-facing dev.sh/cli verbs.

---

## The hard parts (where the real agent value is)
- **Discovery is trial-heavy** — network inspection, header tricks, pagination, with real failures and retries. This *is* the autonomous coding loop: write → run in sandbox → observe → fix.
- **Browser emulation**: HTTP + browser-like headers covers most career APIs (already in `BaseExtractorV2`). A purely JS-rendered site needs Playwright (an 8B sandbox add-on) — if a target needs it, that's a documented escalation ("needs custom logic → human").
- **Parsing stays runtime-LLM** — the agent does NOT generate a parser; `validate_jd`/`ejd` prove a page LLM-parses to a JD. The agent's job is *discovery* only.
- **Writing the real `_fetch_all_jobs`** uses the SAME read/write file tools as 8C (read-before-write, scoped to `extractors_v2/`) — now editing the method body, not just a const.

---

## Acceptance
- [ ] For a company NOT yet in `extractors_v2/`, the agent discovers a working `_fetch_all_jobs` via sandboxed trials and writes it (+ registers the company).
- [ ] `elist <company>` returns a sane job list (count > 0, not absurd).
- [ ] `ejd <company> <url>` returns a valid LLM-parsed JD (Pydantic-validated).
- [ ] Generated code (incl. the real `_fetch_all_jobs`) written to `extractors_v2/{company}.py` (uncommitted) — reviewable via git diff.
- [ ] Gating: strong pass → confidence high; clear fail → bounded retry or report failed; genuinely-stuck (e.g. JS-only) → escalate-to-human note, **nothing garbage written** (the scope guard + validation enforce this).
- [ ] The agent's trials are observable step-by-step (the existing `[stage - step N]` UX).

---

## Decisions / open questions
- **Gating thresholds** — what job count is "sane"? (varies per company — use ">0 and not absurd" + human review for borderline).
- **Bounded iterations** — the existing `MAX_STEPS` cap per stage; then escalate, to avoid runaway cost.
- **Escalation** — JS-only / weird-auth sites: report "needs custom logic" rather than force a bad extractor (honesty over coverage; some sites genuinely need hand-coding).
- **Demo target** — pick a company with a clean JSON API (likely one already in v1 `extractors/` or `trials/`) for the end-to-end demo; note JS-heavy sites are the escalation case.
- **Record file** — already built in 8C (`extractor_agent/runs/{company}-{ts}.log`, gitignored). 8D's multi-trial discovery makes that audit log even more valuable; no new work needed.

---

## After 8D
- **Demo end-to-end** (a fresh company: watch trials → converge → review the diff → `elist`/`ejd`).
- **Wire `extractors_v2` into the backend** (a possible 8E): the registry-driven `list_companies` endpoint returning each generated extractor's `ICON_URL`, replacing v1's enum-driven list — so the agent's output plugs into production with no manual edits.
- **Assemble PHASE_8_SUMMARY** from 8A–8D (the overall phase doc; HRT JD-coverage map → memory, not the public doc).
