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
