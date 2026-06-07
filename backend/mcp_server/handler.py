"""
Lambda handler for the MCP server (Phase 7B, Step 6).

Wraps FastMCP's streamable-http ASGI app with Mangum so it runs on AWS Lambda
behind a Function URL (no API Gateway — like the chat Lambda). Adds
service-to-service auth: the caller (the chat agent / admin agent) must send a
shared secret. The Function URL is AuthType: NONE, so this in-handler check is
the only gate — without it, anyone could call get_resume(user_id=...) and read
another user's data.

Auth model (see MCP auth ADR): the MCP server's caller is a trusted backend
SERVICE (the agent), not the end user. So this is service-to-service auth (a
shared MCP_SERVICE_TOKEN). The agent itself verifies the user's JWT and passes
the authenticated user_id as a tool argument. NOT CORS — CORS only restricts
browsers; this endpoint is called server-to-server.
"""

import os

# Stateless mode: each request independent (right for Lambda + our stateless tools).
# Must be set BEFORE importing server (FastMCP reads it at construction).
os.environ.setdefault("MCP_STATELESS", "1")

import asyncio
import threading

from mangum import Mangum
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from mcp_server.server import mcp


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests lacking the shared service token. Fail closed."""

    async def dispatch(self, request, call_next):
        expected = os.environ.get("MCP_SERVICE_TOKEN", "")
        if not expected:
            # Misconfigured: refuse rather than run unauthenticated.
            return JSONResponse({"error": "MCP_SERVICE_TOKEN not configured"}, status_code=500)
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        if token != expected:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


# --- The Lambda lifespan problem ---
# FastMCP's streamable-http app has a lifespan that calls session_manager.run().
# Mangum runs the ASGI lifespan PER invocation, but .run() may only be called once
# per instance. On a warm container (object reused), the 2nd invocation re-runs the
# lifespan → RuntimeError → 502.
#
# Fix: start the session manager ONCE at module load (cold start) on a dedicated
# background event loop that lives for the whole container, and tell Mangum
# lifespan="off" so it NEVER re-runs the lifespan per invocation. Warm invocations
# reuse the already-running session manager.

app = mcp.streamable_http_app()
app.add_middleware(ServiceAuthMiddleware)

# Background loop + thread that keeps the session manager's run() context alive
# for the lifetime of the (warm) Lambda container.
_bg_loop = asyncio.new_event_loop()
_session_started = threading.Event()


def _run_session_manager():
    asyncio.set_event_loop(_bg_loop)

    async def _start():
        # Enter the session manager's run() context and hold it open forever
        # (until the container is reclaimed).
        async with mcp.session_manager.run():
            _session_started.set()
            await asyncio.Event().wait()  # block forever, keeping run() active

    _bg_loop.run_until_complete(_start())


# Start once at cold start.
_bg_thread = threading.Thread(target=_run_session_manager, daemon=True)
_bg_thread.start()
_session_started.wait(timeout=10)  # ensure the manager is up before serving

# Mangum with lifespan OFF — we manage the session manager ourselves (above),
# so Mangum must NOT re-run the app lifespan per invocation.
handler = Mangum(app, lifespan="off")
