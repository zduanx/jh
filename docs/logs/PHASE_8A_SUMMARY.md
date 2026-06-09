# Phase 8A: extractors_v2 Framework (the agent's contract)

**Status**: ✅ Completed
**Date**: June 8, 2026
**Goal**: A new, **self-contained** `extractors_v2/` framework that defines the contract the discovery agent codes against — minimal, import-clean (so it can be the *only* thing inside the Docker sandbox), and structured around consts that are **pending fill-in** by the agent.

> **Result:** built + all acceptance criteria pass. `extractors_v2/` has **zero imports
> from the rest of `backend/`** (verified) → Docker-sandbox-ready. `base.py` defines the
> `_fetch_all_jobs` abstract contract + `LOGO_URL` const + generic wrappers; a hand-filled
> class runs end-to-end (fetch → title-filter → build URLs). `Company`/`TitleFilters`
> carried from v1; `companies/_template.py` is the agent's output shape; `cli.sh` stub ready.

> Phase 8 overview + all design decisions live across the sub-phase docs
> (8A framework · 8B sandbox · 8C logo skeleton · 8D list-jobs). A full
> PHASE_8_SUMMARY is assembled at the end.

---

## Why a v2 framework (not reuse `extractors/`)

- **Isolation**: the existing `extractors/` stays untouched (production). `extractors_v2/` is the agent's playground — no risk to the live pipeline.
- **The Docker sandbox can contain ONLY this folder.** That's the core constraint: the agent's trial code *extends the base class*, so the base class must be in the container — but **nothing else** (no secrets, no rest-of-backend). Therefore `extractors_v2/` **must be import-clean of the rest of `backend/`** (no `from db...`, no `from config.settings...`). This is the defining requirement of 8A.
- **Fresh, simpler shape**: we don't replicate the existing extractor precisely. v2 is organized around **consts the agent fills in** (`LOGO_URL` in 8C, the list-jobs approach in 8D), so the agent's job is "discover the value, write it into the class."

---

## What 8A builds

### Folder layout
```
backend/extractors_v2/
├── __init__.py
├── base.py            # the self-contained base class (the contract)
├── enums.py           # Company enum (carried from v1, trimmed)
├── config.py          # TitleFilters (carried from v1 — already dependency-free)
├── companies/         # one file per company; consts PENDING FILL-IN by the agent
│   └── __init__.py
└── cli.sh             # local test verbs (e.g. `elogo <company>`) — added incrementally
                       #   (named cli.sh, NOT dev.sh, to avoid confusion with the root dev.sh)
```

### `base.py` — the contract (stripped + self-contained)
Carries the *essential* shape from v1's `base_extractor.py` but **dependency-free**:
- Class vars the agent fills: `COMPANY_NAME`, `LOGO_URL` (8C), `API_URL` / list-approach (8D).
- `async def _fetch_all_jobs() -> list[dict]` — **the abstract method the agent's discovered code implements** (returns `{id, title, location, response_data}` job dicts). This is the heart of what the agent produces.
- Generic wrappers carried over (so a filled-in class is runnable): `extract_source_urls_metadata()` (applies title filters, builds URLs), `crawl_raw_info(url)` (generic page fetch). These stay as-is — only `_fetch_all_jobs` is company-specific.
- **No imports outside `extractors_v2/` + stdlib + httpx.** (httpx is the only third-party dep, and it's what the trial code uses too.)

### `enums.py` / `config.py`
- `Company` enum — carried from v1 (it's already self-contained). May start trimmed and grow as v2 companies are added.
- `TitleFilters` — carried verbatim from v1 `config.py` (already dependency-free: stdlib `dataclass` only).

### `companies/{company}.py` — the agent's output target
- A minimal class per company, e.g.:
  ```python
  class GoogleV2(BaseExtractorV2):
      COMPANY_NAME = Company.GOOGLE
      LOGO_URL = None          # ← PENDING: filled by the agent (8C)
      # _fetch_all_jobs        # ← PENDING: discovered by the agent (8D)
  ```
- The agent's "outcome code" = filling these in. Git diff on this file = the review.

---

## Key requirements / acceptance

- [ ] `extractors_v2/` imports **nothing** from the rest of `backend/` (verify: `grep -r "from db\|from config\|from api\|from models" extractors_v2/` → empty). This is what makes the minimal Docker image possible (8B).
- [ ] `base.py` defines `_fetch_all_jobs` (abstract) + the generic wrappers; a hand-filled company class is runnable end-to-end (fetch → list → URLs).
- [ ] `Company` enum + `TitleFilters` available, dependency-free.
- [ ] A company class shape with `LOGO_URL = None` (pending) + a TODO `_fetch_all_jobs` — the fill-in targets for 8C/8D.
- [ ] `extractors_v2/cli.sh` stub exists (verbs added in 8C+).

---

## Decisions specific to 8A

| Decision | Choice |
|---|---|
| Reuse v1 base? | **No — fresh, stripped, self-contained** v2 base. Carry the *shape* (`_fetch_all_jobs`, the wrappers), drop the coupling. |
| Sync vs async | Keep **async** (`_fetch_all_jobs` is async in v1; httpx async) — matches v1 + the real pipeline. |
| Third-party deps in v2 | **httpx only** (what trial code needs anyway). No DB/SQLAlchemy/pydantic-settings. |
| Company class granularity | **One file per company** under `companies/` — clean diffs, the agent writes one file. |

---

## Out of scope for 8A (later sub-phases)
- The Docker image / sandbox harness → **8B**.
- The agent loop + logo discovery → **8C**.
- `_fetch_all_jobs` actual discovery (list jobs) → **8D**.
- Wiring v2 into the live ingestion pipeline → roadmap (never, for the portfolio).

---

## Next: 8B (Docker sandbox harness) — needs Docker installed (not currently on this machine).
