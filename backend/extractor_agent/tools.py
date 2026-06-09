"""
Local-file tools for the extractor-discovery agent (the "AI coding" part).

The LLM uses these to write its output — like a coding agent (Claude Code / Cursor):
it READS a file, then WRITES it. This demonstrates safe, scoped multi-file editing:
the agent can create extractors_v2/{company}.py AND update extractors_v2/registry.py.

SAFETY (defense in depth):
- All paths are confined to extractors_v2/ (the GENERATED package). Anything outside
  — extractors_v2_base/ (the contract), the rest of backend/, the host — is REFUSED.
- READ-BEFORE-WRITE: write_file refuses to overwrite a file the agent hasn't read
  this session (so it edits based on real current content, not a guess). Creating a
  NEW file is allowed without a prior read.
- The prompt ALSO limits the destination; the code guard here is the hard backstop.

These run on the HOST (they touch the real repo), NOT in the sandbox. Only trial
CODE runs in the sandbox; file edits are the reviewed output (git diff).
"""

from __future__ import annotations

from pathlib import Path

# backend/extractors_v2/  — the ONLY directory these tools may touch.
GENERATED_DIR = (Path(__file__).resolve().parents[1] / "extractors_v2").resolve()


class FileToolError(Exception):
    """Raised for a disallowed path or a write-before-read violation."""


def _resolve(rel_path: str) -> Path:
    """Resolve a path and HARD-ENFORCE it stays within extractors_v2/."""
    # Accept paths with or without the leading "extractors_v2/".
    rel = rel_path.strip().lstrip("/")
    if rel.startswith("extractors_v2/"):
        rel = rel[len("extractors_v2/"):]
    target = (GENERATED_DIR / rel).resolve()
    if target != GENERATED_DIR and GENERATED_DIR not in target.parents:
        raise FileToolError(f"path escapes extractors_v2/: {rel_path!r}")
    if target.suffix != ".py":
        raise FileToolError(f"only .py files allowed: {rel_path!r}")
    return target


class FileTools:
    """Stateful read/write tools for one agent run (tracks what's been read)."""

    def __init__(self):
        self._read: set[Path] = set()

    def read_file(self, path: str) -> dict:
        target = _resolve(path)
        if not target.exists():
            return {"ok": True, "exists": False, "content": "", "path": path}
        content = target.read_text()
        self._read.add(target)
        return {"ok": True, "exists": True, "content": content, "path": path}

    def write_file(self, path: str, content: str) -> dict:
        target = _resolve(path)
        existed = target.exists()
        # READ-BEFORE-WRITE: overwriting requires a prior read this session.
        if existed and target not in self._read:
            raise FileToolError(
                f"refusing to overwrite {path!r} without reading it first — "
                f"call read_file({path!r}) before write_file."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        self._read.add(target)  # a written file is "known" content now
        return {"ok": True, "path": path, "overwrote": existed,
                "bytes": len(content.encode())}
