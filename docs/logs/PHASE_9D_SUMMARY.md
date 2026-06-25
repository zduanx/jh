# Phase 9D: Continuous Integration (GitHub Actions)

**Status**: 📋 Planning
**Date**: June 24, 2026
**Goal**: Run the backend (pytest) + chat (Jest) test suites automatically on every push/PR — a **secret-free, free-tier** CI gate that blocks broken code from reaching `main`.

> Builds on **9B** (the branch/PR flow). The CI checks produced here are what `jprstatus`
> displays and what `jland` + branch protection gate on. **No secrets, no AWS, no
> production** — runs against mocks + a throwaway Postgres in the runner.

---

## Overview

The repo has ~20 real test files (backend pytest, chat Jest) but **no automated CI** — tests only
run when someone remembers to run them locally. 9C adds `.github/workflows/ci.yml`: on every push
and PR to `main`, GitHub spins up a fresh runner, runs the suites, and reports pass/fail. Combined
with **branch protection** on `main`, a red PR cannot be merged.

The defining constraint is **CI must be free, fast, deterministic, and secret-free**. Two design
decisions enforce this:

1. **Database tests get a runner-local Postgres, not a real one.** The 5 db/mcp_server tests are
   *integration* tests — they hit a real Postgres+pgvector on purpose (real SQL, real Alembic
   migrations, real vector search; none of which can be mocked). CI spins up a **Postgres service
   container inside the runner**, so `TEST_DATABASE_URL` is a hardcoded `localhost` value — **not a
   secret.** The rest of the suite is fully mocked.
2. **Paid/LLM code is excluded from CI.** The only money-burning scripts (`eval/run_eval*.py`,
   the discovery agent) are *not* test files (not collected by pytest) and are **never** added to
   the auto-run CI. They stay behind the manual `workflow_dispatch` / local path. So CI never spends
   API credits.

**Included in this phase**:
- `.github/workflows/ci.yml`:
  - Triggers on `push` + `pull_request` to `main`
  - **backend job**: Postgres+pgvector service container → run Alembic migrations → `pytest backend/`
  - **chat job**: `npm test` (Jest)
  - **frontend job**: `npm run build` (build check)
  - Explicitly scoped to `__tests__/` — excludes `eval/` and the agent
- **Branch protection** on `main` (one-time GitHub UI step) — require the CI check green to merge
- New ADR: **ADR-037** (CI design: secret-free, Postgres-in-runner, paid-code excluded)

**Explicitly excluded**:
- Any deploy (that's 9E)
- Any secret in CI (the whole point — `localhost` Postgres, mocked externals)
- Path-based selective test runs (the suite is small/fast; run all)
- Linting/formatting gates (could be added later; not in scope)

---

## Key Achievements (planned)

### 1. The CI workflow
- Three parallel jobs (backend / chat / frontend), each on a clean Ubuntu runner
- backend: `services: postgres` (with pgvector) → migrate → `pytest backend/`
- chat: install + `npm test`
- frontend: install + `npm run build`
- Reference: **ADR-037**

### 2. Secret-free by construction
- `TEST_DATABASE_URL` = `postgresql://postgres:postgres@localhost:5432/test` (hardcoded, non-secret)
- All external services (LLM, AWS, Voyage) are mocked in the included tests
- The one live LLM test auto-skips without `ANTHROPIC_API_KEY` (which CI does not provide)
- `eval/` paid scripts are not pytest-collected → never run in CI

### 3. The merge gate (turns CI from "report" into "enforce")
- Branch protection on `main`: "require status checks to pass before merging"
- Now `jland` (9B) is backed server-side — a red PR's merge button is disabled
- A failing PR can sit on its branch but cannot reach `main`

---

## Highlights

- **CI runs *after* the commit, not before.** Pushing doesn't block — CI reports pass/fail on the
  commit/PR. The *enforcement* point is the **PR merge** (via branch protection), which is why the
  branch/PR flow (9B) is the prerequisite for CI to actually protect `main`.
- **Integration tests need a DB, not a secret.** Spinning up Postgres *in the runner* gives each
  run a fresh, isolated database with a public `localhost` URL — keeping CI secret-free while still
  exercising the real SQL/pgvector path the db/mcp tests require.
- **Cost safety is structural, not incidental.** The paid code (`eval/`, agent) is excluded *by
  not being test files* and *by never being added to the workflow* — so an accidental push can't
  trigger an API-spend. Paid work stays manual (`workflow_dispatch`), write-access-gated.
- **Free on minutes.** Public repo → unlimited Actions minutes; private → 2,000/month (≈400 runs
  at ~5 min/run — far beyond solo usage). Either way, effectively free.

---

## Testing & Validation (planned)

**Manual** (prove the gate works):
- [ ] Push a branch → CI runs, all suites green
- [ ] Open a PR with a deliberately failing test → CI red → merge button blocked
- [ ] `jprstatus` (9B) now shows real check results
- [ ] Fix the test, push → CI re-runs green → merge unblocked
- [ ] Confirm no `ANTHROPIC_API_KEY` / AWS creds are referenced anywhere in `ci.yml`
- [ ] Confirm `eval/` and the agent are not invoked by the workflow

---

## Next Steps → Phase 9E

Continuous Deployment — run **`terraform apply`** (the deploy mechanism from 9A) in GitHub
Actions on merge to `main`, with `TF_VAR_*` from GitHub Secrets. CI (9D) gates the PR; CD (9E)
ships the merged result. The frontend is already CD via Vercel's GitHub integration.

---

## File Structure (planned)

```
jh/
└── .github/
    └── workflows/
        └── ci.yml    # push/PR → backend pytest (+ runner Postgres) | chat Jest | frontend build
```

**Key files**:
- `.github/workflows/ci.yml` — the CI workflow (new)
- [backend/db/__tests__/conftest.py](../../backend/db/__tests__/conftest.py) — the DB fixture CI satisfies via runner Postgres

---

## Key Learnings

- **CI reports; branch protection enforces.** Tests run after the commit; the merge gate is what
  keeps `main` green — which is why the PR flow (9B) had to come first.
- **A database is not a secret.** Integration tests need a real Postgres, but a runner-local one
  has a public `localhost` URL → CI stays secret-free. Reserve real secrets for deploy (9E).
- **Cost control belongs in CI scope.** Keep paid/slow/non-deterministic work (LLM eval, the agent)
  out of auto-CI and behind manual, write-access-gated triggers — so automated runs are always free.

---

## References

- GitHub Actions services (Postgres in runner): https://docs.github.com/actions/using-containerized-services/creating-postgresql-service-containers
- Branch protection rules: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
