# CI/CD with GitHub Actions + Terraform (OIDC, gated deploys, rollback)

**Context**: Phase 9 built jh's full pipeline — CI (9D: tests on every PR) and CD
(9E: `terraform apply` on merge, keyless via OIDC, gated by manual approval). This
documents the non-obvious mechanics and the real traps hit while building it live.

---

## The Pipeline Shape

```
jbranch → jsave → jpr → CI (9D) → review → jland (merge) → CD (9E) → prod
                         │                                   │
              tests on a clean runner            terraform apply, gated + smoke-tested
              (required status checks)           per stack (path-filtered)
```

CI **reports**; branch protection **enforces** (a red required check disables the
merge button). CD runs *after* merge — so the enforcement point for "don't ship
broken code" is the **PR merge gate**, which is why the PR flow had to come first.

---

## OIDC: keyless AWS auth (and the `environment:` trap)

### What OIDC does
Instead of storing long-lived `AWS_ACCESS_KEY_ID` in GitHub Secrets, the runner
proves its identity with a short-lived signed token and assumes an IAM role:

```
GitHub runner → "I'm repo zduanx/jh, here's a signed OIDC token"
AWS STS       → verifies signature + trust policy → returns ~1h temp creds
terraform     → uses temp creds → deploys → creds expire automatically
```

Setup (all IaC, in `bootstrap/terraform/oidc.tf`):
1. `aws_iam_openid_connect_provider` — trust `token.actions.githubusercontent.com`
2. `aws_iam_role` with a **trust policy** scoped to the repo (+ branch/environment)
3. a permissions policy for what `terraform apply` touches

The `backend "s3"` state block has **no credentials** — Terraform uses the standard
AWS credential chain (locally: `~/.aws/credentials` as your IAM user; in CD: the
OIDC-assumed role). Same config, environment supplies the identity.

### THE TRAP: `environment:` changes the token's `sub` claim

| Job config | OIDC token `sub` claim |
|------------|------------------------|
| no environment | `repo:zduanx/jh:ref:refs/heads/main` |
| `environment: production-backend` (the gate) | `repo:zduanx/jh:environment:production-backend` |

We added `environment:` for the **approval gate** — which silently changed the
`sub`. A trust policy scoped to `ref:refs/heads/main` then **rejected** it:
`Not authorized to perform sts:AssumeRoleWithWebIdentity`. Fix:

```hcl
"token.actions.githubusercontent.com:sub" = "repo:zduanx/jh:environment:production-*"
```

Still effectively main-only, because the GitHub Environment's
`deployment_branch_policy.protected_branches` gates it to protected branches. This
gate↔trust interaction is the single most common OIDC-CD gotcha.

---

## Secrets reach Terraform as env vars, not generated files

The runner names each secret into the job env, and `terraform apply` auto-reads any
`TF_VAR_*` from the environment:

```yaml
env:
  TF_VAR_database_url: ${{ secrets.TF_VAR_DATABASE_URL }}
```

- A shell step **can** define env vars for later steps (via `$GITHUB_ENV`), and
  `terraform apply` (always the last step) reads them. Job-level `env:` is global
  from step 1; step-set vars only reach *later* steps (so order the compute step
  before apply).
- Secrets **cannot** be enumerated by name at runtime — `${{ secrets.X }}` must be
  written literally in YAML. This is a feature: it scopes each job to only its
  stack's secrets (least-privilege). Unlike SAM (which needed `generate_*.py` to
  write `template.yaml`/`samconfig.toml`), Terraform consumes env + `.tf` natively
  — no generate step.

---

## "Works locally, fails in clean CI" — the bug class CI/CD exists to catch

A clean runner has no `.env.local`, no ambient shell vars, no `node_modules`, and a
different working dir. Every assumption your machine silently satisfies becomes a
failure. The real ones this phase surfaced:

| Bug | Cause | Fix |
|-----|-------|-----|
| `ModuleNotFoundError: No module named 'main'` | CI rootdir ≠ `backend/` | `pythonpath = .` in pytest.ini |
| `Settings` validation error | `SECRET_KEY`/`GOOGLE_CLIENT_ID` unset | dummy non-secret placeholders in ci.yml `env` |
| chat test expected wrong error | test assumed ambient `MCP_SERVER_URL` was set | make the test **hermetic** (set every var it needs) |
| chat Lambda crashes: `Cannot find package 'jsonwebtoken'` | CD runner never ran `npm install`; package shipped without `node_modules` | `npm ci --omit=dev` step before terraform packages it |
| frontend `npm ci` rejected | stale Create-React-App lockfile | `npm install` (lenient, like Vercel) |

**Three levels, each can pass while the next fails:** a green LOCAL test ≠ green CI
(clean env) ≠ healthy DEPLOY (the smoke test catches the last gap — e.g. it correctly
caught the broken chat Lambda by getting a crash-200 instead of the healthy 401).

---

## Smoke tests: assert the RIGHT signal, not just 200

The smoke test must encode what "healthy" actually means for each service:

- **Backend** has a public `/health` → assert **200**.
- **Chat** auth-gates every request (the handler verifies JWT before anything; there
  is no public health route) → an unauthenticated request returning **401** is the
  healthy signal ("alive + fail-closed auth works"). A **200** would be *wrong* — it
  meant the Lambda had crashed and returned its error body with a 200.

---

## Rollback = git-revert, not a button

Terraform is **declarative** — there's no instant "undo" (without Lambda
versioning). Rollback is:

```
git revert <bad-commit>   # a NEW forward commit that undoes the change (history kept)
→ merge → CD re-runs → terraform apply deploys the prior good code → smoke passes
```

Key points:
- Use `git revert`, **never** `git reset --hard` on protected `main` (rewrites
  history, can't push to a protected branch).
- Rollback reuses the **exact same proven pipeline** — no special emergency machinery.
- A deploy that fails **before** apply (OIDC, plan) or is caught by the **smoke
  test** never left prod broken → **fix-forward**, not rollback. Rollback is only for
  "apply succeeded but the app is broken live."
- **Branch deletion after merge is irrelevant.** `jland` deletes the branch, but the
  code is on `main` and state is in S3 — those are the source of truth. You recover
  from `main` (fix-forward or revert), never from the deleted branch.

---

## Smaller gotchas

- **Terraform downloads a ~648MB AWS provider** into `.terraform/` (it bundles ALL
  of AWS; you use a fraction). It MUST be gitignored — GitHub rejects files >100MB.
  Every new TF directory needs `.terraform/` ignored *before* the first commit after
  `terraform init`. (Bit us: a new `bootstrap/terraform/` lacked the per-dir
  `.gitignore` → the 648MB binary got committed → push rejected.)
- **`.terraform.lock.hcl` SHOULD be committed** (pins provider versions, like
  `package-lock.json`). Only the `.terraform/` *directory* is ignored.
- **Path filters scope which deploy fires.** `on.push.paths: [backend/**]` → a
  backend-only change triggers (and gates) only the backend deploy. You approve only
  what changed.
- **`AIzaSy…` is not automatically a secret.** Google has *server* keys (sensitive)
  and *browser/client* keys (public by design, referrer-restricted). A scraped
  third-party Google Picker key in a test fixture trips GitHub's scanner but is a
  false positive — pattern ≠ exposure.
- **zsh `local x` prints `x=value` when `x` already has a value.** Re-running
  `local names name val tfvar` *inside* a loop made iterations 2+ echo the previous
  iteration's secret values to the terminal. Fix: declare loop-locals once, at the
  top of the function. (Not xtrace — the tell was that single-stack ran clean while
  the 3-iteration `all` path leaked. Lesson: verify the diagnosis before building the
  fix; suspect the code you just changed.)
- **Node 20 deprecation warning** on action wrappers (checkout/setup-node/etc.) is
  harmless — GitHub auto-forces them to Node 24. It's about the action *wrappers'*
  runtime, NOT your Lambda's runtime. Bump to `@v5` actions later to silence it.

---

## Why it's structured this way

- **CI is secret-free** (throwaway runner Postgres at `localhost`, mocks elsewhere) →
  no prod credentials ever enter the test pipeline.
- **CD is the only thing that touches prod + uses secrets** → secrets live in GitHub
  Secrets (synced one-way by `jsyncsecrets` from the unified root `.env.local`), and
  every deploy is gated by a manual approval.
- **Frontend stays on Vercel** (its git integration auto-deploys + gives per-PR
  preview URLs — a real perk worth keeping). `jsyncsecrets` syncs the frontend's
  `REACT_APP_*` to Vercel too; CD does NOT redeploy the frontend (that would race
  Vercel's build).
