# Phase 9A: Migrate Deployment to Terraform (IaC)

**Status**: ✅ Completed (functional) — code-deploy + commands verified in prod
**Date**: June 25, 2026
**Goal**: Replace the hand-rolled SAM deploy pipeline (`generate_template.py` → `sam build`/`sam deploy`) with **Terraform** as the Infrastructure-as-Code tool — adopting the existing live AWS resources in-place (no recreation), so `jpushapi`/`jpushchat` deploy via `terraform apply`.

> **Renumbered:** the original 9A (root `.env.local` secret re-arch) moved to **9E**.
> Phase 9 is now: **9A** Terraform migration → **9B** branch/PR commands → **9C** CI →
> **9D** CD (Terraform `apply` on merge) → **9E** secret re-arch (root file + GitHub Secrets).

---

## Overview

The backend (FastAPI + workers + MCP server) and chat (Node) stacks were deployed via
**SAM**: a custom `generate_template.py`/`generate_samconfig.py` pipeline produced
`template.yaml`/`samconfig.toml`, and `sam build`/`sam deploy` shipped them. 9A migrates
both stacks to **Terraform** — the industry-standard IaC tool — so deployment is declarative
`.tf`, state-tracked, and CI-friendly (setting up the easy `terraform apply` for 9D's CD).

The migration is **in-place adoption**, not recreation. The live resources (deployed by SAM)
were **imported** into Terraform state so Terraform manages the *existing* Lambdas/queues/
buckets without destroying anything. This was the delicate part: SAM's `AWS::Serverless::*`
macros expand to ~28 real resources (Lambdas + auto-generated IAM roles, event-source
mappings, permissions, log groups), every one of which had to import cleanly (`plan` showing
0 destroy / 0 replace) before any apply.

Lambda **code packaging** is handled by the **`terraform-aws-modules/lambda/aws` module**
(idiomatic Terraform — not a hand-rolled `archive_file`). The module does what `sam build`
did: reads `requirements.txt`, pip-installs the deps **in Docker** (correct Linux x86_64
wheels for compiled libs like numpy/cryptography/psycopg2), packages, and deploys.

**Included in this phase**:
- **S3 remote state backend** (`jh-terraform-state-…`, versioned + encrypted + private) +
  native S3 locking (`use_lockfile`)
- **Backend stack** (`backend/terraform/`): 23 resources imported in-place; 5 Lambdas via the
  lambda module (shared `backend/` source, per-Lambda handler/env); IAM roles, 2 SQS queues +
  event-source mappings, API Gateway + stage, Lambda permissions, 2 S3 buckets, MCP Lambda URL
- **Chat stack** (`chat/terraform/`): 5 resources imported; Lambda + URL + permissions + role
- **Co-located** Terraform under each stack (`backend/terraform/`, `chat/terraform/`) — matches
  the per-stack deploy ownership; `tfvars.sh` at repo root loads `TF_VAR_*` from `.env.local`
- **`jpushapi`/`jpushchat` rewired** to `terraform apply` (old SAM versions kept as
  `jpushapi_sam`/`jpushchat_sam`); `jtfplan` previews; `jtfkill` cleans up orphaned builds
- New ADR: **ADR-035** (Terraform over SAM; in-place import; lambda module for packaging)

**Explicitly excluded**:
- Root `.env.local` / GitHub-Secrets secret model → **9E** (TF_VARs come from per-stack
  `.env.local` PROD_VALUEs via `tfvars.sh` for now — temporary)
- CD on merge (`terraform apply` in GitHub Actions) → **9D**
- Removing the old SAM files (`generate_*.py`, `.sam-config`, `template.yaml`) — kept for now
  as reference / the `jpushapi_sam` fallback

---

## Key Achievements

### 1. In-place import migration (0 destroy, 0 replace)
- Backend: 23 live resources, Chat: 5 — all adopted into Terraform state via `import` blocks +
  `terraform plan -generate-config-out`, then cleaned (secrets → variables, code → module)
- Verified `plan` showed **0 to destroy / 0 to replace** before every apply; SQS event mappings
  (the risky job-trigger resources) preserved intact
- Reference: **ADR-035**

### 2. Lambda packaging via the community module (replaces `sam build`)
- `terraform-aws-modules/lambda/aws` builds in Docker: `pip_requirements` installs deps,
  `docker_additional_options=["--platform","linux/amd64"]` forces x86_64 wheels
- `store_on_s3=true` uploads the 78 MB package via S3 (>50 MB can't upload directly → 413)
- `create_role=false` + `lambda_role` reuse the imported IAM roles;
  `use_existing_cloudwatch_log_group=true` adopts the existing log groups

### 3. S3 remote state + co-located stacks
- State in `s3://jh-terraform-state-…/{backend,chat}/terraform.tfstate` (encrypted, versioned)
- Terraform co-located under each stack (`backend/terraform/`, `chat/terraform/`)

### 4. Deploy commands rewired to Terraform
- `jpushapi` → `terraform apply` (backend), `jpushchat` → chat; `jtfplan <stack>` previews
- `tfvars.sh` exports `TF_VAR_*` from `.env.local` PROD_VALUEs; `jtfkill` + traps tear down
  orphaned `package.py` Docker builds on Ctrl-C / kill (no runaway-CPU leftovers)

---

## Highlights

- **SAM was already using S3 for deploys** (its auto-managed `aws-sam-cli-…` bucket) — the
  >50 MB package always staged through S3. Terraform makes that explicit (`store_on_s3`); it's
  the same mechanism, not extra work.
- **Two size limits, both passed**: 78 MB *zipped* (>50 MB → S3 upload) and **233 MiB
  *unzipped*** (<250 MiB runtime limit — fits, with ~17 MiB headroom).
- **Redeploy-every-apply is intentional**: the Docker build isn't byte-reproducible, so each
  apply re-pushes the package. We accept this rather than `ignore_source_code_hash` because in
  **CD (9D)** every apply runs on a merge — we *want* the merged code deployed, and ignoring the
  hash would risk CD skipping real changes.
- **The hand-roll ethos (ADR-029) is scoped to the AI layer, not infra** — using the standard
  Terraform module here is correct, not a violation; CI/CD/IaC is where industry tools belong.

---

## Testing & Validation

**Manual** (verified in prod):
- ✅ Backend: all 5 Lambdas built by the module + deployed; API `/health` → 200, MCP → 401 (up)
- ✅ Chat: imported + endpoint up (401)
- ✅ SQS event-source mappings intact (CrawlerWorker/ExtractorWorker enabled)
- ✅ `jpushapi` (the rewired command) deploys end-to-end; prod stays healthy
- ✅ `terraform plan` after deploy: only the build-hash drift (no real config/infra change)
- ✅ Incident handled: a mid-migration broken deploy was restored via direct S3 deploy of the
  known-good package; prod recovered, then the fixed config (pip_requirements + store_on_s3)
  deployed cleanly

---

## Metrics

| Item | Value |
|------|-------|
| Resources migrated | 28 (backend 23 + chat 5) |
| Destroyed / replaced during migration | **0 / 0** |
| Lambda package size | 78 MB zipped / 233 MiB unzipped |
| Terraform version | 1.15.7 |
| Lambda module | terraform-aws-modules/lambda/aws ~> 7.0 |

---

## Next Steps → Phase 9B

Branch/PR `dev.sh` commands (`jbranch`/`jsave`/`jpr`/`jland`) — the workflow layer that 9C's CI
gates and 9D's CD deploys from. With deployment now on Terraform, 9D's CD becomes a clean
`terraform apply` in GitHub Actions (the runner is Linux — the Docker-build/arch friction we hit
locally disappears there).

---

## File Structure

```
jh/
├── tfvars.sh                    # load TF_VAR_* from <stack>/.env.local PROD_VALUEs
├── dev_terraform.sh             # jpushapi/jpushchat/jtfplan/jtfkill (Terraform deploy)
├── backend/terraform/
│   ├── main.tf                  # provider + S3 backend
│   ├── lambdas.tf               # 5 Lambdas via the lambda module
│   ├── infra.tf                 # IAM, SQS, S3, API Gateway, permissions, mappings
│   ├── locals.tf, variables.tf  # shared env + secret variables (from TF_VAR_*)
│   └── .terraform.lock.hcl      # provider lock (committed)
└── chat/terraform/
    ├── main.tf, chat.tf, variables.tf
    └── .terraform.lock.hcl
```

**Key files**:
- [backend/terraform/lambdas.tf](../../backend/terraform/lambdas.tf) — the 5 Lambdas via the module
- [backend/terraform/infra.tf](../../backend/terraform/infra.tf) — supporting AWS resources
- [tfvars.sh](../../tfvars.sh) · [dev_terraform.sh](../../dev_terraform.sh) — deploy commands

---

## Key Learnings

- **`terraform import` adopts existing infra; Terraform compares `.tf` vs STATE (not live AWS)** —
  so live SAM resources had to be imported into state first, or Terraform would try to *recreate*
  them. The "migration" is the import, not the `.tf` writing.
- **Cross-platform Lambda packaging needs Linux** — on an ARM Mac, deps must build as Linux
  x86_64 wheels (Docker, or `--platform`), or they crash on Lambda. SAM/the module both use
  Docker for this; in CI the Linux runner makes it free.
- **Use the standard module, don't hand-roll** — early attempts to hand-roll `pip install` +
  `archive_file` hit size/platform/dedup issues the `terraform-aws-lambda` module already solves.
- **Lambda has two size limits** (50 MB upload → S3; 250 MiB unzipped runtime → fits or go
  container-image). Knowing which limit a number refers to avoids chasing the wrong fix.

---

## References

- terraform-aws-modules/lambda: https://github.com/terraform-aws-modules/terraform-aws-lambda
- Lambda quotas (50 MB / 250 MiB): https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html
- Terraform S3 backend: https://developer.hashicorp.com/terraform/language/settings/backends/s3
