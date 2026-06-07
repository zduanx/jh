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

# Lambda re-runs the ASGI lifespan per invocation; FastMCP's stateful session
# manager only allows one .run() per instance → use stateless mode on Lambda.
# Must be set BEFORE importing server (FastMCP reads it at construction).
os.environ.setdefault("MCP_STATELESS", "1")

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


# FastMCP's streamable-http ASGI app (Starlette). Add the auth gate in front.
app = mcp.streamable_http_app()
app.add_middleware(ServiceAuthMiddleware)

# Mangum adapts ASGI → Lambda. lifespan="auto" runs FastMCP's session-manager
# lifespan (required for streamable-http).
handler = Mangum(app, lifespan="auto")
