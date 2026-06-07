"""
Service-to-service auth tests for the MCP Lambda handler (ADR-033).

The Function URL is AuthType: NONE, so `ServiceAuthMiddleware` is the ONLY gate
in front of tools that return private user data. We test its three contracts:
  - fail closed: misconfigured (no MCP_SERVICE_TOKEN) -> 500, never serve open
  - reject:      missing / wrong bearer token -> 401
  - allow:       correct bearer token -> request reaches the app

We exercise the middleware directly with a Starlette test app (a trivial inner
app standing in for FastMCP), so this is fast and has no DB / Lambda dependency.

Run: python3 -m pytest mcp_server/__tests__/test_auth_middleware.py -v
"""
import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp_server.handler import ServiceAuthMiddleware


def build_client(monkeypatch, token_env):
    """A minimal app wrapped in the real middleware; env token = `token_env`."""
    if token_env is None:
        monkeypatch.delenv("MCP_SERVICE_TOKEN", raising=False)
    else:
        monkeypatch.setenv("MCP_SERVICE_TOKEN", token_env)

    async def ok(_request):
        return PlainTextResponse("reached-app")

    app = Starlette(routes=[Route("/mcp", ok, methods=["GET", "POST"])])
    app.add_middleware(ServiceAuthMiddleware)
    return TestClient(app)


def test_fail_closed_when_token_unset(monkeypatch):
    client = build_client(monkeypatch, token_env=None)
    resp = client.get("/mcp")
    assert resp.status_code == 500
    assert "not configured" in resp.json()["error"]


def test_rejects_missing_token(monkeypatch):
    client = build_client(monkeypatch, token_env="secret-123")
    resp = client.get("/mcp")  # no Authorization header
    assert resp.status_code == 401


def test_rejects_wrong_token(monkeypatch):
    client = build_client(monkeypatch, token_env="secret-123")
    resp = client.get("/mcp", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_allows_correct_token(monkeypatch):
    client = build_client(monkeypatch, token_env="secret-123")
    resp = client.get("/mcp", headers={"Authorization": "Bearer secret-123"})
    assert resp.status_code == 200
    assert resp.text == "reached-app"


def test_bearer_prefix_is_case_insensitive(monkeypatch):
    client = build_client(monkeypatch, token_env="secret-123")
    resp = client.get("/mcp", headers={"Authorization": "bearer secret-123"})
    assert resp.status_code == 200
