"""
Host-side sandbox harness (Phase 8B): run untrusted LLM trial code in Docker.

`run_trial(code) -> TrialResult` ships a code string into an ephemeral, hardened
container, runs it, and returns the structured result. This is the ONLY thing that
executes generated code — the agent's brain stays on the host (with secrets); only
the trial runs in the box.

Hardening (the isolation that makes generated `rm -rf` / secret-theft harmless):
  --rm                 ephemeral — destroyed on exit (no state leak between trials)
  --network <mode>     default: outbound allowed (to fetch career sites), NO host/internal access
  --read-only          container filesystem read-only ...
  --tmpfs /tmp         ... except a throwaway /tmp
  --memory / --cpus    resource limits (stop runaway code)
  (no -e / --env-file) NO secrets passed in — container can't see API keys / DB creds
  --user (in image)    unprivileged
  timeout              host-side kill for hangs / infinite loops

Build the image once:  build_image()  (or it auto-builds on first run if missing)
"""

from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

IMAGE = "jh-extractor-sandbox"
# build context = backend/  (Dockerfile copies extractors_v2 + the runner from there)
BACKEND_DIR = Path(__file__).resolve().parents[2]
DOCKERFILE = BACKEND_DIR / "extractor_agent" / "sandbox" / "Dockerfile"

DEFAULT_TIMEOUT = 30  # seconds — a discovery trial is short; kill hangs


@dataclass
class TrialResult:
    ok: bool                 # did the trial run AND succeed (no exception)?
    result: object = None    # the trial's `result` value (json-able)
    stdout: str = ""         # what the trial printed
    error: str | None = None # exception summary, if any
    timed_out: bool = False  # killed by the host timeout
    exit_code: int | None = None
    raw: str = ""            # raw container stdout (for debugging)


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def build_image() -> None:
    """Build the sandbox image. Run once (or after Dockerfile/extractors_v2 changes)."""
    if not _docker_available():
        raise RuntimeError("docker not found — install Docker Desktop (Phase 8B step 0)")
    subprocess.run(
        ["docker", "build", "-f", str(DOCKERFILE), "-t", IMAGE, "."],
        cwd=str(BACKEND_DIR), check=True,
    )


def _image_exists() -> bool:
    r = subprocess.run(["docker", "image", "inspect", IMAGE],
                       capture_output=True, text=True)
    return r.returncode == 0


# Monotonic counter for unique container names (no Math.random / wall-clock).
_run_counter = itertools.count(1)


def _kill_container(name: str) -> None:
    """Force-remove a container by name (best effort)."""
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True)


def run_trial(code: str, *, timeout: int = DEFAULT_TIMEOUT,
              network: str = "bridge", memory: str = "256m", cpus: str = "1") -> TrialResult:
    """
    Run `code` in a hardened, ephemeral container; return its TrialResult.

    network: "bridge" = outbound internet (to fetch career sites). Use "none" to
             block all network (for the no-network safety test). NEVER put this on a
             docker network that can reach the host DB / internal services.
    """
    if not _docker_available():
        raise RuntimeError("docker not found — install Docker Desktop (Phase 8B step 0)")
    if not _image_exists():
        build_image()

    # Unique name so we can FORCE-KILL the container on timeout. CRITICAL: a bare
    # subprocess timeout kills only the `docker` CLI, NOT the container — which then
    # keeps running (e.g. an infinite loop pegging a CPU forever). We must kill by name.
    name = f"jh-trial-{os.getpid()}-{next(_run_counter)}"

    cmd = [
        "docker", "run", "--rm", "-i",
        "--name", name,
        "--network", network,
        "--read-only", "--tmpfs", "/tmp",
        "--memory", memory, "--cpus", cpus,
        "--pids-limit", "128",          # prevent fork bombs
        "--cap-drop", "ALL",
        # NOTE: deliberately NO --env / --env-file → container sees no secrets.
        IMAGE,
    ]

    try:
        proc = subprocess.run(
            cmd, input=code, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # The CLI was killed, but the CONTAINER is still running → force-remove it.
        _kill_container(name)
        return TrialResult(ok=False, error="timed out", timed_out=True)
    except BaseException:
        # Any other failure (incl. KeyboardInterrupt) — don't leak the container.
        _kill_container(name)
        raise

    raw = (proc.stdout or "").strip()
    # The runner prints exactly one JSON object as its final stdout.
    try:
        payload = json.loads(raw.splitlines()[-1]) if raw else {}
    except (json.JSONDecodeError, IndexError):
        payload = {}

    return TrialResult(
        ok=bool(payload.get("ok")),
        result=payload.get("result"),
        stdout=payload.get("stdout", ""),
        error=payload.get("error") or (proc.stderr.strip() or None if proc.returncode else None),
        exit_code=proc.returncode,
        raw=raw,
    )
