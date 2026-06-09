# Phase 8C: Logo Walking-Skeleton (the first agent slice)

**Status**: 📋 Planning
**Date**: June 8, 2026
**Goal**: The thinnest end-to-end agent slice — given a company + careers URL, **discover the company logo URL** and write it into the company class (uncommitted). The *task* is trivial; the point is to **wire every layer** (agent loop · sandboxed trials · scoped file write · validation · reporting · dev.sh) on an easy task, before scaling to the hard one (8D).

> Walking-skeleton-first: prove the whole pipeline on "find the logo", then 8D makes
> the *task* harder ("list all jobs") through the *same* proven machinery.

---

## What 8C builds

```
backend/extractor_agent/
├── discover.py         # the autonomous loop (host brain): trial → run_trial() → observe → retry
├── prompts.py          # the logo-discovery prompt
├── apply.py            # scoped, create-only host file writer (write LOGO_URL into the class)
├── report.py           # terminal summary + record file
└── generated/{company}/ # record files (gitignored) — the audit of what the agent did
```

### The flow
```
Input:  company name + careers URL
Agent (autonomous, host-side brain):
  - LLM proposes a trial: "fetch the page, find og:image / favicon / logo <img>"
  - run_trial(code) in Docker (8B)  → fetches the page, returns candidate logo URL(s)
  - observe: found? ambiguous? none? → maybe retry with a different approach
  - converge on a logo URL
Validate:  the URL is reachable + is an image (HEAD/content-type check, in sandbox)
Apply:     write LOGO_URL = "<url>" into extractors_v2/companies/{company}.py  (uncommitted)
Report:    terminal summary (url, source, confidence) + record file (trial log)
Review:    human runs `git diff` → keep or `git checkout` to revert
Test:      extractors_v2/cli.sh elogo <company>  → prints the discovered logo
```

### `apply.py` — scoped create-only writer (reused in 8D)
- Writes **only** within `extractors_v2/companies/` (path validated — refuse anything outside).
- **Create-only by default** (refuse to overwrite an existing filled value unless `--force`) — git is the safety net, but don't clobber silently.
- This helper is built here and reused for the bigger `_fetch_all_jobs` write in 8D.

---

## Why logo first
- **Trivial discovery** (logo is in the page HTML — `og:image`/favicon) → the agent almost always one-shots or needs ≤2 trials. Lets us debug the *plumbing*, not fight a hard task.
- **Exercises every layer**: the loop, Docker `run_trial`, the scoped writer, validation, reporting, dev.sh. If logo works end-to-end, 8D is "same pipeline, harder prompt."
- **No DB change**: there is **no logo field in the schema today** — output is a `LOGO_URL` const in the class + a record file. No migration. Keeps the slice thin.

---

## Acceptance
- [ ] `egen-logo <company> <url>` (root dev.sh, or extractors_v2/cli.sh) runs the full flow.
- [ ] Agent discovers a plausible logo URL via sandboxed trial(s).
- [ ] Validation confirms it's a reachable image.
- [ ] `LOGO_URL` written into `companies/{company}.py` (uncommitted) — visible in `git diff`.
- [ ] Terminal summary + record file produced.
- [ ] `extractors_v2/cli.sh elogo <company>` prints it.
- [ ] Bad/failed discovery → reported clearly (confidence: needs-review/failed), nothing garbage written.

---

## Decisions
| Decision | Choice |
|---|---|
| Agent shape | Autonomous (input→outcome), bounded trial iterations |
| Brain location | Host (has `ANTHROPIC_API_KEY`); only trial code in Docker |
| Output | `LOGO_URL` const (the "code outcome") **and** a record file (the audit) |
| File write | Scoped + create-only (`apply.py`) — within `companies/` only |
| Review | Git diff (uncommitted change) — no custom review UI |
| Framework | Hand-rolled loop (ADR-029) unless PydanticAI clearly wins — decide here |

---

## Next: 8D (list-all-jobs) — the hard discovery task on the same pipeline.
