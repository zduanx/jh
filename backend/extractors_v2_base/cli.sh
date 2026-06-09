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
    echo "elogo: not implemented yet (Phase 8C)"
    exit 1
    ;;
  elist)
    echo "elist: not implemented yet (Phase 8D)"
    exit 1
    ;;
  ejd)
    echo "ejd: not implemented yet (Phase 8D)"
    exit 1
    ;;
  ""|-h|--help|help)
    sed -n '2,14p' "${BASH_SOURCE[0]}"
    ;;
  *)
    echo "unknown verb: $verb (try: elogo, elist, ejd)"
    exit 1
    ;;
esac
