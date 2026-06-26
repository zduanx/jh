# Phase 9E: Continuous Deployment (Terraform via GitHub Actions)

**Status**: ✅ Completed
**Date**: June 26, 2026
**Goal**: Run **`terraform apply`** in a GitHub Actions workflow on merge to `main` — deploying the backend + chat stacks automatically, **gated** by a manual approval, authenticating to AWS via **OIDC (no stored keys)**, with `TF_VAR_*` from GitHub Secrets and a **post-deploy smoke test**.

> **Proven live:** both stacks deployed end-to-end via keyless gated CD — backend (OIDC →
> `terraform apply` → `/health` 200) and chat (OIDC → `npm ci` → apply → 401 healthy). OIDC role
> `jh-github-actions-cd` lives in its own **`bootstrap/terraform/`** state (`jpushbootstrap`); gates
> are GitHub Environments `production-backend`/`production-chat`. Deep-dive: [ci-cd.md](../learning/ci-cd.md).
>
> **3 real bugs the live deploy surfaced (all fixed):** (1) `environment:` changes the OIDC `sub`
> claim → trust policy had to accept `environment:production-*`, not `ref:refs/heads/main`; (2) chat
> Lambda shipped without `node_modules` (runner never ran `npm install`) → added `npm ci --omit=dev`;
> (3) chat smoke must expect **401** (auth-gated, no public health) not 200 — a 200 meant a crashed
> Lambda. The smoke test correctly caught the broken chat deploy. Rollback (git-revert) drill verified.

> The capstone of Phase 9. Builds on **9A** (deployment is now Terraform — `terraform apply`
> deploys infra *and* code), **9C** (the PR flow / the merge that triggers it), and **9D** (CI
> green gates the PR). This is the only sub-phase that touches **production** and uses **secrets**.

**The 9E work, in order:**
1. **OIDC auth** — AWS IAM OIDC provider + a role scoped to `repo:zduanx/jh:ref:refs/heads/main`
   (Terraform), so the runner assumes a role via a short-lived token — **no AWS keys stored in GitHub**
2. **CD workflows** — `deploy-backend.yml` + `deploy-chat.yml`: `init → plan → (gated apply)`
3. **Smoke test** — after apply, assert `/health` returns 200
4. **Rollback** — git-revert the bad commit → CD re-applies the previous good code (Terraform is
   declarative; "rollback" = apply the prior state, not an instant alias flip)
5. **`dev.sh` cleanup** — delete the dead SAM code (`jpushapi_sam`, `jpushchat_sam`,
   `generate_template.py`, `generate_samconfig.py`) left over from the pre-9A SAM deploy path

---

## Overview

Because 9A migrated deployment to **Terraform**, CD becomes simple and standard: on merge to
`main`, GitHub Actions runs **`terraform apply`** for each stack. This is the industry-standard
IaC CD pattern (`plan` on PR for review, `apply` on merge), and it's far cleaner than the old
SAM-generator pipeline would have been.

The friction we hit migrating locally (Docker for Lambda builds, ARM-vs-x86 wheels, the
`--platform` dance) **disappears in CD**: the GitHub runner is **Linux x86_64**, so the Lambda
module's `pip install` produces correct wheels natively, and Docker is pre-installed. So the
local environment was the *hard* case; CD is the easy one.

The frontend is **already CD** (Vercel auto-deploys on push). The new work is the backend + chat
Terraform apply workflows.

Deploys are **gated** (a GitHub Environment with a required reviewer) — on merge, the workflow
runs `terraform plan`, waits for approval, then `apply`. After apply, a **smoke test** hits
`/health`; on failure the workflow goes red. **Rollback is git-revert**: revert the bad commit on
`main` → CD re-applies the previous good code (declarative IaC has no instant undo without Lambda
versioning, which is deferred).

**Included in this phase**:
- **OIDC AWS auth** (Terraform): `aws_iam_openid_connect_provider` (trust GitHub's token issuer)
  + an `aws_iam_role` whose trust policy is scoped to `repo:zduanx/jh:ref:refs/heads/main` (only
  the repo's main branch — PRs and other repos can't assume it) + a permissions policy for the
  services Terraform touches (Lambda, S3, IAM, API Gateway, SQS, CloudWatch Logs, the state bucket).
  **No long-lived AWS keys in GitHub** — the runner gets ~1h temporary creds per run.
- `.github/workflows/deploy-backend.yml` + `deploy-chat.yml` — on merge to `main`:
  `terraform init` → `plan` → (gated approval) → `apply` → smoke test
- **`TF_VAR_*` from GitHub Secrets** (`TF_VAR_database_url`, etc.) — already synced by `jsyncsecrets`
  (9B). Same vars the local `tfvars.sh` exports from `.env.local`; Terraform reads `var.*` identically.
- **GitHub Environments** (`backend`, `chat`) with required-reviewer gates (the manual approval)
- **Post-deploy smoke test** — assert `/health` returns 200 after apply
- **Rollback = git-revert** — if a deploy goes bad, revert the commit → CD re-applies the prior good
  code (Terraform is declarative; rollback is "apply the previous state", not an alias flip)
- `plan`-on-PR: post the Terraform plan as a PR comment for review (infra diff, like code)
- **`dev.sh` SAM cleanup** — remove dead `jpushapi_sam` / `jpushchat_sam` / `generate_*.py`
- New ADR: **ADR-036** (Terraform CD: OIDC auth, `apply` on merge, gated, smoke-test, git-revert rollback)

**Explicitly excluded**:
- **Frontend deploy** — Vercel keeps auto-deploying on git push (we keep its per-PR preview deploys,
  a real perk). `jsyncsecrets` already syncs the frontend's `REACT_APP_*` to Vercel (9B); CD does
  not redeploy the frontend (that would race Vercel's build).
- Fully-automatic (ungated) prod deploys — kept gated (manual approval)
- Lambda alias/versioning for instant rollback — deferred (git-revert is enough at solo scale)
- Re-implementing deploy logic — CD reuses the *same* `.tf` + module the local `jpushapi` uses

---

## Key Achievements

### 1. Terraform apply workflows (per stack)
- Trigger: `push` to `main` (on merge), targeting the stack's Environment (gated)
- Steps: `terraform init` (S3 backend) → `plan` → approval → `apply` → smoke test
- The Lambda module builds in the runner (Linux → no Docker/arch friction)
- Reference: **ADR-036**

### 2. Secrets via GitHub Secrets → TF_VAR_*
- `TF_VAR_database_url`, `TF_VAR_secret_key`, … set from GitHub Secrets in the workflow `env`
- Same variables the local `tfvars.sh` exports from `.env.local` — Terraform reads `var.*`
  identically whether the value came from local env or GitHub Secrets
- AWS creds (for apply + S3 state) also from Secrets / OIDC

### 3. plan-on-PR + gated apply
- On the PR: `terraform plan` posted as a comment (the infra diff, reviewable like code)
- On merge: gated `apply` (required reviewer on the Environment) — preserves human control

### 4. Deploy → smoke-test → rollback
- After `apply`: assert `/health` returns 200 (the endpoint exists in `backend/main.py`)
- On failure: the workflow exits non-zero (red). **Rollback is git-revert**: revert the bad
  commit on `main` → CD re-applies the previous good code. (Honest about Terraform: there's no
  instant "undo" without Lambda versioning; declarative rollback = apply the prior state.)

### 5. The full pipeline
```
jbranch → jsave → jpr → [CI 9D: tests + terraform plan on PR] → review → jland (merge)
                                                                    ├─ Vercel auto-deploys frontend
                                                                    ├─ deploy-backend.yml → (approve) → terraform apply → smoke → ✓/rollback
                                                                    └─ deploy-chat.yml    → (approve) → terraform apply → smoke → ✓/rollback
```

---

## Highlights

- **CD reuses 9A's Terraform unchanged** — the same `.tf` + lambda module the local `jpushapi`
  runs; CD just runs `terraform apply` in a runner with `TF_VAR_*` from Secrets. No new deploy code.
- **Secrets reach Terraform as env vars, not generated files** — the runner names each secret into
  the job env (`TF_VAR_database_url: ${{ secrets.TF_VAR_DATABASE_URL }}`), and `terraform apply`
  auto-reads any `TF_VAR_*` from the environment. Unlike SAM (which needed `generate_*.py` to write
  `template.yaml`/`samconfig.toml`), Terraform consumes env + `.tf` natively — **no generate step**.
  The explicit `${{ secrets.X }}` lines are the required handoff from GitHub's vault into the VM
  (a script can't enumerate secrets by name) and double as **per-job least-privilege** (the backend
  job only sees backend's secrets, never chat's).
- **The local environment was the hard case** — Docker/ARM/`--platform` friction we fought in 9A
  is absent in CD (Linux runner). So the painful local migration *de-risks* CD.
- **`terraform apply` deploying every run is correct for CD** — each CD run is a merge (an
  intended change); we want the merged code deployed. (This is why 9A chose *not* to
  `ignore_source_code_hash`.)
- **State is shared via S3** — the runner reads the same `s3://jh-terraform-state-…` state the
  local deploys use, so CD and local stay consistent.

---

## Testing & Validation

**Manual**:
- [ ] PR shows `terraform plan` as a comment (infra diff reviewable)
- [x] Merge a backend change → `deploy-backend.yml` runs, waits at the approval gate
- [x] Approve → `terraform apply` → backend Lambdas updated; smoke test `/health` 200
- [x] Rollback drill: deployed a marker, git-reverted it → CD re-applied → marker gone
- [x] Chat change → `deploy-chat.yml` gated → approve → chat updated → smoke 401 ✓
- [x] Frontend still auto-deploys via Vercel (per-PR previews preserved)
- [x] **OIDC works keyless** — CD assumes the role, applies, with NO AWS keys in GitHub Secrets
- [x] Terraform state in S3 stays consistent between CD and local runs
- [x] Dead SAM code removed from `dev.sh`; `jpushapi`/`jpushchat` (Terraform) still work

---

## Next Steps → Phase 10

9E is the **capstone of Phase 9** (CI/CD). With it, the full SDLC loop is closed:
`jbranch → jsave → jpr → CI (9D) → review → jland → CD (9E) → prod`. Possible Phase 10
directions: observability (structured logs/metrics/alarms), the autonomous coding-agent work,
or hardening (least-privilege IAM, Lambda versioning for instant rollback).

---

## File Structure

```
jh/
├── .github/workflows/
│   ├── deploy-backend.yml   # merge → init → plan → (gated) apply → smoke test
│   └── deploy-chat.yml
├── backend/terraform/
│   └── *.tf                 # the infra/lambda .tf CD applies (from 9A)
├── bootstrap/terraform/
│   ├── oidc.tf              # GitHub OIDC provider + CD role (repo-level; jpushbootstrap)
│   └── main.tf              # own S3 state (key=bootstrap/), separate from the app stacks
└── chat/terraform/
```

**Key files**:
- `bootstrap/terraform/oidc.tf` — repo-level OIDC provider + CD role (separate state; `jpushbootstrap`)
- [backend/terraform/](../../backend/terraform/) — the Terraform CD applies (unchanged from 9A)
- [tfvars.sh](../../tfvars.sh) — local TF_VAR source; CD reads the same vars from GitHub Secrets
  (`jsyncsecrets` keeps both in sync from the unified root `.env.local`)

---

## Key Learnings

- **Terraform makes CD trivial** — `plan` on PR + gated `apply` on merge is the standard IaC CD
  pattern, and 9A's migration set it up for free. The hard part was 9A (the migration), not 9E.
- **CD's Linux runner removes local packaging pain** — the cross-platform Lambda-build friction
  is a local-dev problem, not a CD one.
- **Secret injection lives in the deploy workflow, never in the PR flow** — `jpr`/`jland` (9B)
  touch no secrets; CD sets `TF_VAR_*` from GitHub Secrets at apply time.
- **A deploy isn't done until verified** — smoke-test turns `terraform apply` into a *safe* deploy
  (the pipeline catches a bad deploy, not a user hitting a 500).
- **OIDC beats stored keys** — federated auth (GitHub proves its identity with a short-lived signed
  token; AWS trusts it via a repo+branch-scoped role) means **no long-lived AWS credentials in
  GitHub** to leak. The trust is scoped to `repo:zduanx/jh:ref:refs/heads/main`, so PRs and other
  repos can't assume the role. It's all IaC (`oidc.tf`) — the auth setup is itself version-controlled.
- **Terraform "rollback" is git-revert, not a button** — declarative IaC has no instant undo without
  Lambda versioning. Being honest about this (revert + re-apply) beats pretending there's a rollback
  switch. Instant rollback (alias flip) is a deliberate future add, not assumed.

---

## References

- Terraform in GitHub Actions: https://developer.hashicorp.com/terraform/tutorials/automation/github-actions
- GitHub Environments + required reviewers: https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment
- setup-terraform action: https://github.com/hashicorp/setup-terraform
