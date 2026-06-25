#!/usr/bin/env bash
# Load TF_VAR_* for a Terraform stack from that stack's .env.local PROD_VALUEs.
# Phase 9A/9E: the `var.x` declared in variables.tf reads from TF_VAR_x, which we
# export here from the matching `# X_PROD_VALUE=` comment in .env.local.
#
# Usage:  source tfvars.sh <stack>     (stack = backend | chat)
# Then `terraform apply` (or jpushapi/jpushchat) picks up the exported TF_VAR_*.
#
# Maps TF_VAR_database_url  ->  # DATABASE_URL_PROD_VALUE=...  in <stack>/.env.local.

_jh_load_tfvars() {
  local stack="$1"
  # This file lives at the repo root. Each stack co-locates its Terraform under
  # <stack>/terraform/ and its secrets under <stack>/.env.local.
  local self="${BASH_SOURCE[0]:-${(%):-%x}}"
  local root; root="$(cd "$(dirname "$self")" && pwd)"
  local envfile="$root/$stack/.env.local"
  local varsfile="$root/$stack/terraform/variables.tf"

  if [ ! -f "$envfile" ]; then echo "✗ no $envfile" >&2; return 1; fi
  if [ ! -f "$varsfile" ]; then echo "✗ no $varsfile" >&2; return 1; fi

  local count=0 missing="" upper val
  # for each `variable "x" {` in variables.tf, export TF_VAR_x from X_PROD_VALUE
  while IFS= read -r tfvar; do
    upper="$(echo "$tfvar" | tr '[:lower:]' '[:upper:]')"
    val="$(grep "^# ${upper}_PROD_VALUE=" "$envfile" | head -1 | cut -d= -f2-)"
    if [ -n "$val" ]; then
      export "TF_VAR_${tfvar}=${val}"
      count=$((count + 1))
    else
      missing="$missing $tfvar"
    fi
  done < <(grep -E '^variable ' "$varsfile" | grep -oE '"[a-z_]+"' | tr -d '"')

  echo "✓ loaded $count TF_VAR_* for '$stack'${missing:+ (no PROD_VALUE for:$missing — using defaults)}"
}

# allow `source tfvars.sh <stack>` to load immediately
if [ -n "${1:-}" ]; then _jh_load_tfvars "$1"; fi
