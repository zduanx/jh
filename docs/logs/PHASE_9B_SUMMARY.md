# Phase 9B: Secret Re-Architecture (root `.env.local` + GitHub Secrets → TF_VAR)

**Status**: 📋 Planning
**Date**: June 25, 2026
**Goal**: Replace the per-stack `.env.local` PROD_VALUE source (read by `tfvars.sh` today) with a **single root `.env.local`** as the local source of truth and **GitHub Secrets** as the CI/CD source — both feeding Terraform's `TF_VAR_*` consistently.

> The original 9A-scope secret work, now 9B (after the Terraform migration took 9A). Adapts to
> Terraform: clean, consistent TF_VAR_* for local (tfvars.sh) and CD (GitHub Secrets).
> (the new 9A). It now adapts to Terraform: the target is clean, consistent `TF_VAR_*` for both
> local (`tfvars.sh`) and CD (9D's GitHub-Secrets workflow).

---

## Overview

Today (after 9A) secrets live in **per-stack `.env.local`** files, and `tfvars.sh` reads each
stack's PROD_VALUEs to export `TF_VAR_*` for local `terraform apply`. That works but has the same
fragility the original 9A flagged: each `.env.local` is the sole local copy, buried in the tree,
and split across stacks. And for **CD (9D)**, secrets must also exist in **GitHub Secrets**.

9E unifies the secret story around Terraform's `TF_VAR_*`:

- **Local**: a single **root `.env.local`** (the one local cache, branch-safe, copy-able) →
  `tfvars.sh` reads it → exports `TF_VAR_*` for local deploys
- **CI/CD (9D)**: **GitHub Secrets** → the workflow sets `TF_VAR_*` from them → `terraform apply`
- **Sync**: `jsyncsecrets` pushes the root file's values to GitHub Secrets (one-way; GitHub
  secrets are write-only)

So the same `TF_VAR_x` is satisfied from the root `.env.local` locally and from GitHub Secrets in
CD — Terraform's `var.x` doesn't care which; only the *source of the env var* differs per
environment.

**Included in this phase**:
- A single **root `.env.local`** (merge the per-stack files; shared vars — `SECRET_KEY`,
  `MCP_SERVICE_TOKEN` — dedupe to one definition)
- Update **`tfvars.sh`** to read the root file (it currently reads per-stack `<stack>/.env.local`)
- Update the **app loaders** that still read per-stack `.env.local` (backend `config/settings.py`,
  `chat/local.js`) to the root file — verified to fall back to Lambda env vars in prod (unchanged)
- **`jsyncsecrets`** — push the root file's PROD_VALUEs → GitHub Secrets (for 9D)
- (Optional) **AWS Secrets Manager** as a durable source of truth + `jpullsecrets` to regenerate
  the root cache — the "central store, pull on demand" model
- New ADR: **ADR-037** (single local secret source → TF_VAR_*; GitHub Secrets for CD)

**Explicitly excluded**:
- Anything Terraform-deploy-related (done in 9A)
- The CD workflow itself (9D) — 9E just makes the secret *source* consistent for it

---

## Key Achievements (planned)

### 1. Root `.env.local` (one local source)
- Merge `backend/`, `chat/`, `frontend/` `.env.local` into one root file (shared vars dedupe)
- Branch-safe (sits above per-stack code), copy-able, single place to edit
- Reference: **ADR-037**

### 2. tfvars.sh + app loaders read the root file
- `tfvars.sh`: `<stack>/.env.local` → root `.env.local` (one source for all stacks' TF_VARs)
- backend `config/settings.py` + `chat/local.js`: per-stack → root path (prod unaffected — both
  fall back to Lambda env vars when the file is absent)

### 3. GitHub Secrets sync for CD
- `jsyncsecrets` reads the root file's PROD_VALUEs → `gh secret set` (one-way push)
- 9D's workflow then sets `TF_VAR_*` from those secrets

### 4. (Optional) AWS Secrets Manager source of truth
- Store secrets in SM; `jpullsecrets` regenerates the root `.env.local` (disposable cache)
- The big-company "central store, pull on demand" model, right-sized

---

## Highlights

- **Terraform unifies the consumer**: both local and CD satisfy the same `TF_VAR_*`, so the only
  thing 9E changes is *where the env var's value comes from* (root file vs GitHub Secrets) — the
  `.tf` and `var.*` declarations are identical across environments.
- **Secrets in three homes, one value each** — local (root `.env.local`), CI/CD (GitHub Secrets),
  prod runtime (Lambda env vars, set by Terraform from `TF_VAR_*`). 9E makes the *local* one a
  single file and adds the *sync* to GitHub.
- **One-way sync only** — `.env.local` (or AWS SM) is the source; pushed to GitHub Secrets (which
  can't be read back). Never sync down.

---

## Testing & Validation (planned)

**Manual**:
- [ ] `tfvars.sh backend` loads `TF_VAR_*` from the **root** `.env.local`; `terraform plan` clean
- [ ] `tfvars.sh chat` likewise
- [ ] Backend + chat boot locally reading the root `.env.local`
- [ ] `jpushapi` / `jpushchat` deploy using the root-file TF_VARs
- [ ] `jsyncsecrets` → values present in GitHub Secrets (`gh secret list`)
- [ ] Delete root `.env.local` → (if SM) `jpullsecrets` regenerates it
- [ ] Switching git branches never disturbs the root `.env.local`

---

## File Structure (planned)

```
jh/
├── .env.local              # ROOT: single local secret source (gitignored, branch-safe)
├── tfvars.sh               # reads root .env.local → exports TF_VAR_*
├── dev_terraform.sh        # + jsyncsecrets (push to GitHub Secrets)
├── backend/config/settings.py   # reads ../.env.local
└── chat/local.js                # reads ../.env.local
```

**Key files**:
- [tfvars.sh](../../tfvars.sh) — repoint to root `.env.local`
- [backend/config/settings.py](../../backend/config/settings.py) · [chat/local.js](../../chat/local.js) — app loaders

---

## Key Learnings

- **Terraform's `TF_VAR_*` is the unifying interface** — once deploy is Terraform (9A), the secret
  question reduces to "how does each environment set `TF_VAR_*`": root file locally, GitHub Secrets
  in CD. Same variable, different source.
- **A secret file's location is a local-only concern** — prod reads Lambda env vars (set by
  Terraform), so moving the local file to root is invisible to deploy.
- **The big-company model, right-sized** — AWS Secrets Manager + `jpullsecrets` makes the local
  file a disposable cache, but for solo scale the root `.env.local` + `jsyncsecrets` is enough.

---

## References

- Terraform `TF_VAR_` env vars: https://developer.hashicorp.com/terraform/language/values/variables#environment-variables
- GitHub encrypted secrets: https://docs.github.com/actions/security-guides/encrypted-secrets
- `gh secret set`: https://cli.github.com/manual/gh_secret_set
