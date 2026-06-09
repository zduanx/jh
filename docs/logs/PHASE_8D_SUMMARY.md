# Phase 8D: List-All-Jobs Discovery (the hard task)

**Status**: 📋 Planning
**Date**: June 8, 2026
**Goal**: Scale the proven 8C pipeline to the **real, hard task**: the agent autonomously discovers a company's "list all jobs" mechanism (which API endpoint / network link / pagination / browser headers), produces a working `_fetch_all_jobs()` that returns `list[dict]`, verifies it, and writes it into the company class for human review.

> Same machinery as 8C (loop · sandbox · scoped write · report · dev.sh) — just a much
> harder *task*, requiring real trial-and-error discovery.

---

## What 8D builds (on top of 8A–8C)

### The discovery task
```
Input:  company name + careers/list URL
Agent (autonomous, sandboxed trials):
  - hypothesize how to enumerate jobs:
      • plain GET the URL? → empty/JS-only?
      • inspect for an underlying JSON API (the real source)?
      • needs browser-like headers / a token?
      • paginated? what's the pattern?
  - write a TRIAL _fetch_all_jobs implementation → run_trial() in Docker → observe
      (returned jobs? 403? empty? JS-rendered? partial?)
  - ITERATE: rewrite the approach based on what failed   (the genuine coding loop)
  - converge → a working _fetch_all_jobs returning list[dict] of {id,title,location,response_data}
Verify (the eval/gate):
  - the discovered code returns jobs (count > 0, sane N — not 1, not 10000)
  - a sample job page can be fetched (crawl_raw_info) + LLM-parses to a valid JD (Pydantic)
Apply:  write _fetch_all_jobs into extractors_v2/companies/{company}.py (uncommitted)
Report: summary (approach, sample jobs, confidence) + record file (full trial log)
Review: git diff → keep or revert
```

### Verification tools (`elist` / `ejd`)
Added here (deferred from earlier — they need a list-task to verify):
- **`elist <company>`** — run the discovered `_fetch_all_jobs` → print the job list + count. The agent's primary "did it work?" check.
- **`ejd <company> <job_url>`** — fetch a job page + LLM-parse → print the JD. Verifies the runtime-LLM parsing path (no per-company `extract_raw_info`).
- These are the agent's **verification tools** (it calls them to grade its own trials) and also human-facing dev.sh verbs.

---

## The hard parts (where real agent value is)
- **Discovery is trial-heavy** — the agent must explore (network inspection, header tricks, pagination) with real failures and retries. This *is* the "autonomous coding agent": write → run → observe → fix.
- **Browser emulation**: HTTP + browser-like headers covers most career APIs. A site that's purely JS-rendered needs Playwright (the 8B add-on) — if a target needs it, that's a documented escalation, possibly "needs custom logic → human."
- **Parsing stays runtime-LLM** — the agent does NOT generate a parser; `ejd` proves a page LLM-parses to a JD. Keeps the agent's job to *discovery* only.

---

## Acceptance
- [ ] For a company NOT in `extractors_v2/`, the agent discovers a working `_fetch_all_jobs` via sandboxed trials.
- [ ] `elist <company>` returns a sane job list (count > 0).
- [ ] `ejd <company> <url>` returns a valid LLM-parsed JD (Pydantic-validated).
- [ ] Code written to `companies/{company}.py` (uncommitted) — reviewable via git diff.
- [ ] Gating: strong pass → confidence high; clear fail → iterate (bounded) or report failed; genuinely-stuck (e.g. JS-only) → escalate-to-human note, nothing garbage written.
- [ ] Full trial log in the record file (the audit of what was tried).

---

## Decisions / open questions
- **Gating thresholds** — what job count is "sane"? (per-company varies — use ">0 and not absurd" + human review for borderline).
- **Bounded iterations** — cap trials (e.g. 8–10) then escalate, to avoid runaway cost.
- **Escalation** — JS-only / weird-auth sites: report "needs custom logic" rather than force a bad extractor (keeps honesty; some sites genuinely need hand-coding).
- **Demo target** — pick a company with a clean JSON API (likely one already in `trials/`) for the end-to-end demo; note that JS-heavy sites are the escalation case.

---

## After 8D
- **Demo end-to-end** (a fresh company, watch trials → converge → review diff).
- **Assemble PHASE_8_SUMMARY** from 8A–8D (the overall phase doc, with the JD-coverage map → in memory, not the public doc).
