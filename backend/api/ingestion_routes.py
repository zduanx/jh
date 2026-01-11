"""
API routes for ingestion workflow.

Endpoints:
- GET  /api/ingestion/companies       List available companies from extractor registry
- GET  /api/ingestion/settings        Get user's configured company settings
- POST /api/ingestion/settings        Batch create/update/delete company settings
- POST /api/ingestion/dry-run         Extract job URLs for enabled companies (preview)
- GET  /api/ingestion/current-run     Check for active ingestion run (for page refresh)
- POST /api/ingestion/start           Start ingestion run, returns run_id
- POST /api/ingestion/abort           Abort an active ingestion run
- GET  /api/ingestion/progress/{run_id}  SSE endpoint for real-time progress updates
- GET  /api/ingestion/logs/{run_id}   CloudWatch logs for a run (polling)

Interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Running locally:
    cd backend
    uvicorn main:app --reload
"""

import asyncio
import json
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import Optional, Literal, Any
from datetime import datetime
from sqlalchemy.orm import Session
import boto3
from auth.dependencies import get_current_user, get_current_user_from_token
from db.session import get_db, SessionLocal
from db.company_settings_service import (
    get_user_settings,
    get_enabled_settings,
    batch_operations,
)
from extractors.registry import list_companies
from models.ingestion_run import IngestionRun, RunStatus
from models.job import Job
from sourcing.extractor_utils import run_extractors_async

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class CompanyInfo(BaseModel):
    """Company information for frontend display."""
    name: str
    display_name: str
    logo_url: Optional[str] = None


class CompanySettingResponse(BaseModel):
    """Response model for a single company setting."""
    id: int
    company_name: str
    title_filters: dict
    is_enabled: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingOperation(BaseModel):
    """A single operation in a batch request."""
    op: Literal['upsert', 'delete']
    company_name: str
    title_filters: Optional[dict] = None
    is_enabled: bool = True

    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        """Validate company name exists in registry."""
        available = list_companies()
        if v.lower() not in available:
            raise ValueError(f"Company '{v}' not found. Available: {', '.join(available)}")
        return v.lower()


class OperationResult(BaseModel):
    """Result of a single operation."""
    op: str
    success: bool
    company_name: str
    id: Optional[int] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Company Metadata (static config)
# =============================================================================

# Display names and logos for companies
# Using Google's favicon service (reliable, works for all domains)
# Format: https://www.google.com/s2/favicons?domain={domain}&sz=128
COMPANY_METADATA = {
    "google": {"display_name": "Google", "logo_url": "https://www.google.com/s2/favicons?domain=google.com&sz=128"},
    "amazon": {"display_name": "Amazon", "logo_url": "https://www.google.com/s2/favicons?domain=amazon.com&sz=128"},
    "anthropic": {"display_name": "Anthropic", "logo_url": "https://www.google.com/s2/favicons?domain=anthropic.com&sz=128"},
    "tiktok": {"display_name": "TikTok", "logo_url": "https://www.google.com/s2/favicons?domain=tiktok.com&sz=128"},
    "roblox": {"display_name": "Roblox", "logo_url": "https://www.google.com/s2/favicons?domain=roblox.com&sz=128"},
    "netflix": {"display_name": "Netflix", "logo_url": "https://www.google.com/s2/favicons?domain=netflix.com&sz=128"},
}


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/companies", response_model=list[CompanyInfo])
async def get_available_companies():
    """
    List available companies from extractor registry.

    Returns company names with display metadata for frontend cards.
    No authentication required (public endpoint).

    Returns:
        List of CompanyInfo objects

    Example:
        GET /api/ingestion/companies

        Response:
        [
            {"name": "google", "display_name": "Google", "logo_url": "https://www.google.com/s2/favicons?domain=google.com&sz=128"},
            {"name": "anthropic", "display_name": "Anthropic", "logo_url": "https://www.google.com/s2/favicons?domain=anthropic.com&sz=128"},
            ...
        ]
    """
    companies = list_companies()
    return [
        CompanyInfo(
            name=name,
            display_name=COMPANY_METADATA.get(name, {}).get("display_name", name.title()),
            logo_url=COMPANY_METADATA.get(name, {}).get("logo_url"),
        )
        for name in companies
    ]


@router.get("/settings", response_model=list[CompanySettingResponse])
async def get_settings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user's configured company settings.

    Returns all company settings for the authenticated user.
    Auth: JWT required

    Returns:
        List of CompanySettingResponse objects

    Example:
        GET /api/ingestion/settings
        Authorization: Bearer <jwt_token>

        Response:
        [
            {
                "id": 1,
                "company_name": "anthropic",
                "title_filters": {"include": ["engineer"], "exclude": ["intern"]},
                "is_enabled": true
            },
            ...
        ]
    """
    user_id = current_user["user_id"]
    settings = get_user_settings(db, user_id)
    return settings


@router.post("/settings", response_model=list[OperationResult])
async def batch_update_settings(
    operations: list[SettingOperation],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch create, update, or delete company settings.

    Accepts an array of operations, each with an 'op' field ('upsert' or 'delete').
    Returns an array of results confirming each operation's success.
    Auth: JWT required

    Args:
        operations: List of SettingOperation objects

    Returns:
        List of OperationResult objects

    Example:
        POST /api/ingestion/settings
        Authorization: Bearer <jwt_token>
        [
            {"op": "upsert", "company_name": "google", "title_filters": {"include": ["engineer"]}, "is_enabled": true},
            {"op": "upsert", "company_name": "amazon", "title_filters": {}, "is_enabled": false},
            {"op": "delete", "company_name": "netflix"}
        ]

        Response:
        [
            {"op": "upsert", "success": true, "company_name": "google", "id": 1, "updated_at": "2025-12-18T..."},
            {"op": "upsert", "success": true, "company_name": "amazon", "id": 2, "updated_at": "2025-12-18T..."},
            {"op": "delete", "success": true, "company_name": "netflix"}
        ]
    """
    user_id = current_user["user_id"]

    # Convert Pydantic models to dicts for service layer
    ops_data = [op.model_dump() for op in operations]

    results = batch_operations(db, user_id, ops_data)

    return results


# =============================================================================
# Dry Run Endpoint
# =============================================================================

class JobMetadata(BaseModel):
    """Single job metadata from extraction."""
    id: str
    title: str
    location: str
    url: str


class CompanyDryRunResult(BaseModel):
    """Dry run result for a single company."""
    status: Literal['success', 'error']
    total_count: int = 0
    filtered_count: int = 0
    urls_count: int = 0
    included_jobs: list[JobMetadata] = []
    excluded_jobs: list[JobMetadata] = []
    error_message: Optional[str] = None


@router.post("/dry-run", response_model=dict[str, CompanyDryRunResult])
async def dry_run(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract job URLs for all enabled companies (preview/dry run).

    Reads user's enabled company settings from DB, runs extractors in parallel,
    and returns results keyed by company name. Each company extraction is
    independent - one failure doesn't block others.

    Auth: JWT required

    Returns:
        Dict mapping company_name to CompanyDryRunResult

    Example:
        POST /api/ingestion/dry-run
        Authorization: Bearer <jwt_token>

        Response:
        {
            "google": {
                "status": "success",
                "total_count": 128,
                "filtered_count": 3,
                "urls_count": 125,
                "included_jobs": [
                    {"id": "123", "title": "Software Engineer", "location": "NYC", "url": "https://..."},
                    ...
                ],
                "excluded_jobs": [...],
                "error_message": null
            },
            "amazon": {
                "status": "error",
                "total_count": 0,
                "filtered_count": 0,
                "urls_count": 0,
                "included_jobs": [],
                "excluded_jobs": [],
                "error_message": "Request timed out - career site may be slow"
            }
        }
    """
    user_id = current_user["user_id"]

    # Get enabled settings from DB
    settings = get_enabled_settings(db, user_id)

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enabled companies configured. Add companies in Stage 1."
        )

    # Run extractors in parallel using shared utility
    extractor_results = await run_extractors_async(settings)

    # Convert ExtractorResult dataclasses to dicts for API response
    results: dict[str, Any] = {}
    for company_name, result in extractor_results.items():
        results[company_name] = {
            "status": result.status,
            "total_count": result.total_count,
            "filtered_count": result.filtered_count,
            "urls_count": result.urls_count,
            "included_jobs": result.included_jobs,
            "excluded_jobs": result.excluded_jobs,
            "error_message": result.error_message,
        }

    return results


# =============================================================================
# Start Ingestion Endpoint
# =============================================================================

class CurrentRunResponse(BaseModel):
    """Response for checking current active run."""
    run_id: Optional[int] = None


class StartIngestionResponse(BaseModel):
    """Response for starting an ingestion run."""
    run_id: int


@router.get("/current-run", response_model=CurrentRunResponse)
async def get_current_run(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check for an active ingestion run.

    Returns the most recent run that is not finished or errored.
    Used on page load to resume active runs after refresh.

    Auth: JWT required

    Returns:
        CurrentRunResponse with run_id if active run exists,
        or run_id=null if no active run.

    Example:
        GET /api/ingestion/current-run
        Authorization: Bearer <jwt_token>

        Response (active run exists):
        {
            "run_id": 123
        }

        Response (no active run):
        {
            "run_id": null
        }
    """
    user_id = current_user["user_id"]

    # Find most recent non-terminal run
    run = db.query(IngestionRun).filter(
        IngestionRun.user_id == user_id,
        IngestionRun.status.notin_(RunStatus.TERMINAL)
    ).order_by(IngestionRun.created_at.desc()).first()

    if run:
        return CurrentRunResponse(run_id=run.id)
    else:
        return CurrentRunResponse(run_id=None)


class StartIngestionRequest(BaseModel):
    """Request body for starting ingestion."""
    force: bool = False  # Phase 2L: bypass SimHash check when True


@router.post("/start", response_model=StartIngestionResponse)
async def start_ingestion(
    request: StartIngestionRequest = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a new ingestion run.

    Creates an ingestion_runs record with status='pending', triggers the async
    worker Lambda, and returns the run_id immediately.
    Frontend uses this run_id to connect to the SSE progress endpoint.

    Auth: JWT required

    Request body (optional):
        force: bool - If true, bypass SimHash check and re-crawl all jobs

    Returns:
        StartIngestionResponse with run_id

    Example:
        POST /api/ingestion/start
        Authorization: Bearer <jwt_token>
        Body: { "force": true }

        Response:
        {
            "run_id": 123
        }
    """
    # Handle None request (no body sent)
    force = request.force if request else False

    user_id = current_user["user_id"]

    # Verify user has enabled companies before starting
    settings = get_enabled_settings(db, user_id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enabled companies configured. Add companies in Stage 1."
        )

    # Create ingestion run record with force flag in metadata
    run_metadata = {"force": force} if force else {}
    run = IngestionRun(user_id=user_id, status=RunStatus.PENDING, run_metadata=run_metadata)
    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info(f"Created ingestion run {run.id} for user {user_id}, force={force}")

    # Trigger async worker Lambda
    worker_function_name = os.environ.get("WORKER_FUNCTION_NAME")
    if worker_function_name:
        try:
            lambda_client = boto3.client("lambda")

            # Check if we're running locally (not in Lambda)
            # If local, pass use_test_db=true so worker uses TEST_DATABASE_URL
            is_local = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None
            payload_data = {
                "run_id": run.id,
                "user_id": user_id,
                "use_test_db": is_local,  # True for local dev, False for Lambda
                "force": force,  # Phase 2L: pass force flag to worker
            }
            payload = json.dumps(payload_data)

            # InvocationType='Event' = async invoke (fire-and-forget)
            # Returns immediately with 202 Accepted
            response = lambda_client.invoke(
                FunctionName=worker_function_name,
                InvocationType="Event",
                Payload=payload,
            )

            logger.info(
                f"Invoked worker {worker_function_name} for run {run.id}, "
                f"StatusCode={response.get('StatusCode')}, use_test_db={is_local}, force={force}"
            )
        except Exception as e:
            # Log but don't fail - run record exists, can be recovered
            logger.exception(f"Failed to invoke worker for run {run.id}: {e}")
            # Mark run as error so it can be retried
            run.status = RunStatus.ERROR
            run.error_message = f"Failed to start worker: {str(e)[:200]}"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start ingestion worker"
            )
    else:
        # Local development - no worker Lambda configured
        logger.warning(f"WORKER_FUNCTION_NAME not set, run {run.id} will stay pending")

    return StartIngestionResponse(run_id=run.id)


# =============================================================================
# Abort Ingestion Endpoint
# =============================================================================

class AbortResponse(BaseModel):
    """Response for aborting an ingestion run."""
    success: bool
    message: str


@router.post("/abort/{run_id}", response_model=AbortResponse)
async def abort_ingestion(
    run_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Abort an active ingestion run.

    Sets the run status to 'aborted'. Only works for runs that are not
    already in a terminal state (finished, error, aborted).
    Security: JWT user_id must match run's user_id.

    Auth: JWT required

    Args:
        run_id: Path parameter - the run to abort

    Returns:
        AbortResponse with success status and message

    Example:
        POST /api/ingestion/abort/123
        Authorization: Bearer <jwt_token>

        Response:
        {
            "success": true,
            "message": "Run 123 aborted"
        }
    """
    user_id = current_user["user_id"]

    # Find the run (user_id check ensures security)
    run = db.query(IngestionRun).filter(
        IngestionRun.id == run_id,
        IngestionRun.user_id == user_id
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Check if run is in a terminal state
    if run.status in RunStatus.TERMINAL:
        return AbortResponse(
            success=False,
            message=f"Run {run_id} is already {run.status}"
        )

    # Abort the run
    run.status = RunStatus.ABORTED
    db.commit()

    logger.info(f"Aborted ingestion run {run.id} for user {user_id}")

    return AbortResponse(success=True, message=f"Run {run_id} aborted")


# =============================================================================
# SSE Progress Endpoint
# =============================================================================


def _build_jobs_by_company(jobs: list[Job]) -> dict[str, list[dict]]:
    """
    Build job map grouped by company.

    Returns: {company: [{external_id, title, status}, ...]}
    """
    result: dict[str, list[dict]] = {}
    for job in jobs:
        if job.company not in result:
            result[job.company] = []
        result[job.company].append({
            "external_id": job.external_id,
            "title": job.title,
            "status": job.status,
        })
    return result


def _compute_job_diffs(
    prev_state: dict[str, dict[str, str]],
    curr_jobs: list[Job]
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """
    Compute diff between previous state and current jobs.

    Args:
        prev_state: {company: {external_id: status, ...}}
        curr_jobs: Current job list from DB

    Returns:
        (new_state, diff) where diff only contains changed statuses
    """
    # Build current state map
    curr_state: dict[str, dict[str, str]] = {}
    for job in curr_jobs:
        if job.company not in curr_state:
            curr_state[job.company] = {}
        curr_state[job.company][job.external_id] = job.status

    # Compute diff
    diff: dict[str, dict[str, str]] = {}
    for company, jobs_map in curr_state.items():
        prev_company = prev_state.get(company, {})
        for ext_id, status in jobs_map.items():
            if prev_company.get(ext_id) != status:
                if company not in diff:
                    diff[company] = {}
                diff[company][ext_id] = status

    return curr_state, diff


async def _progress_generator(run_id: int, user_id: int):
    """
    Generator for SSE progress events.

    Event types:
    - status: Run status string (pending, initializing, finished, error, aborted)
    - all_jobs: Full job map on first poll during ingesting phase
    - update: Diff of changed job statuses during ingesting phase

    Polls DB every 3 seconds. Stops when run reaches terminal status.
    Uses db.expire_all() before each poll to see committed changes from other sessions.

    TEMP: Forces close after 30s to test reconnection locally (simulates API Gateway timeout).
    """
    import time
    start_time = time.time()

    # Track previous job state for computing diffs
    prev_job_state: dict[str, dict[str, str]] = {}
    sent_all_jobs = False

    db = SessionLocal()
    try:
        while True:
            # TEMP: Force close after 30s to simulate AWS API Gateway timeout
            # API Gateway terminates connections abruptly - no chance to send data
            if time.time() - start_time > 30:
                logger.info(f"SSE forcing close after 30s for run {run_id} (simulating API Gateway timeout)")
                raise Exception("Simulated API Gateway 29s timeout")
            # Expire all cached objects so next query fetches fresh data
            # This is the standard SQLAlchemy pattern for long-running sessions
            db.expire_all()

            # Fetch current run state
            run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

            if not run:
                yield f"event: error\ndata: Run not found\n\n"
                break

            # Security check: verify user owns this run
            if run.user_id != user_id:
                yield f"event: error\ndata: Not authorized\n\n"
                break

            # Handle based on run status
            if run.status in [RunStatus.PENDING, RunStatus.INITIALIZING]:
                # No jobs yet, just emit status
                yield f"event: status\ndata: {run.status}\n\n"

            elif run.status == RunStatus.INGESTING:
                # Poll jobs table for real-time updates
                jobs = db.query(Job).filter(Job.run_id == run_id).all()
                logger.info(f"SSE poll run {run_id}: {len(jobs)} jobs, sent_all_jobs={sent_all_jobs}")

                if not sent_all_jobs:
                    # First poll: emit full job map
                    jobs_by_company = _build_jobs_by_company(jobs)
                    logger.info(f"SSE emitting all_jobs for run {run_id}")
                    yield f"event: all_jobs\ndata: {json.dumps(jobs_by_company)}\n\n"

                    # Initialize prev_state for diff tracking
                    for job in jobs:
                        if job.company not in prev_job_state:
                            prev_job_state[job.company] = {}
                        prev_job_state[job.company][job.external_id] = job.status

                    sent_all_jobs = True
                else:
                    # Subsequent polls: emit only diffs
                    prev_job_state, diff = _compute_job_diffs(prev_job_state, jobs)
                    if diff:
                        logger.info(f"SSE emitting update for run {run_id}: {len(diff)} companies")
                        yield f"event: update\ndata: {json.dumps(diff)}\n\n"

            elif run.status in RunStatus.TERMINAL:
                # Terminal status - emit final job state, then status, then close
                jobs = db.query(Job).filter(Job.run_id == run_id).all()
                if jobs:
                    # Always send final all_jobs so frontend has complete state
                    jobs_by_company = _build_jobs_by_company(jobs)
                    yield f"event: all_jobs\ndata: {json.dumps(jobs_by_company)}\n\n"
                yield f"event: status\ndata: {run.status}\n\n"
                break

            # Wait before next poll
            await asyncio.sleep(3)
    except Exception as e:
        logger.exception(f"SSE generator error for run {run_id}: {e}")
        yield f"event: error\ndata: Server error\n\n"
    finally:
        db.close()


@router.get("/progress/{run_id}")
async def get_progress(
    run_id: int,
    token: str,
):
    """
    SSE endpoint for real-time ingestion progress updates.

    Streams progress events every 2 seconds until the run reaches
    a terminal state (finished, error, aborted).

    Auth: JWT token must be passed as query parameter (?token=xxx)
    because EventSource API cannot send Authorization headers.

    Args:
        run_id: Path parameter - the run to monitor
        token: Query parameter - JWT token for authentication

    Returns:
        StreamingResponse with text/event-stream content type

    Event Types:
        - status: Run status (pending, initializing, finished, error, aborted)
        - all_jobs: Full job map on first poll during ingesting phase
        - update: Diff of changed job statuses during ingesting phase
        - error: Error message (run not found, not authorized, server error)

    Example:
        // Frontend usage
        const es = new EventSource(`/api/ingestion/progress/123?token=${jwt}`);

        es.addEventListener('status', (e) => {
            console.log('Status:', e.data);  // "pending", "initializing", "finished"
            if (['finished', 'error', 'aborted'].includes(e.data)) {
                es.close();
            }
        });

        es.addEventListener('all_jobs', (e) => {
            const jobs = JSON.parse(e.data);
            // jobs = {google: [{external_id, title, status}, ...], amazon: [...]}
            setJobs(jobs);
        });

        es.addEventListener('update', (e) => {
            const diff = JSON.parse(e.data);
            // diff = {google: {external_id: "ready"}, amazon: {ext_id: "error"}}
            applyDiff(diff);
        });

        es.addEventListener('error', (e) => {
            console.error('SSE error:', e.data);
            es.close();
        });

    Event format (SSE):
        event: status
        data: pending

        event: all_jobs
        data: {"google": [{"external_id": "123", "title": "Engineer", "status": "pending"}]}

        event: update
        data: {"google": {"123": "ready"}}

        event: status
        data: finished
    """
    # Authenticate using query param token
    current_user = get_current_user_from_token(token)
    user_id = current_user["user_id"]

    return StreamingResponse(
        _progress_generator(run_id, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# =============================================================================
# CloudWatch Logs Streaming Endpoint
# =============================================================================

class LogEntry(BaseModel):
    """Single log entry from CloudWatch."""
    timestamp: int
    message: str
    source: str  # Worker type: "ingestion", "crawler", "extractor"
    ingestion_time: Optional[int] = None


class LogsResponse(BaseModel):
    """Response containing log entries and pagination token."""
    logs: list[LogEntry]
    next_token: Optional[str] = None


# Map short names to CloudWatch log groups (ADR-019)
LOG_GROUP_MAP = {
    "ingestion": "/aws/lambda/IngestionWorker",
    "crawler": "/aws/lambda/CrawlerWorker",
    "extractor": "/aws/lambda/ExtractorWorker",  # Phase 2K
}

# Map short names to CloudWatch filter patterns
LOG_FILTER_MAP = {
    "ingestion": lambda run_id: f'"[IngestionWorker" "run_id={run_id}]"',
    "crawler": lambda run_id: f'"[CrawlerWorker" "run_id={run_id}"',
    "extractor": lambda run_id: f'"[ExtractorWorker" "run_id={run_id}"',  # Phase 2K
}


@router.get("/logs/{run_id}", response_model=LogsResponse)
async def get_worker_logs(
    run_id: int,
    token: str,
    groups: Optional[str] = None,
    start_time: Optional[int] = None,
    limit: int = 100,
):
    """
    Get CloudWatch logs for a specific ingestion run from multiple workers.

    Fetches logs from IngestionWorker and CrawlerWorker Lambdas, filtered by
    the log prefix pattern for each worker type. Results are merged and sorted
    by timestamp.

    Uses FilterLogEvents API (free tier: 1M requests/month).

    Auth: JWT token must be passed as query parameter (?token=xxx)
    because EventSource API cannot send Authorization headers.

    Args:
        run_id: Path parameter - the run to get logs for
        token: Query parameter - JWT token for authentication
        groups: Optional - Comma-separated worker types to query (default: all)
                Valid values: ingestion, crawler
        start_time: Optional - Unix timestamp (ms) to start from
        limit: Optional - Max number of log entries per group (default 100, max 500)

    Returns:
        LogsResponse with log entries sorted by timestamp

    Example:
        // Fetch all worker logs
        GET /api/ingestion/logs/123?token=xxx

        // Fetch only ingestion logs
        GET /api/ingestion/logs/123?token=xxx&groups=ingestion

        // Fetch crawler logs only
        GET /api/ingestion/logs/123?token=xxx&groups=crawler

        // Polling for new logs (pass last timestamp + 1)
        GET /api/ingestion/logs/123?token=xxx&start_time=1704067200001
    """
    # Authenticate using query param token
    current_user = get_current_user_from_token(token)
    user_id = current_user["user_id"]

    # Verify user owns this run
    db = SessionLocal()
    try:
        run = db.query(IngestionRun).filter(
            IngestionRun.id == run_id,
            IngestionRun.user_id == user_id
        ).first()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {run_id} not found"
            )
    finally:
        db.close()

    # Determine which groups to query (ADR-019)
    if groups:
        group_keys = [g.strip() for g in groups.split(",") if g.strip() in LOG_GROUP_MAP]
    else:
        group_keys = list(LOG_GROUP_MAP.keys())

    if not group_keys:
        return LogsResponse(logs=[], next_token=None)

    # Query CloudWatch Logs for each group
    logs_client = boto3.client("logs")
    all_logs: list[LogEntry] = []

    # Default start time to last 24 hours
    import time
    effective_start_time = start_time if start_time else int((time.time() - 86400) * 1000)

    for group_key in group_keys:
        log_group = LOG_GROUP_MAP[group_key]
        filter_pattern = LOG_FILTER_MAP[group_key](run_id)

        try:
            params = {
                "logGroupName": log_group,
                "filterPattern": filter_pattern,
                "startTime": effective_start_time,
                "limit": min(limit, 500),  # Cap per-group limit
            }

            response = logs_client.filter_log_events(**params)

            # Add logs with source tag
            for event in response.get("events", []):
                all_logs.append(LogEntry(
                    timestamp=event["timestamp"],
                    message=event["message"],
                    source=group_key,
                    ingestion_time=event.get("ingestionTime"),
                ))

        except logs_client.exceptions.ResourceNotFoundException:
            # Log group doesn't exist yet (no Lambda invocations)
            logger.debug(f"Log group {log_group} not found (no invocations yet)")
            continue

        except Exception as e:
            logger.warning(f"Failed to fetch logs from {log_group}: {e}")
            continue

    # Sort all logs by timestamp
    all_logs.sort(key=lambda x: x.timestamp)

    # Apply total limit (after merge)
    if len(all_logs) > limit:
        all_logs = all_logs[:limit]

    return LogsResponse(logs=all_logs, next_token=None)
