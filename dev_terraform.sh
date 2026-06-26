#!/usr/bin/env bash
# Terraform-based deploy commands (Phase 9A). Sourced by dev.sh.
#
# 9A migrated both stacks from SAM to Terraform: infra + Lambda code are now managed
# by `terraform apply` (the module builds the package in Docker, uploads via S3, deploys).
# These replace the old SAM-based jpushapi/jpushchat. Secrets come from <stack>/.env.local
# PROD_VALUEs via tfvars.sh (temporary until 9E's root .env.local + GitHub Secrets).

# Repo root (this file is sourced from dev.sh which sets JH_ROOT; fall back if not).
_JH_TF_ROOT="${JH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)}"

# Kill any orphaned module build scripts (the module's package.py Docker-build helpers
# that can survive a killed/timed-out terraform run and peg the CPU). Safe to run anytime.
jtfkill() {
  local n
  n=$(pgrep -f "modules/.*/package.py" 2>/dev/null | wc -l | tr -d ' ')
  if [ "${n:-0}" -gt 0 ]; then
    pkill -9 -f "modules/.*/package.py" 2>/dev/null
    echo -e "${YELLOW:-}  cleaned up $n orphaned build process(es)${NC:-}"
  fi
  pkill -9 -f "terraform apply -auto-approve" 2>/dev/null
}

# Deploy a Terraform stack: load TF_VARs from its .env.local, then terraform apply.
# Runs terraform in its OWN process group and traps INT/TERM so Ctrl-C (or a kill)
# tears down the WHOLE build tree (terraform + the package.py Docker builds) — no orphans.
#   _jh_tf_deploy <stack>   (stack = backend | chat)
_jh_tf_deploy() {
  local stack="$1"
  local tfdir="$_JH_TF_ROOT/$stack/terraform"

  echo -e "${BLUE:-}=== Deploying $stack via Terraform ===${NC:-}"

  if [ ! -d "$tfdir" ]; then echo "✗ no $tfdir" >&2; return 1; fi

  # Docker is required (the module builds the Lambda package in a Linux container).
  if ! docker info >/dev/null 2>&1; then
    echo -e "${RED:-}✗ Docker is not running (needed to build the Lambda package).${NC:-}"
    echo "  Start Docker Desktop, then retry."
    return 1
  fi

  # Load TF_VAR_* for this stack from its .env.local PROD_VALUEs.
  source "$_JH_TF_ROOT/tfvars.sh" "$stack" || return 1

  # On Ctrl-C / TERM, clean up any orphaned build processes before exiting.
  trap 'jtfkill; trap - INT TERM; return 130' INT TERM

  ( cd "$tfdir" && terraform apply -auto-approve )
  local rc=$?

  trap - INT TERM
  jtfkill  # belt-and-suspenders: sweep any leftover builds after the run

  if [ $rc -eq 0 ]; then
    echo -e "${GREEN:-}✓ $stack deployed via Terraform${NC:-}"
  else
    echo -e "${RED:-}✗ terraform apply failed (rc=$rc)${NC:-}"
  fi
  return $rc
}

# jpushapi — deploy the backend stack (5 Lambdas + API/SQS/S3) via Terraform.
jpushapi() { _jh_tf_deploy backend; }

# jpushchat — deploy the chat stack via Terraform.
jpushchat() { _jh_tf_deploy chat; }

# jpushbootstrap — apply the repo-level bootstrap stack (GitHub OIDC provider + CD
# role). No Lambda, no secrets, so it skips the Docker/tfvars machinery — just a plain
# terraform apply. One-time / rarely-changing (the CD auth foundation for 9E).
jpushbootstrap() {
  local tfdir="$_JH_TF_ROOT/bootstrap/terraform"
  [ -d "$tfdir" ] || { echo -e "${RED:-}✗ no $tfdir${NC:-}"; return 1; }
  echo -e "${BLUE:-}=== Applying bootstrap (OIDC + CD role) via Terraform ===${NC:-}"
  ( cd "$tfdir" && terraform init -input=false >/dev/null && terraform apply -auto-approve )
  local rc=$?
  [ $rc -eq 0 ] && echo -e "${GREEN:-}✓ bootstrap applied${NC:-}" \
                || echo -e "${RED:-}✗ bootstrap apply failed (rc=$rc)${NC:-}"
  return $rc
}

# jtfplan — preview changes for a stack without applying (terraform plan).
# Also builds in Docker (to compute the code hash), so it traps + cleans up like deploy.
#   jtfplan backend | jtfplan chat
jtfplan() {
  local stack="${1:-backend}"
  source "$_JH_TF_ROOT/tfvars.sh" "$stack" || return 1
  trap 'jtfkill; trap - INT TERM; return 130' INT TERM
  ( cd "$_JH_TF_ROOT/$stack/terraform" && terraform plan )
  trap - INT TERM
  jtfkill
}

# jsyncsecrets — manual one-way push of each stack's vars from the unified root
# .env.local PROD_VALUEs to its deploy target (Phase 9B → 9E CD). Manifest-driven:
# each stack's deploy.config.json `target` decides WHERE the vars go —
#   target=terraform → GitHub Secrets as TF_VAR_<lowercase>   (CD `terraform apply` reads them)
#   target=vercel    → Vercel production env via `vercel env`  (Vercel still deploys; we only sync)
# Source is root .env.local; the destinations are write-only. Purely manual (never automatic).
#   jsyncsecrets [backend|chat|frontend|all]   (default: all stacks)
jsyncsecrets() {
  local which="${1:-all}"
  local root="$_JH_TF_ROOT"
  local envfile="$root/.env.local"

  if [ ! -f "$envfile" ]; then echo -e "${RED:-}✗ no root .env.local${NC:-}"; return 1; fi

  local stacks=()
  case "$which" in
    all) stacks=(backend chat frontend) ;;
    *)   stacks=("$which") ;;
  esac

  # Declare ALL loop-locals ONCE up front. (In zsh, re-running `local x` on a later
  # loop iteration — when x already holds a value — PRINTS `x=value` to stdout, which
  # would leak secret values. Declaring once avoids that re-declaration entirely.)
  local pushed=0 stack manifest target names name val tfvar bvars bv
  for stack in "${stacks[@]}"; do
    manifest="$root/$stack/deploy.config.json"
    [ -f "$manifest" ] || { echo "  ⚠ no $manifest, skip"; continue; }
    target="$(python3 -c "import json;print(json.load(open('$manifest')).get('target',''))" 2>/dev/null)"

    case "$target" in
      terraform)
        if ! command -v gh >/dev/null 2>&1; then echo "  ⚠ gh CLI missing — skip '$stack'"; continue; fi
        if ! gh auth status >/dev/null 2>&1; then echo "  ⚠ gh not authed (gh auth login) — skip '$stack'"; continue; fi
        echo -e "${BLUE:-}=== '$stack' (terraform) → GitHub Secrets ===${NC:-}"
        names="$(python3 -c "import json;print('\n'.join(json.load(open('$manifest')).get('secrets',[])))" 2>/dev/null)"
        while IFS= read -r name; do
          [ -z "$name" ] && continue
          val="$(grep "^# ${name}_PROD_VALUE=" "$envfile" | head -1 | cut -d= -f2-)"
          [ -z "$val" ] && { echo "  ⚠ no PROD_VALUE for $name"; continue; }
          tfvar="TF_VAR_$(echo "$name" | tr '[:upper:]' '[:lower:]')"
          printf '%s' "$val" | gh secret set "$tfvar" >/dev/null 2>&1 \
            && { echo "  ✓ $tfvar"; pushed=$((pushed+1)); } \
            || echo "  ✗ failed: $tfvar"
        done <<< "$names"
        ;;

      vercel)
        if ! command -v vercel >/dev/null 2>&1; then echo "  ⚠ vercel CLI missing — skip '$stack'"; continue; fi
        echo -e "${BLUE:-}=== '$stack' (vercel) → Vercel production env ===${NC:-}"
        echo "  (Vercel still deploys on git push; this only syncs its build-time vars.)"
        # frontend manifest uses build_vars[] (public REACT_APP_*), not secrets[]
        bvars="$(python3 -c "import json;print('\n'.join(json.load(open('$manifest')).get('build_vars',[])))" 2>/dev/null)"
        ( cd "$root/frontend" || exit 1
          while IFS= read -r bv; do
            [ -z "$bv" ] && continue
            val="$(grep "^# ${bv}_PROD_VALUE=" "$envfile" | head -1 | cut -d= -f2- | tr -d '\r')"
            [ -z "$val" ] && { echo "  ⚠ no PROD_VALUE for $bv"; continue; }
            # replace: remove the existing prod var (ignore if absent), then add fresh
            echo "y" | vercel env rm "$bv" production >/dev/null 2>&1
            printf '%s' "$val" | vercel env add "$bv" production >/dev/null 2>&1 \
              && echo "  ✓ $bv" || echo "  ✗ failed: $bv"
          done <<< "$bvars"
        ) && pushed=$((pushed+1))
        ;;

      *)
        echo "  ⚠ '$stack' has unknown target '$target' — skip"
        ;;
    esac
  done
  echo -e "${GREEN:-}✓ jsyncsecrets done${NC:-}"
}
