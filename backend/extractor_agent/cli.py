"""
CLI entry for the extractor-discovery agent (Phase 8C).

Usage (via dev.sh):  jcompany [--d] <company> <careers_url>
Direct:              python -m extractor_agent.cli [--d] <company> <url>

Plan-and-Execute (outer) + ReAct (inner): plans the stages, runs each stage's loop.
The agent itself writes its output via read_file/write_file tools (scoped to
extractors_v2/) — extractors_v2/{company}.py + registry.py — uncommitted, review
via `git diff`.  --d = verbose (full thought + trial code each step).
"""

import sys

from .discover import run_agent


def main(argv: list[str]) -> int:
    debug = False        # --d : print full thought + trial code each step
    args = []
    for a in argv:
        if a in ("--d", "--debug"):
            debug = True
        else:
            args.append(a)

    if len(args) < 2:
        print("Usage: python -m extractor_agent.cli [--d] <company> <careers_url>")
        return 1
    company, url = args[0], args[1]

    outcome = run_agent(company, url, debug=debug)

    print()
    if not outcome.ok:
        failed = next((s for s in outcome.stages if not s.ok), None)
        print(f"RESULT: failed at stage '{failed.stage if failed else '?'}' → "
              f"{failed.reason if failed else 'no stages ran'}")
        return 1

    print(f"RESULT: ok — plan {outcome.plan} → {outcome.merged_results}")
    print("  Review the agent's edits with: git status / git diff extractors_v2/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
