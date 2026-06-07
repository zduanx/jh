"""
Job Hunt MCP Server (Phase 7B).

A SINGLE standalone Python MCP server that exposes internal resources as
LLM-callable tools (ADR-030). Built once; any MCP client connects (the Node
chat agent in 7C; the admin agent in Phase 8).

Design (ADR / PHASE_7B): a tool is a *capability/verb*, not a query shape.
Count/grouping/filter variations are **parameters**; genuinely different actions
are separate tools. Tools are thin wrappers over existing Python logic, called
in-process (no network hop to the logic; no MCP→MCP cascading).

Tools:
  - search_jobs_semantic(user_id, query?, limit, company?)  -> ranked jobs
  - get_job(user_id, job_id)                                -> one job's detail
  - get_resume(user_id)                                     -> the user's resume text
  - score_against_jd(user_id, job_id)                       -> resume↔job fit signal

Run:
  python -m mcp_server.server            # stdio (default; inspector / local client)
  MCP_TRANSPORT=http python -m mcp_server.server   # streamable HTTP (for the Node agent)

NOTE: user_id is a tool argument here. In 7C the chat agent (which holds the
verified JWT) passes the authenticated uid; the server trusts its caller (the
agent), mirroring how the REST layer derives uid from the JWT.
"""

import os

from mcp.server.fastmcp import FastMCP

from db.session import SessionLocal
from db.jobs_service import search_jobs_by_vector, get_job_by_id
from models.resume import Resume
from utils.embeddings import vectorize_text

# Port for the HTTP transport (default 8001 — 8000 is FastAPI). Override with MCP_PORT.
_MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))
# On Lambda, Mangum re-runs the ASGI lifespan per invocation, but FastMCP's
# streamable-http session manager can only .run() once per instance. So on
# Lambda we use stateless_http=True (no persistent session manager — each request
# is independent), which is FastMCP's intended serverless mode. Set MCP_STATELESS=1
# (the Lambda handler does this). Local persistent servers leave it stateful.
_STATELESS = os.environ.get("MCP_STATELESS", "0") == "1"

# FastMCP enables DNS-rebinding protection by default, allowing only localhost
# hosts — which 421-rejects requests to a Lambda Function URL host. We disable it
# because access is gated by our own service-token auth (see handler.py), and the
# Function URL host is dynamic. Only relax this on Lambda (stateless mode).
_transport_security = None
if _STATELESS:
    from mcp.server.transport_security import TransportSecuritySettings
    _transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

mcp = FastMCP(
    "job-hunt",
    host="127.0.0.1",
    port=_MCP_PORT,
    stateless_http=_STATELESS,
    json_response=_STATELESS,
    transport_security=_transport_security,
)


def _session():
    return SessionLocal()


@mcp.tool()
def search_jobs_semantic(
    user_id: int,
    query: str | None = None,
    limit: int = 10,
    company: str | None = None,
) -> list[dict]:
    """
    Find the user's jobs most relevant to their resume (or to `query` if given),
    ranked by semantic similarity (RAG retrieval over pgvector).

    Use this for "best jobs for me", "top N jobs", "jobs about <topic>", or
    "jobs at <company>". Vary `limit` for "top 5/10/20"; pass `company` to scope
    to one company; pass `query` to match a topic instead of the resume.

    Args:
        user_id: the authenticated user's id (provided by the agent).
        query: optional topic to match against; if omitted, matches the resume.
        limit: how many jobs to return (default 10).
        company: optional company filter (e.g. "anthropic").

    Returns: list of {job_id, company, title, location, similarity}, best first.
    """
    db = _session()
    try:
        # Decide what to match against: the query (topic) or the resume vector.
        if query:
            query_vec = vectorize_text(query, input_type="query")
        else:
            resume = db.query(Resume).filter(Resume.user_id == user_id).first()
            if not resume or resume.embedding is None:
                return []  # no resume to match against
            query_vec = [float(x) for x in resume.embedding]

        # Over-fetch when filtering by company (filter is applied post-rank below).
        fetch_k = limit * 5 if company else limit
        results = search_jobs_by_vector(db, user_id, query_vec, top_k=fetch_k)

        out = []
        for job, dist in results:
            if company and (job.company or "").lower() != company.lower():
                continue
            out.append({
                "job_id": job.id,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "similarity": round(1 - dist, 4),
            })
            if len(out) >= limit:
                break
        return out
    finally:
        db.close()


@mcp.tool()
def get_job(user_id: int, job_id: int) -> dict | None:
    """
    Get one job's full detail (title, company, location, description,
    requirements, url). Use after search to read a specific job in depth.

    Returns the job dict, or None if not found / not owned by the user.
    """
    db = _session()
    try:
        job = get_job_by_id(db, job_id, user_id)
        if not job:
            return None
        return {
            "job_id": job.id,
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "url": job.url,
            "description": job.description,
            "requirements": job.requirements,
            "status": job.status,
        }
    finally:
        db.close()


@mcp.tool()
def get_resume(user_id: int) -> dict | None:
    """
    Get the user's profile resume text (what the assistant reasons over for fit).

    Returns {filename, text} or None if no resume uploaded.
    """
    db = _session()
    try:
        resume = db.query(Resume).filter(Resume.user_id == user_id).first()
        if not resume or not resume.extracted_text:
            return None
        return {"filename": resume.filename, "text": resume.extracted_text}
    finally:
        db.close()


@mcp.tool()
def score_against_jd(user_id: int, job_id: int) -> dict | None:
    """
    A quick resume↔job fit signal: the semantic similarity between the user's
    resume and a specific job. (Higher = closer. A coarse signal — the agent can
    reason over get_resume + get_job for a nuanced assessment.)

    Returns {job_id, title, similarity} or None if resume/job missing.
    """
    db = _session()
    try:
        resume = db.query(Resume).filter(Resume.user_id == user_id).first()
        if not resume or resume.embedding is None:
            return None
        job = get_job_by_id(db, job_id, user_id)
        if not job or job.embedding is None:
            return None
        # Cosine similarity in plain Python (both vectors on hand).
        import math
        a = [float(x) for x in resume.embedding]
        b = [float(x) for x in job.embedding]
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        sim = dot / (na * nb) if na and nb else 0.0
        return {"job_id": job.id, "title": job.title, "similarity": round(sim, 4)}
    finally:
        db.close()


def main():
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
