#!/usr/bin/env bash
# extractors_v2 CLI — local test verbs for the v2 framework.
# Named cli.sh (NOT dev.sh) to avoid confusion with the repo-root dev.sh.
#
# Usage:  ./cli.sh <verb> [args]
# Verbs (added incrementally across Phase 8):
#   edocker                  check / start the Docker daemon (e.g. after a reboot)
#   eclean [--image]         clean up Docker leftovers (containers, dangling images, cache)
#   elogo <company>          (8C) print the discovered LOGO_URL for a company
#   elist <company>          (8D) run _fetch_all_jobs → print the job list + count
#   ejd   <company> <url>    (8D) crawl a job page → LLM-parse → print the JD
#
# Run from backend/extractors_v2/ (or any cwd — paths resolve relative to this file).

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$(cd "$HERE/.." && pwd)"

verb="${1:-}"; shift || true

SANDBOX_IMAGE="jh-extractor-sandbox"

case "$verb" in
  edocker)
    # Check / start the Docker daemon (needed by the sandbox; may be down after a reboot).
    if docker info >/dev/null 2>&1; then
      echo "✓ Docker daemon is running"
    else
      echo "Docker daemon not running — launching Docker Desktop…"
      open -a Docker
      echo "  (takes ~30s; re-run 'edocker' to confirm, or: docker info)"
    fi
    ;;
  eclean)
    # Clean up Docker leftovers from sandbox runs.
    #   eclean         → stopped/lingering sandbox containers + dangling images + build cache
    #   eclean --image → ALSO remove the jh-extractor-sandbox image (next run rebuilds it)
    echo "Removing any lingering '$SANDBOX_IMAGE' containers…"
    docker ps -aq --filter "ancestor=$SANDBOX_IMAGE" | xargs -r docker rm -f 2>/dev/null || true
    echo "Pruning stopped containers + dangling images + build cache…"
    docker container prune -f >/dev/null 2>&1 || true
    docker image prune -f     >/dev/null 2>&1 || true
    docker builder prune -f   >/dev/null 2>&1 || true
    if [ "${1:-}" = "--image" ]; then
      echo "Removing the $SANDBOX_IMAGE image (next run rebuilds)…"
      docker rmi -f "$SANDBOX_IMAGE" >/dev/null 2>&1 || true
    fi
    echo "✓ cleanup done"
    docker system df 2>/dev/null | head -4
    ;;
  elogo)
    # Load the GENERATED extractor for a company via the registry, print its ICON_URL.
    # Proves the agent's output actually loads + works when used by the backend.
    company="${1:-}"
    if [ -z "$company" ]; then echo "Usage: elogo <company>"; exit 1; fi
    cd "$BACKEND"
    source venv/bin/activate 2>/dev/null || true
    python -c "
import sys
from extractors_v2.registry import get_extractor
try:
    cls = get_extractor('$company')
except ValueError as e:
    print('✗', e); sys.exit(1)
print(f'company : {cls.COMPANY_NAME}')
print(f'class   : {cls.__name__}')
print(f'icon_url: {cls.ICON_URL}')
"
    ;;
  elist)
    # Run the GENERATED extractor's _fetch_all_jobs → print the jobs (id, location, title, url).
    #   elist <company>         → summary: count + first 100 lines (one job per line)
    #   elist <company> --all   → all jobs
    #   elist <company> --json  → raw JSON of all mapped jobs
    company="${1:-}"; shift || true
    if [ -z "$company" ]; then echo "Usage: elist <company> [--all|--json]"; exit 1; fi
    mode="${1:-summary}"
    cd "$BACKEND"; source venv/bin/activate 2>/dev/null || true
    company="$company" mode="$mode" python -c "
import os, sys, json, asyncio
from extractors_v2.registry import get_extractor
company = os.environ['company']; mode = os.environ['mode']
try:
    cls = get_extractor(company)
except ValueError as e:
    print('✗', e); sys.exit(1)
ext = cls()
jobs = asyncio.run(ext._fetch_all_jobs())
rows = [{'id': j['id'], 'title': j['title'].strip(), 'location': j.get('location',''),
         'url': ext._build_url(j)} for j in jobs]
if mode == '--json':
    print(json.dumps(rows, indent=2)); sys.exit(0)
print(f'{company}: {len(rows)} jobs')
shown = rows if mode == '--all' else rows[:100]
for r in shown:
    print(f\"  {r['location'][:28]:28} {r['title'][:50]:50} {r['url']}\")
if mode != '--all' and len(rows) > 100:
    print(f'  … (+{len(rows)-100} more — use --all)')
"
    ;;
  ejd)
    # Fetch one job page (crawl_raw_info) and print the raw content (the JD source).
    #   ejd <company> <job_url>
    company="${1:-}"; joburl="${2:-}"
    if [ -z "$company" ] || [ -z "$joburl" ]; then echo "Usage: ejd <company> <job_url>"; exit 1; fi
    cd "$BACKEND"; source venv/bin/activate 2>/dev/null || true
    company="$company" joburl="$joburl" python -c "
import os, sys, asyncio
from extractors_v2.registry import get_extractor
company = os.environ['company']; url = os.environ['joburl']
try:
    cls = get_extractor(company)
except ValueError as e:
    print('✗', e); sys.exit(1)
raw = asyncio.run(cls().crawl_raw_info(url))
print(f'=== {url} ({len(raw)} chars) ===')
print(raw[:4000])
print('… (truncated)' if len(raw) > 4000 else '')
"
    ;;
  ""|-h|--help|help)
    sed -n '2,14p' "${BASH_SOURCE[0]}"
    ;;
  *)
    echo "unknown verb: $verb (try: elogo, elist, ejd)"
    exit 1
    ;;
esac
