# Phase 9B: Secret Re-Architecture (unified root `.env.local` + manifest-driven config)

**Status**: ✅ Completed
**Date**: June 25, 2026
**Goal**: Collapse the three per-stack `.env.local` files into a **single unified root `.env.local`** (one source for local dev + tests + Terraform deploys), with a per-stack **`deploy.config.json`** manifest that orchestrates *which* secrets and *which* deploy target each stack uses.

> The original 9A-scope secret work, now **9B** (the Terraform migration took 9A). Adapts to
> Terraform: one local secret source → `TF_VAR_*`, and a manifest that makes both `tfvars.sh`
> and (later) 9E's CD generic. Phase 9: 9A Terraform → **9B secrets** → 9C branch/PR → 9D CI → 9E CD.

---

## Overview

After 9A, secrets lived in **three per-stack `.env.local`** files (`backend/`, `chat/`,
`frontend/`), each the sole local copy, with shared vars (`SECRET_KEY`, `MCP_SERVICE_TOKEN`)
**duplicated** across stacks. 9B unifies them into **one root `.env.local`** and makes the
tooling read it through a per-stack **manifest** rather than hardcoded paths.

The manifest — `deploy.config.json` per stack — is the **orchestrator**: it declares the stack's
**`target`** (`terraform` vs `vercel`, so CD routes correctly) and its **`secrets[]`** (which
env-var names the stack needs). `tfvars.sh` reads the manifest to grep exactly those vars'
PROD_VALUEs from the root `.env.local` and export `TF_VAR_*` — so adding a var to a stack is a
manifest edit, not a shell change. The same manifest will drive 9E's CD (which GitHub Secrets to
inject, whether to run `terraform apply` or let Vercel handle it).

Crucially, **every live reader** was repointed to the root file: the app loaders (so local dev
uses it), the test conftest, and `tfvars.sh` (for deploy). Prod is unaffected — in Lambda no file
exists, so Pydantic/dotenv read the Terraform-set OS env vars (unchanged).

**Included in this phase**:
- **Unified root `.env.local`** — merged from the 3 per-stack files; shared vars deduped
  (line-based dedup; gitignored, never committed)
- Per-stack **`deploy.config.json`** — `{ target, secrets[] }` (or `build_vars[]` for frontend):
  the orchestrator manifest (deploy routing + which secrets the stack needs)
- **Generic `tfvars.sh`** — reads the manifest's `secrets[]`, greps from root `.env.local`,
  exports `TF_VAR_*` (root preferred; per-stack fallback for safety)
- **App loaders → root**: `backend/config/settings.py`, `chat/local.js`,
  `backend/db/__tests__/conftest.py` prefer the root `.env.local` (legacy per-stack fallback)
- **`jsyncsecrets`** — push the manifest's secrets (PROD_VALUEs from root) → GitHub Secrets as
  `TF_VAR_*` (one-way; for 9E's CD)
- Removed the per-stack `.env.local` files (backed up to gitignored `.env-backups-9b/`)
- New ADR: **ADR-035** (unified root secret source + per-stack deploy.config.json manifest)

**Explicitly excluded**:
- AWS Secrets Manager / `jpullsecrets` — deferred (the root file + `jsyncsecrets` is enough at
  solo scale); could be a future "central store, pull on demand" upgrade
- Deleting the dead SAM deploy path (`jpushapi_sam`, `generate_*.py`) — unused (Terraform
  replaced it), left in place to avoid risky edits to the 2000-line `dev.sh`

---

## Key Achievements

### 1. Unified root `.env.local` (one source)
- Merged the 3 per-stack files; `SECRET_KEY` + `MCP_SERVICE_TOKEN` (identical across stacks) appear
  **once**. The root file feeds local dev, tests, and deploys.
- Reference: **ADR-035**

### 2. deploy.config.json — the orchestrator manifest
- `backend` / `chat`: `{ target: "terraform", secrets: [VAR names...] }`
- `frontend`: `{ target: "vercel", build_vars: [REACT_APP_*...] }`
- Single source of truth for **which stack deploys where** + **which secrets it needs** — used by
  `tfvars.sh` now and 9E's CD later (routing + secret injection)

### 3. Generic, manifest-driven `tfvars.sh`
- Reads `deploy.config.json secrets[]` → greps each `# NAME_PROD_VALUE=` from root `.env.local` →
  exports `TF_VAR_<lowercase>`. Adding a var = a manifest edit, no shell change.
- Root preferred; per-stack fallback (so it worked before and after the merge)

### 4. App loaders read the root file
- `settings.py` / `local.js` / `conftest.py` prefer root `.env.local` → local dev + tests use the
  unified source too (not just deploy). Prod unchanged (reads Lambda env vars).

### 5. jsyncsecrets (root → GitHub Secrets)
- Manifest-driven push of PROD_VALUEs → GitHub Secrets as `TF_VAR_*` (one-way; gh-auth-gated)

---

## Highlights

- **The manifest decouples "what each stack needs" from the tooling** — `tfvars.sh` and CD are
  generic; per-stack specifics live in `deploy.config.json`. `target` lets CD route
  `terraform apply` vs Vercel without special-casing.
- **One value, three homes** — local (root `.env.local`), CI/CD (GitHub Secrets via `jsyncsecrets`),
  prod runtime (Lambda env vars set by Terraform). 9B makes the local one a single file.
- **A secret file's path is a local-only concern** — moving to root is invisible to deploy (prod
  reads OS env vars), which is why repointing the loaders was safe.
- **Blast radius was bigger than "3 files"** — the full sweep touched app loaders, the test
  conftest, and `tfvars.sh`; the dead SAM path still references the removed files but is unused.

---

## Testing & Validation

**Manual** (verified):
- ✅ `tfvars.sh backend` / `chat` load `TF_VAR_*` from root `.env.local` (8 / 6 vars)
- ✅ Root-loaded values match the per-stack originals (no merge corruption)
- ✅ Backend boots reading root (`DATABASE_URL`/`SECRET_KEY`/`VOYAGE_API_KEY` loaded)
- ✅ Chat resolves root `.env.local`; conftest reads `TEST_DATABASE_URL` from root
- ✅ `jpushchat` deploys via root (`loaded 6 TF_VAR from jh/.env.local`), chat healthy
- ✅ Per-stack files removed; backend still boots (root only)
- ✅ `jsyncsecrets` loads + stops cleanly when `gh` not authed

---

## File Structure

```
jh/
├── .env.local                   # ROOT: unified secret source (gitignored)
├── tfvars.sh                    # manifest-driven: deploy.config.json → root .env.local → TF_VAR_*
├── dev_terraform.sh             # + jsyncsecrets (root → GitHub Secrets)
├── backend/deploy.config.json   # { target: terraform, secrets: [...] }
├── chat/deploy.config.json      # { target: terraform, secrets: [...] }
├── frontend/deploy.config.json  # { target: vercel, build_vars: [...] }
├── backend/config/settings.py   # reads root .env.local
├── chat/local.js                # reads root .env.local
└── backend/db/__tests__/conftest.py  # reads root .env.local
```

**Key files**:
- [tfvars.sh](../../tfvars.sh) · [backend/deploy.config.json](../../backend/deploy.config.json)
- [backend/config/settings.py](../../backend/config/settings.py) · [chat/local.js](../../chat/local.js)

---

## Next Steps → Phase 9C

Branch/PR `dev.sh` commands (`jbranch`/`jsave`/`jpr`/`jland`) — the workflow layer that 9D's CI
gates and 9E's CD deploys from. (GitHub setup: `gh auth login` for the PR commands; branch
protection on `main` for the CI gate.)

---

## Key Learnings

- **A manifest makes the tooling generic** — `deploy.config.json` (`target` + `secrets`) lets one
  `tfvars.sh` (and one CD workflow) serve all stacks; per-stack knowledge lives in data, not code.
- **Unify the consumer, then unify the source** — since Terraform reads `TF_VAR_*` regardless of
  origin, collapsing to one root `.env.local` + one manifest format was low-risk.
- **Fix every reader before deleting the source** — app loaders, tests, and deploy all had to point
  at root before removing the per-stack files (else local dev breaks).

---

## References

- Terraform `TF_VAR_` env vars: https://developer.hashicorp.com/terraform/language/values/variables#environment-variables
- GitHub encrypted secrets: https://docs.github.com/actions/security-guides/encrypted-secrets
- `gh secret set`: https://cli.github.com/manual/gh_secret_set
