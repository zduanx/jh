"""
In-container trial runner (Phase 8B). Runs INSIDE the Docker sandbox.

Contract:
  - reads the trial code from STDIN (the LLM-generated snippet)
  - executes it in a namespace where `extractors_v2` is importable
  - the trial communicates its answer by either:
      (a) assigning to a top-level variable `result`, OR
      (b) defining `async def run() -> Any` (we await it), OR
      (c) printing JSON to stdout itself
  - we wrap the outcome in a single JSON object on stdout:
      {"ok": bool, "result": <json-able>, "error": <str|null>, "stdout": <captured>}

Everything dangerous about the trial (arbitrary code, network fetches) is contained
by the CONTAINER (no secrets, read-only FS, timeout, resource limits) — see host_harness.py.
This runner just provides a clean code→result channel.
"""

import sys
import io
import json
import asyncio
import traceback
import contextlib


def _jsonable(x):
    """Best-effort make the result JSON-serializable."""
    try:
        json.dumps(x)
        return x
    except (TypeError, ValueError):
        return repr(x)


def main() -> None:
    code = sys.stdin.read()
    captured = io.StringIO()
    ns: dict = {}

    out = {"ok": False, "result": None, "error": None, "stdout": ""}
    try:
        with contextlib.redirect_stdout(captured):
            # Execute the trial code (defines vars / functions / may fetch).
            exec(compile(code, "<trial>", "exec"), ns)

            # If it defined an async run(), await it and take its return as result.
            if "run" in ns and asyncio.iscoroutinefunction(ns["run"]):
                ns["result"] = asyncio.run(ns["run"]())

        out["ok"] = True
        out["result"] = _jsonable(ns.get("result"))
        out["stdout"] = captured.getvalue()
    except BaseException as e:  # noqa: BLE001 — report ANY failure cleanly
        out["ok"] = False
        out["error"] = f"{type(e).__name__}: {e}"
        out["stdout"] = captured.getvalue()
        out["traceback"] = traceback.format_exc()

    # The ONE line of real stdout the harness parses (everything the trial printed
    # is captured separately in out["stdout"]).
    sys.__stdout__.write(json.dumps(out))
    sys.__stdout__.flush()


if __name__ == "__main__":
    main()
