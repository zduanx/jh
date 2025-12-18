# Phase 2C: Development Automation (dev.sh)

**Status**: ✅ Completed
**Date**: December 18, 2025
**Goal**: Comprehensive development shortcuts and deployment automation via dev.sh

---

## Overview

Phase 2C established the complete development automation infrastructure through `dev.sh`, providing one-command shortcuts for local development, deployment to AWS Lambda and Vercel, and environment verification.

**Included in this phase**:
- Local development shortcuts (start/stop/status)
- Background process management with log files
- Readiness checks with auto-fix capabilities
- AWS Lambda deployment automation (`jpushapi`)
- Vercel frontend deployment automation (`jpushvercel`)
- Environment variable sync verification (`jenvcheck`)
- Config generation scripts for SAM deployment
- Database migration automation (`jdbcreate`, `jdbpush`, `jdbstatus`)
- Helper utilities for DB URL extraction

**Explicitly excluded** (deferred to Phase 2D):
- 5-stage horizontal stepper UI
- User company settings table and CRUD endpoints

---

## Key Achievements

### 1. Local Development Shortcuts
- **`jbe` / `jfe`**: Start backend/frontend in foreground
- **`jbe-bg` / `jfe-bg`**: Start in background with nohup, survives terminal close
- **`jkill-be` / `jkill-fe` / `jkillall`**: Port-based process termination
- **`jstatus`**: Check what's running on ports 8000/3000

### 2. Readiness Check (`jready`)
7-step verification with auto-fix:
1. Backend virtual environment exists
2. Backend dependencies installed (auto-installs if missing)
3. Backend `.env.local` with required variables
4. Frontend `node_modules` exists
5. Frontend `.env.local` with required variables
6. Database connectivity (both test and prod)
7. Port availability (8000, 3000)

### 3. AWS Lambda Deployment (`jpushapi`)
7-step deployment workflow:
1. Git status check (require clean state or commit)
2. Lambda env var comparison with `.env.local` PROD_VALUE
3. Generate `template.yaml` and `samconfig.toml` via Python scripts
4. Review changes and confirm
5. Auto-commit generated files
6. SAM build and deploy
7. Verify deployment and show API URL

### 4. Vercel Deployment (`jpushvercel`)
5-step deployment workflow:
1. Check Vercel project status
2. Compare env vars (pull from Vercel, compare to PROD_VALUE)
3. Auto-update differing variables
4. Git status and branch check
5. Git push for CI/CD trigger

### 5. Environment Verification (`jenvcheck`)
- Compare Lambda env vars vs `.env.local` PROD_VALUE
- Compare Vercel env vars vs `.env.local` PROD_VALUE
- Detect corruption (literal `\n` escape sequences)
- Show clear diff for mismatches

### 6. Config Generation Scripts
- **`generate_template.py`**: Creates CloudFormation `template.yaml` from `.sam-config` + `.env.local` metadata
- **`generate_samconfig.py`**: Creates SAM `samconfig.toml` from `.sam-config` + `.env.local` PROD_VALUE
- **Exit codes**: 0=no change, 1=modified, 2=new file (enables shell branching)

### 7. Database Migration Automation
- **`jdbcreate <name>`**: Generate new Alembic migration with autogenerate
- **`jdbpush`**: Apply migrations to both test and prod databases sequentially
- **`jdbstatus`**: Show current migration revision and list tables for both databases
- **Helper functions**: `_get_test_db_url()`, `_get_prod_db_url()`, `_mask_db_url()` for consistent URL handling

---

## Highlights

### Global Environment Variable Configuration
At script load time, parses PROD_VALUE comments from `.env.local` files into associative arrays (`BACKEND_CHECK`, `FRONTEND_CHECK`). This enables consistent comparison across all commands.

### Value Normalization
`_normalize_env_value()` strips literal escape sequences (`\n`, `\r`, `\t`) and quotes. Prevents false mismatches from corrupted values.

### Background Process Management
Uses `nohup` with output redirected to `server.log`. PIDs displayed for reference. Port-based killing via `lsof` ensures clean termination.

### Change Detection Without Git
Python scripts compare existing file content vs newly generated content. Returns exit codes for shell to branch on. Works for gitignored files like `samconfig.toml`.

---

## Testing & Validation

**Manual Testing**:
- ✅ `jready` detects missing venv, auto-installs dependencies
- ✅ `jbe-bg && jfe-bg` starts both services in background
- ✅ `jstatus` correctly shows running/not running
- ✅ `jkillall` terminates both processes
- ✅ `jpushapi` deploys to Lambda with env var sync
- ✅ `jpushvercel` deploys to Vercel with env var sync
- ✅ `jenvcheck` detects mismatches and corruption
- ✅ `jdbcreate` generates Alembic migration files
- ✅ `jdbpush` applies migrations to test + prod databases
- ✅ `jdbstatus` shows migration status with masked URLs and table lists

---

## Metrics

- **Shell Functions**: 18 (jbe, jfe, jbe-bg, jfe-bg, jkill-be, jkill-fe, jkillall, jstatus, jready, jpushapi, jpushvercel, jenvcheck, jdbcreate, jdbpush, jdbstatus, jhelp, + 5 helpers)
- **Python Scripts**: 2 (generate_template.py, generate_samconfig.py)
- **Lines of Code**: ~1180 (shell) + ~400 (Python)
- **Checks in jready**: 7 steps

---

## Next Steps → Phase 2D

Phase 2D will implement **Ingestion Stage 1 (Configure)**:
- 5-stage horizontal stepper UI (skeleton)
- User company settings table and CRUD endpoints
- Stage 1 company configuration UI

**Target**: Complete Stage 1 company configuration workflow

---

## File Structure

```
Root/
├── dev.sh                           # All development shortcuts
└── DEV_SHORTCUTS.md                 # Documentation

backend/
├── scripts/
│   ├── generate_template.py         # CloudFormation template generator
│   └── generate_samconfig.py        # SAM config generator
├── .sam-config                      # Deployment metadata (committed)
├── .env.local                       # Env vars with PROD_VALUE (gitignored)
├── template.yaml                    # Generated CloudFormation (committed)
└── samconfig.toml                   # Generated SAM config (gitignored)
```

**Key Files**:
- [dev.sh](../../dev.sh) - All development shortcuts
- [generate_template.py](../../backend/scripts/generate_template.py) - Template generator
- [generate_samconfig.py](../../backend/scripts/generate_samconfig.py) - SAM config generator

---

## Key Learnings

### Associative Arrays for Config
zsh `typeset -A` creates key-value maps parsed once at load time. All commands share the same source of truth.

### Exit Codes for Script Communication
Python scripts return 0/1/2 to indicate no-change/modified/new. Shell branches without parsing stdout.

### Background Processes
`nohup` + output redirection + `&` enables true background processes. PID tracking for later termination.

---

## References

**External Documentation**:
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli.html)
- [Vercel CLI](https://vercel.com/docs/cli)
- [zsh Associative Arrays](https://zsh.sourceforge.io/Doc/Release/Parameters.html)
