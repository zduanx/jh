#!/usr/bin/env bash
# Load TF_VAR_* for a stack from the unified root .env.local PROD_VALUEs (Phase 9B).
#
# Generic, manifest-driven: the stack's deploy.config.json `secrets[]` lists which
# env-var names it needs; we grep each one's `# NAME_PROD_VALUE=` from the unified
# root .env.local and export it as TF_VAR_<lowercase>. So adding a var to a stack is
# a deploy.config.json edit — no change here.
#
# Secrets source precedence:
#   1. root .env.local        (Phase 9B unified source — preferred)
#   2. <stack>/.env.local     (fallback, pre-9B per-stack files)
#
# Usage:  source tfvars.sh <stack>     (stack = backend | chat)
# Then `terraform apply` (jpushapi/jpushchat) picks up the exported TF_VAR_*.

_jh_load_tfvars() {
  local stack="$1"
  local self="${BASH_SOURCE[0]:-${(%):-%x}}"
  local root; root="$(cd "$(dirname "$self")" && pwd)"
  local manifest="$root/$stack/deploy.config.json"

  if [ ! -f "$manifest" ]; then echo "✗ no $manifest" >&2; return 1; fi

  # Secrets file: prefer the unified root .env.local; fall back to the per-stack one.
  local envfile
  if [ -f "$root/.env.local" ]; then
    envfile="$root/.env.local"
  elif [ -f "$root/$stack/.env.local" ]; then
    envfile="$root/$stack/.env.local"
  else
    echo "✗ no root .env.local or $stack/.env.local" >&2; return 1
  fi

  # The var names this stack needs come from deploy.config.json `secrets[]`.
  # Parse with python if available (robust), else a grep fallback.
  local names
  if command -v python3 >/dev/null 2>&1; then
    names="$(python3 -c "import json,sys; print('\n'.join(json.load(open('$manifest')).get('secrets',[])))" 2>/dev/null)"
  else
    names="$(grep -oE '"[A-Z_]+"' "$manifest" | tr -d '"')"
  fi

  local count=0 missing="" name val tfvar
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    val="$(grep "^# ${name}_PROD_VALUE=" "$envfile" | head -1 | cut -d= -f2-)"
    tfvar="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
    if [ -n "$val" ]; then
      export "TF_VAR_${tfvar}=${val}"
      count=$((count + 1))
    else
      missing="$missing $tfvar"
    fi
  done <<< "$names"

  echo "✓ loaded $count TF_VAR_* for '$stack' from $(basename "$(dirname "$envfile")")/.env.local${missing:+ (no PROD_VALUE for:$missing — using defaults)}"
}

# allow `source tfvars.sh <stack>` to load immediately
if [ -n "${1:-}" ]; then _jh_load_tfvars "$1"; fi
