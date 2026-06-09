"""
Phase 8B — the sandbox safety proof.

A broken sandbox is worse than none, so these PROVE the isolation before any agent
depends on run_trial(): safe code works; malicious code is contained.

Run:  python3 -m pytest backend/extractor_agent/sandbox/__tests__/test_sandbox.py -v
      (needs Docker running; auto-skips if docker is not installed.)
"""

import shutil
import pytest

from extractor_agent.sandbox.host_harness import run_trial, build_image

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="docker not installed — install Docker Desktop (Phase 8B step 0)",
)


@pytest.fixture(scope="module", autouse=True)
def _image():
    build_image()  # build once for the module


# --------------------------------------------------------------------------- #
# Legit use
# --------------------------------------------------------------------------- #
def test_safe_snippet_returns_result():
    r = run_trial("result = {'hello': 'world', 'n': 1 + 1}")
    assert r.ok
    assert r.result == {"hello": "world", "n": 2}


def test_async_run_is_awaited():
    code = "async def run():\n    return [1, 2, 3]\n"
    r = run_trial(code)
    assert r.ok
    assert r.result == [1, 2, 3]


def test_can_import_extractors_v2():
    # The whole point: trial code extends the baked-in framework.
    code = (
        "from extractors_v2_base import BaseExtractorV2, Company\n"
        "result = Company.GOOGLE.value\n"
    )
    r = run_trial(code)
    assert r.ok
    assert r.result == "google"


def test_network_fetch_works():
    code = (
        "import httpx\n"
        "async def run():\n"
        "    resp = httpx.get('https://example.com', timeout=15)\n"
        "    return resp.status_code\n"
    )
    r = run_trial(code, timeout=30)
    assert r.ok
    assert r.result == 200


# --------------------------------------------------------------------------- #
# Containment — the malicious / broken cases
# --------------------------------------------------------------------------- #
def test_secrets_not_visible():
    # No host filesystem, no env secrets → can't read AWS creds / .env.
    code = (
        "import os\n"
        "result = {\n"
        "  'aws_exists': os.path.exists(os.path.expanduser('~/.aws/credentials')),\n"
        "  'has_anthropic_key': 'ANTHROPIC_API_KEY' in os.environ,\n"
        "}\n"
    )
    r = run_trial(code)
    assert r.ok
    assert r.result["aws_exists"] is False
    assert r.result["has_anthropic_key"] is False


def test_filesystem_is_read_only():
    # Writing outside /tmp should fail (read-only FS) → contained.
    code = "open('/app/evil.txt', 'w').write('pwned'); result = 'wrote'"
    r = run_trial(code)
    # Either the write raises (ok=False) — the container FS is read-only.
    assert r.ok is False
    assert r.error is not None


def test_infinite_loop_times_out():
    r = run_trial("while True:\n    pass\n", timeout=5)
    assert r.timed_out is True
    assert r.ok is False


def test_no_network_when_disabled():
    # With network='none', a fetch must fail → proves we can cut the network.
    code = (
        "import httpx\n"
        "async def run():\n"
        "    return httpx.get('https://example.com', timeout=5).status_code\n"
    )
    r = run_trial(code, network="none", timeout=20)
    assert r.ok is False  # no network → the fetch errors


def test_exception_reported_cleanly():
    r = run_trial("raise ValueError('boom')")
    assert r.ok is False
    assert "ValueError" in (r.error or "")
