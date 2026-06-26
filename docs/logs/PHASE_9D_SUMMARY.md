# Phase 9D: Continuous Integration (GitHub Actions)

**Status**: ✅ Completed
**Date**: June 26, 2026
**Goal**: Run the backend (pytest) + chat (Jest) test suites automatically on every push/PR — a **secret-free, free-tier** CI gate that blocks broken code from reaching `main`.

> Builds on **9C** (the branch/PR flow + branch-protected `main`). The CI checks produced
> here are what `jprstatus` displays and what `jland` + branch protection gate on. **No
> secrets, no AWS, no production** — runs against mocks + a throwaway Postgres in the runner.
>
> A full test audit (all 20 test files) confirmed **0 tests would hit production**, even if
> prod secrets were synced: DB tests strictly use `TEST_DATABASE_URL` (fail if absent, never
> fall back to prod `DATABASE_URL`); LLM/Voyage/AWS are mocked or faked.

---

## Overview

The repo has 20 real test files (16 backend pytest, 4 chat Jest) but **no automated CI** — tests
only run when someone remembers to run them locally. 9D adds `.github/workflows/ci.yml`: on every
push and PR to `main`, GitHub spins up a fresh runner, runs the suites, and reports pass/fail.
`main` is already PR-protected (9C); 9D adds CI as a **required status check** → a red PR can't merge.

The defining constraint is **CI must be free, fast, deterministic, and secret-free**. Three design
decisions enforce this (all validated by the test audit):

1. **Database tests get a runner-local Postgres, not a real one.** 4 tests are *integration* tests
   (`db/test_company_settings_service`, `db/test_user_service`, `mcp_server/test_protocol`,
   `mcp_server/test_tools`) — they hit a real Postgres+pgvector on purpose (real SQL, Alembic
   migrations, vector search). CI spins up a **`pgvector/pgvector:pg16` service container**, so
   `TEST_DATABASE_URL` is a hardcoded `localhost` value — **not a secret, NOT synced**. The conftest
   runs the 11 Alembic migrations against it → a **prod-architecture** schema (same extensions/tables),
   isolated per run. The other 12 tests are fully mocked/offline.
2. **No prod var is ever read by a test.** The audit confirmed DB tests use `TEST_DATABASE_URL` (not
   prod `DATABASE_URL`); LLM tests are mocked; Voyage is faked (monkeypatch); AWS/MCP tokens mocked.
   So even if all prod secrets were present, **0 tests touch production**.
3. **Paid + manual-script code is excluded.** `eval/run_eval*.py` and the discovery agent aren't
   pytest-collected (no API spend). Two *manual* scripts that make real network calls if run —
   `backend/auth/__tests__/test_auth.py` (needs a local server) and
   `backend/sourcing/__tests__/test_sourcing.py` (crawls real career sites) — are explicitly
   `--ignore`d in CI.

**Included in this phase**:
- `.github/workflows/ci.yml`:
  - Triggers on `push` + `pull_request` to `main`
  - **backend job**: `pgvector/pgvector:pg16` service container; `TEST_DATABASE_URL=localhost`;
    `pytest backend/ --ignore=auth/__tests__/test_auth.py --ignore=sourcing/__tests__/test_sourcing.py`
    (conftest runs the Alembic migrations against the runner DB)
  - **chat job**: `npm test` (Jest)
  - **frontend job**: `npm run build` (build check)
- **Add CI as a required status check** to the existing `main` branch protection (9C set
  "require PR"; 9D adds "require the CI check green to merge")
- New ADR: **ADR-038** (CI design: secret-free, Postgres-in-runner, prod-vars-never-read, paid/manual-scripts excluded)

**Explicitly excluded**:
- Any deploy (that's 9E)
- Any secret in CI — `localhost` Postgres, mocked externals; `jsyncsecrets` is **CD-only**, never CI
- Path-based selective test runs (the suite is small/fast; run all)
- Linting/formatting gates (could be added later; not in scope)

---

## Key Achievements (planned)

### 1. The CI workflow
- Three parallel jobs (backend / chat / frontend), each on a clean Ubuntu runner
- backend: `pgvector/pgvector:pg16` service → migrate (via conftest) → `pytest backend/` (2 manual scripts ignored)
- chat: install + `npm test`
- frontend: install + `npm run build`
- Reference: **ADR-038**

### 2. Secret-free by construction
- `TEST_DATABASE_URL` = `postgresql://postgres:postgres@localhost:5432/test` (hardcoded, non-secret)
- All external services (LLM, AWS, Voyage) are mocked in the included tests
- No test reads a prod var (audit-verified): LLM tests mocked, Voyage faked (monkeypatch)
- `eval/` paid scripts are not pytest-collected → never run in CI

### 3. The merge gate (turns CI from "report" into "enforce")
- 9C already requires a PR; 9D ADDS "require status checks to pass" → CI must be green to merge
- Now `jland` (9C) is backed server-side — a red PR's merge button is disabled
- A failing PR can sit on its branch but cannot reach `main`

---

## Highlights

- **CI runs *after* the commit, not before.** Pushing doesn't block — CI reports pass/fail on the
  commit/PR. The *enforcement* point is the **PR merge** (via branch protection), which is why the
  branch/PR flow (9C) is the prerequisite for CI to actually protect `main`.
- **Integration tests need a DB, not a secret.** Spinning up Postgres *in the runner* gives each
  run a fresh, isolated database with a public `localhost` URL — keeping CI secret-free while still
  exercising the real SQL/pgvector path the db/mcp tests require.
- **Cost safety is structural, not incidental.** The paid code (`eval/`, agent) is excluded *by
  not being test files* and *by never being added to the workflow* — so an accidental push can't
  trigger an API-spend. Paid work stays manual (`workflow_dispatch`), write-access-gated.
- **Free on minutes.** Public repo → unlimited Actions minutes; private → 2,000/month (≈400 runs
  at ~5 min/run — far beyond solo usage). Either way, effectively free.

---

## Testing & Validation

**Verified end-to-end** (PR #5 was the first real CI run):
- [x] Opened PR #5 → CI ran all 3 jobs on fresh runners
- [x] `jprstatus` showed real check results (🟡 → ✓/✗)
- [x] Iterated red → green (CI caught real bugs; see below), then all 3 jobs passed
- [x] `ci.yml` references **no** `ANTHROPIC_API_KEY` / AWS creds — DB is hardcoded `localhost`
- [x] `eval/` and the discovery agent are not pytest-collected → never invoked by CI
- [x] **Merge gate enforced**: CI added as **required status checks** on `main` branch
      protection (`backend (pytest)`, `chat (node --test)`, `frontend (build)`) → a red PR's
      merge button is now disabled server-side (not just `jland`'s client-side gate)

**CI caught 4 real "works-locally-fails-in-clean-env" bugs** on the first run — exactly the value
of CI (a clean runner with no `.env.local` and no ambient vars surfaced what local runs masked):
1. `from main import app` → `ModuleNotFoundError` (CI rootdir ≠ `backend/`) → fixed via
   `pythonpath = .` in `pytest.ini`
2. `Settings` validation: `SECRET_KEY` + `GOOGLE_CLIENT_ID` required but unset → dummy non-secret
   placeholders in `ci.yml` `env:` (tests mock real usage)
3. `chat` test #14 assumed `MCP_SERVER_URL` was set (ambient locally, absent in CI) → made the
   test **hermetic** (sets both vars it depends on)
4. `frontend` `npm ci` rejected a stale Create-React-App lockfile → switched to lenient
   `npm install` (the same approach Vercel's build uses)

Plus a pre-existing **stale test** surfaced and fixed: `title_filters` asserted `include: None`
but the code normalizes to `[]` (the test was wrong, the code was right).

---

## Next Steps → Phase 9E

Continuous Deployment — run **`terraform apply`** (the deploy mechanism from 9A) in GitHub
Actions on merge to `main`, with `TF_VAR_*` from GitHub Secrets. CI (9D) gates the PR; CD (9E)
ships the merged result. The frontend is already CD via Vercel's GitHub integration.

---

## File Structure

```
jh/
├── .github/
│   └── workflows/
│       └── ci.yml         # push/PR → backend pytest (+ runner Postgres) | chat | frontend build
└── backend/
    └── pytest.ini         # pythonpath, `manual` marker, testpaths (CI test discovery)
```

**Key files**:
- `.github/workflows/ci.yml` — the CI workflow (new)
- [backend/db/__tests__/conftest.py](../../backend/db/__tests__/conftest.py) — the DB fixture CI satisfies via runner Postgres

---

## Key Learnings

- **CI reports; branch protection enforces.** Tests run after the commit; the merge gate is what
  keeps `main` green — which is why the PR flow (9B) had to come first.
- **A database is not a secret.** Integration tests need a real Postgres, but a runner-local one
  has a public `localhost` URL → CI stays secret-free. Reserve real secrets for deploy (9E); jsyncsecrets is CD-only.
- **Cost control belongs in CI scope.** Keep paid/slow/non-deterministic work (LLM eval, the agent)
  out of auto-CI and behind manual, write-access-gated triggers — so automated runs are always free.
- **CI's value is the clean environment.** The first run caught 4 bugs that passed locally — all
  "works on my machine" cases (import paths, ambient env vars, a stale lockfile) that only surface
  in a runner with no `.env.local` and no leftover shell state. A green local test ≠ a green CI.
- **`AIzaSy…` is not automatically a secret.** Google has *server* keys (sensitive) and *browser/
  client* keys (public by design, referrer-restricted). A scraped third-party Picker key in a test
  fixture tripped GitHub's scanner but is a false positive — pattern ≠ exposure.

---

## References

- GitHub Actions services (Postgres in runner): https://docs.github.com/actions/using-containerized-services/creating-postgresql-service-containers
- Branch protection rules: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
