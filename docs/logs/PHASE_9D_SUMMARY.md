# Phase 9D: Continuous Deployment (Terraform via GitHub Actions)

**Status**: 📋 Planning
**Date**: June 25, 2026
**Goal**: Run **`terraform apply`** in a GitHub Actions workflow on merge to `main` — deploying the backend + chat stacks automatically, **gated** by a manual approval, with `TF_VAR_*` from GitHub Secrets and a **post-deploy smoke test + rollback**.

> The capstone of Phase 9. Builds on **9A** (deployment is now Terraform — `terraform apply`
> deploys infra *and* code), **9B** (the merge that triggers it), and **9C** (CI green gates the
> PR). This is the only sub-phase that touches **production** and uses **secrets**.

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
`/health` (+ representative endpoints); on failure the workflow **rolls back** (re-apply the
previous known-good package / Terraform state) so a bad deploy never stays live.

**Included in this phase**:
- `.github/workflows/deploy-backend.yml` + `deploy-chat.yml` — on merge to `main`:
  `terraform init` → `plan` → (gated approval) → `apply`
- **`TF_VAR_*` from GitHub Secrets** (`TF_VAR_database_url`, etc.) — the CD analogue of the local
  `tfvars.sh` (which reads `.env.local`); 9E centralizes the source
- **AWS creds** via GitHub Secrets (or OIDC) for Terraform + the S3 state backend
- **GitHub Environments** (`backend`, `chat`) with required-reviewer gates
- **Post-deploy smoke test + rollback** (deploy is self-verifying)
- `plan`-on-PR: post the Terraform plan as a PR comment for review (infra diff, like code)
- New ADR: **ADR-036** (Terraform CD: `apply` on merge, gated, smoke-test + rollback)

**Explicitly excluded**:
- Frontend deploy work — already CD via Vercel
- Fully-automatic (ungated) prod deploys — kept gated
- Re-implementing deploy logic — CD reuses the *same* `.tf` + module the local `jpushapi` uses

---

## Key Achievements (planned)

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
- After `apply`: assert `/health` (+ representative endpoints) return 200
- On failure: roll back (re-apply prior state / known-good package), exit non-zero

### 5. The full pipeline
```
jbranch → jsave → jpr → [CI 9C: tests + terraform plan on PR] → review → jland (merge)
                                                                    ├─ Vercel auto-deploys frontend
                                                                    ├─ deploy-backend.yml → (approve) → terraform apply → smoke → ✓/rollback
                                                                    └─ deploy-chat.yml    → (approve) → terraform apply → smoke → ✓/rollback
```

---

## Highlights

- **CD reuses 9A's Terraform unchanged** — the same `.tf` + lambda module the local `jpushapi`
  runs; CD just runs `terraform apply` in a runner with `TF_VAR_*` from Secrets. No new deploy code.
- **The local environment was the hard case** — Docker/ARM/`--platform` friction we fought in 9A
  is absent in CD (Linux runner). So the painful local migration *de-risks* CD.
- **`terraform apply` deploying every run is correct for CD** — each CD run is a merge (an
  intended change); we want the merged code deployed. (This is why 9A chose *not* to
  `ignore_source_code_hash`.)
- **State is shared via S3** — the runner reads the same `s3://jh-terraform-state-…` state the
  local deploys use, so CD and local stay consistent.

---

## Testing & Validation (planned)

**Manual**:
- [ ] PR shows `terraform plan` as a comment (infra diff reviewable)
- [ ] Merge a trivial backend change → `deploy-backend.yml` runs, waits at the approval gate
- [ ] Approve → `terraform apply` → backend Lambdas updated; smoke test `/health` 200
- [ ] Force a bad deploy → smoke fails → rollback → prod healthy, workflow exits non-zero
- [ ] Chat change → `deploy-chat.yml` gated → approve → chat updated → smoke ✓
- [ ] Frontend still auto-deploys via Vercel
- [ ] Confirm Terraform state in S3 stays consistent between CD and local runs

---

## Next Steps → Phase 9E

Secret re-architecture — replace the per-stack `.env.local` PROD_VALUE source (`tfvars.sh`) with
a **root `.env.local`** + a `jsyncsecrets` push to **GitHub Secrets**, so local and CD pull from
one consistent place. (9E is the original 9A scope, deferred behind the Terraform migration.)

---

## File Structure (planned)

```
jh/
├── .github/workflows/
│   ├── deploy-backend.yml   # merge → init → plan → (gated) apply → smoke/rollback
│   └── deploy-chat.yml
├── backend/terraform/       # the .tf CD runs (from 9A)
└── chat/terraform/
```

**Key files**:
- [backend/terraform/](../../backend/terraform/) — the Terraform CD applies (unchanged from 9A)
- [tfvars.sh](../../tfvars.sh) — local TF_VAR source; CD uses GitHub Secrets instead

---

## Key Learnings

- **Terraform makes CD trivial** — `plan` on PR + gated `apply` on merge is the standard IaC CD
  pattern, and 9A's migration set it up for free. The hard part was 9A (the migration), not 9D.
- **CD's Linux runner removes local packaging pain** — the cross-platform Lambda-build friction
  is a local-dev problem, not a CD one.
- **Secret injection lives in the deploy workflow, never in the PR flow** — `jpr`/`jland` (9B)
  touch no secrets; CD sets `TF_VAR_*` from GitHub Secrets at apply time.
- **A deploy isn't done until verified** — smoke-test + rollback turns `terraform apply` into a
  *safe* deploy (the pipeline catches a bad deploy, not a user hitting a 500).

---

## References

- Terraform in GitHub Actions: https://developer.hashicorp.com/terraform/tutorials/automation/github-actions
- GitHub Environments + required reviewers: https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment
- setup-terraform action: https://github.com/hashicorp/setup-terraform
