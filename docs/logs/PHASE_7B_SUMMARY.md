# Phase 7B: MCP Server (Single, Standalone, Python)

**Status**: ✅ Completed
**Date**: June 6, 2026
**Goal**: Build ONE standalone Python MCP server that exposes internal resources (jobs, resume, scoring, semantic search) as LLM-callable tools — consumed by the chat agent now and the admin agent (Phase 8) later.

> **Result:** the MCP server is **deployed and working on AWS** (Function URL, no API Gateway). Verified with a real MCP client over HTTPS: service-token auth (401 without / passes with), `tools/list` returns all 4 tools, `tools/call` executes. Required three Lambda adaptations (stateless mode, run-session-manager-once, disable DNS-rebind protection) — see Key Learnings. (Deployed MCP returns empty until prod jobs/resume are embedded — a data step, not a code issue.)

---

## Overview

7B wraps the Phase 7A logic (and existing service-layer functions) as **MCP tools**, in a **single standalone Python MCP server** ([ADR-030](../architecture/DECISIONS.md#adr-030-single-standalone-python-mcp-server-multi-client)). This is the verbatim HRT JD line — "custom MCP wrapper around internal resources." Built **once**; every consumer connects as an MCP **client** (chat agent in Node now, admin agent in Python in Phase 8).

The server is **Python** (where the logic lives → wraps it in-process, no HTTP hop). Tools are thin adapters over existing Python functions — one source of truth shared with the REST API.

**Included**:
- Standalone Python MCP server (MCP Python SDK): `tools/list` + `tools/call`.
- Tools: `search_jobs`, `search_jobs_semantic`, `get_job`, `get_resume`, `score_against_jd`.
- Machine-readable tool descriptions/schemas (so the LLM can discover/choose).
- Settle transport (stdio vs HTTP/SSE) + hosting (the ADR-030 open sub-decisions).
- Standalone test (MCP inspector / a simple client) before wiring the agent, plus an automated suite (tool logic + in-memory protocol + service auth).

**Excluded**:
- The agent loop / wiring to chat → 7C.
- Admin-specific tools → Phase 8 (added to the same server then).

---

## Build Steps & Status

### Step 1 — Single standalone Python MCP server (FastMCP) ✅
- [mcp_server/server.py](../../backend/mcp_server/server.py) — `FastMCP("job-hunt")`, separate from any consumer ([ADR-030](../architecture/DECISIONS.md#adr-030-single-standalone-python-mcp-server-multi-client)). Multi-client by design.
- Tools = thin wrappers over existing Python logic (in-process; no network hop, no MCP→MCP cascading).
- DB via `SessionLocal` (per-call session, closed in `finally`). `mcp[cli]` added to requirements.
- FastMCP auto-generates `tools/list` / `tools/call` from `@mcp.tool()` decorators (signature → JSON schema, docstring → description).

### Step 2 — Transport (resolve ADR-030 open item) ✅
- Code supports both via `MCP_TRANSPORT` env: `stdio` (default) and `streamable-http` (`MCP_TRANSPORT=http`).
- **Decision:** the deployed chat path uses **HTTP** (Node client + Python server = network boundary; persistent shared server, NOT a subprocess-per-SSE). stdio is for local/same-machine clients. *(If Phase 8's Python agent is same-process, it can skip the protocol entirely and call the tool functions directly / `mcp.call_tool()` in-process — no server, no transport. Transport follows the consumer.)*

### Step 3 — Tool surface (capability-level, parameterized) ✅
- **A tool is a *verb/capability*, NOT a query shape.** Count/grouping/filter variations → **parameters**; different actions → **separate tools**. Few, well-described tools → better LLM tool-selection.
- Built tools:
  - `search_jobs_semantic(user_id, query?, limit=10, company?)` — wraps `search_jobs_by_vector` (7A). `query` → topic match; omit → resume match. Absorbs "top N" / "at company X" as params.
  - `get_job(user_id, job_id)` — one job's full detail.
  - `get_resume(user_id)` — the user's resume text.
  - `score_against_jd(user_id, job_id)` — cosine similarity resume↔job.
- `user_id` is a tool arg: the chat agent (holding the verified JWT) passes the authenticated uid; the server trusts its caller (mirrors REST deriving uid from JWT).

### Step 4 — DB wiring + verification (in-process) ✅
- All 4 tools tested against the test DB (uid 18, 550 embedded jobs): `search_jobs_semantic` returns relevant senior-backend roles; company filter + topic query both work; `get_job`/`get_resume`/`score_against_jd` correct. Consistent with 7A's `/api/resume/match` (shared logic).

### Step 5 — Protocol-level verification ✅
- Real MCP client (`streamablehttp_client` + `ClientSession`) over HTTP did the `initialize` handshake + `tools/list` + `tools/call` — proves it's a working server, not just in-process functions. Verified locally (port 8001) and on AWS.

### Step 6 — Deploy + auth ✅ (deployed to AWS, in the backend stack)
- **Placement (revised):** NOT its own stack — added as a **new `McpServer` Lambda + Function URL in `jh-backend-stack`**, deployed by `jpushapi`. The MCP server is Python and imports backend code (db/utils/models), so it reuses the backend build/deps/env. (Own-stack would duplicate the Python build for the same codebase; chat got its own stack only because it's Node — see Highlights.)
- **Handler** ([mcp_server/handler.py](../../backend/mcp_server/handler.py)): Mangum wraps FastMCP's Starlette ASGI app; Function URL (`AuthType: NONE`, no API Gateway).
- **Auth** ([mcp_server/handler.py](../../backend/mcp_server/handler.py)): `ServiceAuthMiddleware` — service-to-service shared token (`MCP_SERVICE_TOKEN`), 401 without it, fails closed if unconfigured. NOT the user JWT, NOT CORS (server-to-server). The agent passes the verified `user_id`. ([ADR-033](../architecture/DECISIONS.md#adr-033-mcp-server-auth--service-to-service-token-not-cors))
- **SAM wiring** ([scripts/generate_template.py](../../backend/scripts/generate_template.py)): `McpServer` function + `FunctionUrlConfig` + `McpServerUrl` output; `MCP_SERVICE_TOKEN` via Globals + CFN parameter (same `_PARAM_NAME`/`_PROD_VALUE` mechanism as Voyage/JWT).
- **dev.sh:** `jbemcp` / `jbemcp-bg` (HTTP, port 8001) / `jkill-bemcp` / `jbeall` (start all 3 backends) / `jkillall` updated.
- **Verified on AWS:** auth 401/pass, `tools/list` + `tools/call` over the deployed Function URL. (Returns empty until prod data is embedded — a data step.)

### Step 7 — Automated test suite ✅ (regression-proof, replaces one-off checks)
- [mcp_server/__tests__/](../../backend/mcp_server/__tests__/) — **25 pytest tests, all passing**. The Steps 4–6 verification above was *manual / one-off* (a throwaway script against uid 18); Step 7 makes that coverage **permanent and repeatable** (`jbemcp-test`).
- Three layers, the industry-standard MCP layering:
  - **Tool logic** ([test_tools.py](../../backend/mcp_server/__tests__/test_tools.py), 16) — each tool against the **real test DB** (real pgvector `<=>`, SQL, ownership filters); only the live Voyage call is faked. Covers shape contracts, resume-vs-query modes, `limit`, company filter (case-insensitive), and **cross-user data-leak prevention**.
  - **Protocol** ([test_protocol.py](../../backend/mcp_server/__tests__/test_protocol.py), 4) — in-memory client↔server over the **real MCP protocol** (`create_connected_server_and_client_session`): tools registered/discoverable, schemas serialize, `call_tool` round-trips. Catches wiring bugs (un-registered tool, un-serializable signature/return) that direct calls miss.
  - **Service auth** ([test_auth_middleware.py](../../backend/mcp_server/__tests__/test_auth_middleware.py), 5) — ADR-033's `ServiceAuthMiddleware`: fail-closed (500), reject missing/wrong token (401), allow correct token, case-insensitive bearer.
- **Isolation:** [conftest.py](../../backend/mcp_server/__tests__/conftest.py) reuses the db suite's engine/migrations as a pytest plugin; binds the tools' own `SessionLocal()` to a **rolled-back transaction** (standard SQLAlchemy "join an external transaction" pattern) so every test seeds + discards its own data — **data-independent** (safe to wipe test-DB rows). Deterministic 1024-dim fake embedding → offline + free (no Voyage call). `anyio_backend` pinned to asyncio (no new deps).
- **dev.sh:** `jbemcp-test` (run the suite) + `jbemcp-inspect` (launch the official MCP Inspector for manual click-through).

---

## Highlights

### Tool design: parameters for variation, separate tools for capability
"Top 10 jobs" and "top 3 per company" are the **same capability (search) with different parameters** → ONE parameterized tool, not two. The LLM translates phrasing → params (that's what tool-calling does). Separate tools only for genuinely different verbs (search vs. get-one vs. score vs. get-resume). Tool *proliferation* degrades selection accuracy — so keep the surface small and well-described.
- Open sub-choice: handle "top N per company" via a `group_by` param, OR keep the tool dead-simple and let the LLM group `search_jobs_semantic(limit=30)` results in its reasoning. Start simple; add params only if needed.

### Why one Python server, not per-consumer
The point of MCP as a *protocol* is "build the tool surface once; any client connects." Phase 8's admin agent will be a *second client* of this same server — no second MCP server, no duplicated logic. ([ADR-030](../architecture/DECISIONS.md#adr-030-single-standalone-python-mcp-server-multi-client))

### No cascading
Tools call Python logic **in-process**; MCP servers don't call other MCP servers. Flat fan-out of clients → one server → logic.

### MCP ≠ REST
The MCP server is a protocol surface for **LLM agents** (discover + call tools), not a REST API for humans/frontends. The same underlying logic (e.g. `search_jobs_by_vector`) is *also* exposed via REST for the frontend (`/api/resume/match`) — different adapters, same logic.

---

## Testing & Validation

### Automated (permanent — `jbemcp-test`, 25 tests passing)
- [x] **Tool logic** (16) against the real test DB: shapes, resume/query modes, `limit`, company filter (case-insensitive), cross-user isolation, identical-vector cosine ≈ 1.0, None cases.
- [x] **Protocol** (4): in-memory `tools/list` (all 4 + schemas) + `call_tool` round-trips for `get_resume` and `search_jobs_semantic`.
- [x] **Service auth** (5): fail-closed (500), 401 on missing/wrong token, allow correct, case-insensitive bearer.
- [x] Data-independent (transaction rollback) → safe to re-run / wipe test rows; offline (faked embedding, no Voyage call).

### Manual / one-off (during the build)
- [x] `tools/call` against test DB (uid 18, 550 jobs): relevant results, company filter, topic query, get_job/get_resume/score — consistent with 7A's `/api/resume/match` (shared `search_jobs_by_vector`).
- [x] Real MCP client over HTTP (local 8001) — handshake + tools/list + tools/call.
- [x] **Deployed on AWS** — auth (401/pass) + tools/list + tools/call over the Function URL.
- [x] Warm-reuse simulation (handler invoked 3× in one process) → 3× 200 (no `.run()` crash).
- [ ] Prod data embedded so the deployed MCP returns non-empty results (re-extract on prod — data step, not code).

---

## Next Steps → Phase 7C

Build the agent loop in the Node chat service as an **MCP client** to this server; replace the mock.

---

## File Structure

```
backend/
├── mcp_server/
│   ├── server.py          # FastMCP server + the 4 @mcp.tool() functions; main() runs stdio/HTTP
│   ├── handler.py         # Lambda handler: Mangum(FastMCP ASGI) + service-token auth + lifespan fix
│   └── __tests__/         # 25 tests (Step 7)
│       ├── conftest.py            # reuses db engine/migrations; binds SessionLocal to rolled-back txn; fake embedding
│       ├── test_tools.py          # tool logic vs test DB (16)
│       ├── test_protocol.py       # in-memory MCP protocol round trips (4)
│       └── test_auth_middleware.py # ADR-033 service-token auth (5)
├── scripts/generate_template.py   # + McpServer function, FunctionUrlConfig, McpServerUrl output
├── config/settings.py     # + MCP_SERVICE_TOKEN
├── requirements.txt       # + mcp[cli]
└── .env.example           # + MCP_SERVICE_TOKEN (placeholder)

dev.sh                     # jbemcp / jbemcp-bg / jkill-bemcp / jbemcp-test / jbemcp-inspect / jbeall; jkillall updated
```
(Note: tools live in `server.py` directly via `@mcp.tool()` — no separate `tools/` dir needed; they're thin wrappers over `db/jobs_service`, `models/resume`, `utils/embeddings`.)

---

## Key Learnings

### MCP fundamentals
- **FastMCP auto-generates the protocol.** `@mcp.tool()` → FastMCP introspects the signature (→ JSON schema) and docstring (→ description), and builds `tools/list` / `tools/call`. You never hand-write the protocol handlers.
- **`tools/list` / `tools/call` are JSON-RPC messages, not URLs.** Over HTTP it's ONE endpoint (`POST /mcp`) with the method in the body — not REST paths. Over stdio it's JSON over pipes (no HTTP).
- **MCP only earns its place across a boundary** (process / language / network). No boundary → just call the function (or `mcp.call_tool()` in-process). The Node→Python (cross-language) chat path is the real justification; a same-process Python admin agent (Phase 8) could skip MCP entirely.
- **Transport follows the consumer:** HTTP + persistent server for concurrent cross-language clients (chat); stdio + subprocess for occasional same-language/local clients. Same server supports both.

### Running FastMCP on Lambda (three real adaptations — the hard part)
1. **Lifespan runs per invocation, but the session manager runs once.** Lambda reuses warm containers; Mangum runs the ASGI lifespan on each invocation; FastMCP's `StreamableHTTPSessionManager.run()` is "once per instance" → the 2nd warm invocation → `RuntimeError` → **502**. Fix: start the session manager **once at module load** (background thread/loop) and `Mangum(app, lifespan="off")` so it isn't re-run.
2. **Stateless mode for serverless.** `stateless_http=True` + `json_response=True` — each request independent (right for Lambda's request/response model and our stateless lookup tools; we don't need server-push/long sessions, which would require a persistent server anyway).
3. **DNS-rebinding protection 421s non-localhost hosts.** FastMCP allows only `localhost`/`127.0.0.1` by default → a Function URL host → **421**. Disable it (`TransportSecuritySettings(enable_dns_rebinding_protection=False)`); access is gated by our own service-token auth instead.

### Lambda model (reinforced)
- **Lambda is NOT fresh per request** — warm containers are reused; module-level objects persist across invocations (this is *why* the run-once session manager broke). Cold start runs init once; warm starts reuse it.
- **A backend 500 surfaces in the browser as CORS** — but server-to-server (agent→MCP) has no browser; secure it with **auth, not CORS**.

### Deployment placement
- **Deployment boundary follows ownership/coupling, not file location.** The MCP server rides the backend stack because it's Python sharing backend code; a team that *owns* MCP would extract a shared core + deploy independently. Chat is its own stack because it's Node (can't share a Python build) — a language constraint, not an architectural law.

### Testing an MCP server (the standard layering)
- **Test the tool functions directly AND through the protocol.** Direct calls verify logic; the SDK's **in-memory** client/server (`create_connected_server_and_client_session`, no sockets) verifies the *wiring* — that tools are registered, schemas serialize, and `call_tool` round-trips. The in-memory layer catches a defined-but-unregistered tool or an un-serializable return that a direct call never would.
- **Make DB tests data-independent.** Bind the code's own `SessionLocal` to a connection inside a per-test transaction and **roll back** at the end (SQLAlchemy "join an external transaction"). Each test seeds + discards its own rows, so the suite never depends on what's in the test DB — re-runnable, parallel-safe, and immune to row deletes. (`get_or_create` for the shared fixed user keeps even that self-healing.)
- **Fake the paid/network edge, keep the real DB.** Embeddings are faked with a deterministic hash→vector (offline, free, repeatable); the pgvector search itself runs for real, so the SQL/index path is genuinely exercised. Retrieval *quality* is a separate concern (the eval harness), not a unit test.
- **FastMCP wraps non-object returns under `"result"`.** A tool typed `dict | None` or `list[...]` comes back as `structuredContent["result"]`, not keyed directly — assert accordingly.

---

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK / FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- [Mangum (ASGI → Lambda)](https://mangum.io/)
- [ADR-030](../architecture/DECISIONS.md#adr-030-single-standalone-python-mcp-server-multi-client) · [vectors-rag-eval.md](../learning/vectors-rag-eval.md)
