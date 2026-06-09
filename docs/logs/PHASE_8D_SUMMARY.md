# Phase 8D: List-All-Jobs Discovery (the hard task)

**Status**: ✅ Completed
**Date**: June 9, 2026
**Goal**: Scale the proven 8C agent to the **real, hard task** — autonomously discover a company's "list all jobs" mechanism (which API/endpoint, headers, pagination), produce a working `_fetch_all_jobs()` returning the contract dicts, **verify it end-to-end**, and have the agent write the verified code into the company's extractor for review.

> **Result:** the agent onboarded **5 real companies across 4 different ATS systems** — including cracking a **custom WordPress endpoint** (HRT) and **pagination** (Netflix) — each producing **verified, runnable, production-usable** extractors. Counts matched manual verification.

---

## Results — 5 companies, 4 ATSs, all verified via `elist`

| Company | ATS / mechanism | Discovery difficulty | Filtered jobs | `elist` works |
|---|---|---|---|---|
| **anthropic** | Greenhouse (`boards-api...`) | easy (signature in HTML) | 375 | ✅ |
| **openai** | Ashby (`posting-api...`, tried blind) | medium | 128 | ✅ |
| **roblox** | Greenhouse `?content=true` (blind slug) | medium | 110 | ✅ |
| **netflix** | Eightfold (`/api/apply/v2/jobs`, **paginated** 533) | harder | 120 | ✅ |
| **hrt** | **custom WP plugin** (`admin-ajax.php`, read the JS bundle + `setting` DOM blob) | hardest | ~8–11 | ✅ |

All counts matched the manual verification done first by hand. Each generated extractor loads via the registry and returns jobs **with full job URLs** (verified by `elist <company>`).

---

## What 8D built (on top of 8A–8C)

8C already had the agent (plan-execute, sandboxed `run_trial`, read/write file tools, registry, Pydantic validation). 8D added **new stages + the job contract + verification verbs** — **no new infrastructure**.

### New stages (entries in `_STAGE_INSTRUCTIONS`)
- **`fetch_jobs`** — discover how to enumerate ALL jobs. The hard ReAct stage: identify the ATS → hit its public API (or read the JS bundle for a custom endpoint) → paginate if needed → map per-ATS fields → filter client-side. Returns a `code` string (the `_fetch_all_jobs` body). Prompt encodes the **discovery ladder** + an ATS-API cheat-sheet (Greenhouse/Ashby/Eightfold/Lever/Workday) + a **symptom→fix table** for custom endpoints.
- **`validate_jd`** — proves the discovered code works END-TO-END *before* it's written: the trial code IS the extractor class (extends the baked `BaseExtractorV2`), runs `_fetch_all_jobs`, then crawls one job's `url` via the framework's `crawl_raw_info`. The LLM judges "is this a real JD for this company?" Returns `verified_code` — the exact body that just worked. This stage also **makes `extractors_v2_base` actually used** in the sandbox (it was dead weight before).

Full onboarding plan: `["validate_company","icon","fetch_jobs","validate_jd","write_extractor"]`.

### Contract change: explicit `url` field
Job dicts are now `{id, title, location, url, response_data}`. The **job URL is extracted per-ATS** (Greenhouse `absolute_url`, Ashby `jobUrl`, Eightfold `canonicalPositionUrl`, HRT card `href`) — NOT constructed from a prefix. Dropped the vestigial `URL_PREFIX_JOB` (URLs are slug- or id-based and vary; they're always present in the listing data). Added `INPUT_CAREER_URL` (provenance).

### Verification verbs (`elist` / `ejd`)
- **`elist <company> [--all|--json]`** — load the generated extractor via the registry, run `_fetch_all_jobs` → print jobs (id · location · title · **full url**) + count. The "did it work?" check.
- **`ejd <company> <job_url>`** — fetch a job page via `crawl_raw_info` → print the raw JD source.

### Per-stage step budgets
`run_stage` is generic; it looks up the prompt + cap by stage name. Caps: validate_company=4, icon=8, fetch_jobs=18, validate_jd=5, write_extractor=8. Two-tier: prompt sets a soft target (~10), code allows more (18) so a hard stage isn't killed mid-discovery.

### Prompt caching (token efficiency)
The (detailed, stable) stage system prompt is cached (`cache_control: ephemeral`) → the rich ATS guidance costs ~nothing after turn 1, so the agent can go straight to the right API instead of exploring blindly. (Each ReAct turn re-sends the whole conversation, so cutting round-trips matters more than prompt size.)

---

## Key findings (debugged from real runs — see [agent-discovery-prompts.md](../learning/agent-discovery-prompts.md))

Each was found by watching a run fail, then fixing the prompt or harness:
1. **Judgment vs. control flow** — `validate_company` judged `valid:false` but returned `done` → pipeline continued. Fix: CODE enforces `valid:false → stop`; the LLM only judges.
2. **Loose prompts for judgment** — a rigid name↔domain match false-rejected real companies (Google@abc.xyz, ATS domains). Fix: confidence-based judgment with a bias-to-allow.
3. **Verify == ship** — `validate_jd` fixed a `self.client` bug in its trial but the OLD broken code got written. Fix: `validate_jd` emits `verified_code`; `write_extractor` writes THAT.
4. **`self.client` hallucination** — the base class has no client. Fix: prompt says "make your own `httpx.AsyncClient()`; only `self.INPUT_CAREER_URL`."
5. **Dropped `url`** — the agent captured the url while parsing but omitted it from the final return. Fix: `url` mandated in the returned dict.
6. **Rabbit holes** — HRT chased the server-side filter (18 steps); OpenAI's icon chased Wayback/cache. Fix: encode the shortcut ("fetch-all-then-filter-locally"; "try /favicon.ico directly, don't over-explore").
7. **Custom-endpoint unlock** — HRT's WP `admin-ajax` needed the `setting` DOM blob; a 500 = missing param. Fix: a symptom→fix table in the prompt.
8. **Context trimming backfired** — compacting old JS-bundle results forced re-fetches. Fix: trimming OFF (correctness first).

---

## The hard parts (where real agent value showed)
- **HRT** (hardest): no public API. The agent read the JS bundle, found the custom `get_hrt_jobs_handler` action, discovered the required `setting` param (a DOM `data-filters-settings` blob), reconstructed the exact POST, parsed `data-term`-encoded filters, filtered client-side — autonomously. This is the genuine "autonomous coding agent" payoff: reverse-engineering an unknown endpoint from failures + the JS.
- **Netflix**: handled pagination (533 jobs across pages) correctly, untaught-by-example, hitting the exact 120.
- **Parsing stays runtime-LLM** — the agent discovers *listing*; JD parsing is a separate runtime concern (`crawl_raw_info` returns raw text; `validate_jd` confirms it's a JD).

---

## Acceptance — status
- [x] For companies NOT in `extractors_v2/`, the agent discovers a working `_fetch_all_jobs` via sandboxed trials + writes it (+ registers). (5 companies, 4 ATSs.)
- [x] `elist <company>` returns a sane job list with full URLs. (All 5.)
- [x] `validate_jd` confirms a real JD for the company before writing (via the framework's `crawl_raw_info`).
- [x] Generated code written to `extractors_v2/{company}.py` (uncommitted) — reviewable via git diff; **the written code is the VERIFIED code**.
- [x] Failure → reported (OpenAI's first icon attempt failed cleanly at the step cap; nothing garbage written).
- [x] Observable step-by-step (`[stage - step N]`), full LLM-I/O via `--d`, gitignored run logs.

---

## Known limitations / non-priorities
- **Parallel `jcompany` → registry race** — concurrent runs read-modify-write the shared `registry.py`; a later write clobbers an earlier entry (lost update). Extractor files are fine (distinct names); only the shared registry collides. **Run sequentially.** (Not a priority; future fix: auto-discover files instead of editing a shared registry.)
- **Netflix `elist` is slow (~28s)** — Eightfold caps page size, so ~53 sequential requests to fetch 533 jobs before filtering to 120. Correct, just slow (a caching layer could help).
- **Playwright** — purely-JS sites with no API would need it (8B add-on); none of the 5 did.

---

## Next: 8E — Prompt / Context / Harness Engineering
Systematic improvement of the agent (see [PHASE_8E_SUMMARY](PHASE_8E_SUMMARY.md)). The 8D findings are the raw material — turn the ad-hoc fixes into a deliberate methodology.
