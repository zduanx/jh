"""
API routes for job listing, details, and sync (Phase 3A/3B).

Endpoints:
- GET  /api/jobs                            List all jobs grouped by company
- GET  /api/jobs/{job_id}                   Get full job details
- POST /api/jobs/sync                       Sync all jobs (extract URLs, UPSERT, mark expired)
- POST /api/jobs/re-extract              Re-extract job(s) from S3 HTML (body: job_id or company)

Interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from db.session import get_db
from db.jobs_service import get_jobs_grouped_by_company, get_job_by_id, upsert_jobs, mark_expired_jobs
from db.company_settings_service import get_enabled_settings
from models.ingestion_run import IngestionRun, RunStatus
from sourcing.extractor_utils import run_extractors_async

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Company Metadata (shared with ingestion_routes.py)
# =============================================================================

# Display names and logos for companies
# Using Google's favicon service (reliable, works for all domains)
COMPANY_METADATA = {
    "google": {"display_name": "Google", "logo_url": "https://www.google.com/s2/favicons?domain=google.com&sz=128"},
    "amazon": {"display_name": "Amazon", "logo_url": "https://www.google.com/s2/favicons?domain=amazon.com&sz=128"},
    "anthropic": {"display_name": "Anthropic", "logo_url": "https://www.google.com/s2/favicons?domain=anthropic.com&sz=128"},
    "tiktok": {"display_name": "TikTok", "logo_url": "https://www.google.com/s2/favicons?domain=tiktok.com&sz=128"},
    "roblox": {"display_name": "Roblox", "logo_url": "https://www.google.com/s2/favicons?domain=roblox.com&sz=128"},
    "netflix": {"display_name": "Netflix", "logo_url": "https://www.google.com/s2/favicons?domain=netflix.com&sz=128"},
}


# =============================================================================
# Pydantic Models
# =============================================================================

class JobSummary(BaseModel):
    """Job summary for list display."""
    id: int
    title: Optional[str]
    location: Optional[str]


class CompanyJobs(BaseModel):
    """Company with its jobs."""
    name: str
    display_name: str
    logo_url: Optional[str]
    ready_count: int
    jobs: list[JobSummary]


class JobsListResponse(BaseModel):
    """Response for GET /api/jobs."""
    companies: list[CompanyJobs]
    total_ready: int


class JobDetailResponse(BaseModel):
    """Response for GET /api/jobs/{job_id}."""
    id: int
    company: str
    external_id: str
    title: Optional[str]
    location: Optional[str]
    url: str
    status: str
    description: Optional[str]
    requirements: Optional[str]
    raw_s3_url: Optional[str]
    updated_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=JobsListResponse)
async def list_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all jobs for the authenticated user, grouped by company.

    Returns only READY jobs, grouped by company with counts.
    Auth: JWT required

    Returns:
        JobsListResponse with companies and total_ready count

    Example:
        GET /api/jobs
        Authorization: Bearer <jwt_token>

        Response:
        {
            "companies": [
                {
                    "name": "google",
                    "display_name": "Google",
                    "logo_url": "https://...",
                    "ready_count": 45,
                    "jobs": [
                        {"id": 123, "title": "K8s Engineer", "location": "Seattle, WA"},
                        ...
                    ]
                }
            ],
            "total_ready": 126
        }
    """
    user_id = current_user["user_id"]

    # Get jobs grouped by company from service
    jobs_by_company = get_jobs_grouped_by_company(db, user_id)

    # Build response with company metadata
    companies = []
    total_ready = 0

    for company_name, jobs in jobs_by_company.items():
        metadata = COMPANY_METADATA.get(company_name, {})
        ready_count = len(jobs)
        total_ready += ready_count

        companies.append(CompanyJobs(
            name=company_name,
            display_name=metadata.get("display_name", company_name.title()),
            logo_url=metadata.get("logo_url"),
            ready_count=ready_count,
            jobs=[
                JobSummary(id=job.id, title=job.title, location=job.location)
                for job in jobs
            ]
        ))

    # Sort companies by name for consistent ordering
    companies.sort(key=lambda c: c.name)

    return JobsListResponse(companies=companies, total_ready=total_ready)


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_details(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get full job details including description and requirements.

    Auth: JWT required
    Security: Only returns jobs owned by the authenticated user.

    Args:
        job_id: Path parameter - the job ID

    Returns:
        JobDetailResponse with full job data

    Example:
        GET /api/jobs/123
        Authorization: Bearer <jwt_token>

        Response:
        {
            "id": 123,
            "company": "google",
            "external_id": "abc123",
            "title": "Kubernetes Platform Engineer",
            "location": "Seattle, WA",
            "url": "https://careers.google.com/...",
            "status": "ready",
            "description": "Build and maintain...",
            "requirements": "• 3+ years...",
            "raw_s3_url": "s3://bucket/raw/google/abc123.html",
            "updated_at": "2026-01-12T10:30:00Z"
        }
    """
    user_id = current_user["user_id"]

    job = get_job_by_id(db, job_id, user_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return JobDetailResponse.model_validate(job)


# =============================================================================
# Phase 3B: Sync All Jobs
# =============================================================================

class CompanySyncResult(BaseModel):
    """Sync result for a single company."""
    company: str
    found: int        # Total jobs found by extractor on career page (B)
    existing: int     # Jobs in DB AND still on career page (A ∩ B)
    new: int          # Jobs on career page but not in DB (B - A)
    expired: int      # Jobs marked as expired, in DB but not on career page (A - B)
    error: Optional[str] = None


class SyncResponse(BaseModel):
    """Response for POST /api/jobs/sync."""
    companies: list[CompanySyncResult]
    total_found: int
    total_existing: int
    total_new: int
    total_expired: int


@router.post("/sync", response_model=SyncResponse)
async def sync_all_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sync all jobs: run extractors, compare with DB, mark expired.

    This is a synchronous operation that:
    1. Gets user's enabled companies from settings
    2. Runs extractors to get current job URLs
    3. Compares with existing jobs in DB
    4. Marks jobs NOT in results as EXPIRED
    5. Returns per-company breakdown (found, existing, new, expired)

    NOTE: Does NOT insert new jobs - just identifies them for later extraction.

    Auth: JWT required

    Returns:
        SyncResponse with per-company breakdown and totals

    Example:
        POST /api/jobs/sync
        Authorization: Bearer <jwt_token>

        Response:
        {
            "companies": [
                {"company": "google", "found": 50, "existing": 45, "new": 5, "expired": 2},
                {"company": "amazon", "found": 30, "existing": 28, "new": 2, "expired": 1}
            ],
            "total_found": 80,
            "total_existing": 73,
            "total_new": 7,
            "total_expired": 3
        }
    """
    from models.job import Job, JobStatus

    user_id = current_user["user_id"]

    # Get enabled settings
    settings = get_enabled_settings(db, user_id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No enabled companies configured. Add companies in Settings."
        )

    logger.info(f"Starting sync for user {user_id}")

    try:
        # Run extractors
        extractor_results = await run_extractors_async(settings)

        # Process each company
        company_results: list[CompanySyncResult] = []
        all_found_ids: set[tuple[str, str]] = set()  # (company, external_id)

        for company_name, result in extractor_results.items():
            if result.status != "success":
                company_results.append(CompanySyncResult(
                    company=company_name,
                    found=0,
                    existing=0,
                    new=0,
                    expired=0,
                    error=result.error_message,
                ))
                continue

            # Get external IDs from extractor
            found_external_ids = {job["id"] for job in result.included_jobs}
            found_count = len(found_external_ids)

            # Track all found jobs for expired detection
            for ext_id in found_external_ids:
                all_found_ids.add((company_name, ext_id))

            # Get existing READY jobs for this company from DB
            existing_jobs = db.query(Job).filter(
                Job.user_id == user_id,
                Job.company == company_name,
                Job.status == JobStatus.READY,
            ).all()

            existing_external_ids = {job.external_id for job in existing_jobs}

            # Calculate counts using set operations
            # A = existing_external_ids (READY in DB)
            # B = found_external_ids (on career page)
            # new = B - A (on career page but not in DB)
            # expired = A - B (in DB but not on career page)
            # existing = A ∩ B (in DB AND still on career page)
            new_count = len(found_external_ids - existing_external_ids)
            existing_count = len(existing_external_ids & found_external_ids)

            # Mark expired jobs for this company (in DB but not in extractor results)
            expired_count = 0
            for job in existing_jobs:
                if job.external_id not in found_external_ids:
                    job.status = JobStatus.EXPIRED
                    job.updated_at = datetime.now(timezone.utc)
                    expired_count += 1

            company_results.append(CompanySyncResult(
                company=company_name,
                found=found_count,
                existing=existing_count,
                new=new_count,
                expired=expired_count,
            ))

            logger.info(f"Sync {company_name}: found={found_count}, existing={existing_count}, new={new_count}, expired={expired_count}")

        db.commit()

        # Calculate totals
        total_found = sum(r.found for r in company_results)
        total_existing = sum(r.existing for r in company_results)
        total_new = sum(r.new for r in company_results)
        total_expired = sum(r.expired for r in company_results)

        logger.info(f"Sync complete: found={total_found}, existing={total_existing}, new={total_new}, expired={total_expired}")

        return SyncResponse(
            companies=company_results,
            total_found=total_found,
            total_existing=total_existing,
            total_new=total_new,
            total_expired=total_expired,
        )

    except Exception as e:
        logger.exception(f"Sync failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sync failed. Please try again."
        )


# =============================================================================
# Phase 3B: Re-Extract Jobs
# =============================================================================

class ReExtractRequest(BaseModel):
    """Request body for POST /api/jobs/re-extract."""
    job_id: Optional[int] = None
    company: Optional[str] = None


class ReExtractJobResult(BaseModel):
    """Result for a single job extraction."""
    job_id: int
    title: Optional[str] = None
    success: bool
    description_length: Optional[int] = None
    requirements_length: Optional[int] = None
    error: Optional[str] = None


class ReExtractResponse(BaseModel):
    """Response for POST /api/jobs/re-extract."""
    company: Optional[str] = None
    total_jobs: int
    successful: int
    failed: int
    results: list[ReExtractJobResult]


@router.post("/re-extract", response_model=ReExtractResponse)
async def re_extract_jobs(
    request: ReExtractRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Re-run extraction for job(s) from existing S3 HTML.

    Downloads raw HTML from S3 and re-runs the company's extractor
    to update description and requirements fields. Useful after fixing
    extractors to populate previously empty fields.

    Auth: JWT required

    Request body (one of):
        - job_id: Re-extract a single job
        - company: Re-extract all READY jobs for a company

    Returns:
        ReExtractResponse with batch results

    Examples:
        # Single job
        POST /api/jobs/re-extract
        {"job_id": 123}

        # All jobs for a company
        POST /api/jobs/re-extract
        {"company": "netflix"}

        Response:
        {
            "company": "netflix",
            "total_jobs": 25,
            "successful": 25,
            "failed": 0,
            "results": [
                {"job_id": 1, "title": "SWE", "success": true, "description_length": 3815, "requirements_length": 918}
            ]
        }
    """
    import boto3
    from models.job import Job, JobStatus
    from extractors.registry import get_extractor

    user_id = current_user["user_id"]

    # Validate request - must have exactly one of job_id or company
    if request.job_id is None and request.company is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify either job_id or company"
        )
    if request.job_id is not None and request.company is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specify only one of job_id or company, not both"
        )

    # Single job mode
    if request.job_id is not None:
        job = get_job_by_id(db, request.job_id, user_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {request.job_id} not found"
            )
        jobs = [job]
        company_name = job.company
    else:
        # Company mode
        company_name = request.company.lower()
        jobs = db.query(Job).filter(
            Job.user_id == user_id,
            Job.company == company_name,
            Job.status == JobStatus.READY,
        ).all()

    if not jobs:
        return ReExtractResponse(
            company=company_name,
            total_jobs=0,
            successful=0,
            failed=0,
            results=[],
        )

    # Get extractor for this company (once, outside the loop)
    try:
        extractor = get_extractor(company_name)
    except Exception as e:
        logger.error(f"Failed to get extractor for {company_name}: {e}")
        return ReExtractResponse(
            company=company_name,
            total_jobs=len(jobs),
            successful=0,
            failed=len(jobs),
            results=[
                ReExtractJobResult(
                    job_id=job.id,
                    title=job.title,
                    success=False,
                    error=f"No extractor found for {company_name}"
                )
                for job in jobs
            ],
        )

    # Initialize S3 client once
    s3_client = boto3.client("s3")

    results: list[ReExtractJobResult] = []
    successful = 0
    failed = 0

    for job in jobs:
        # Check if we have raw HTML in S3
        if not job.raw_s3_url:
            results.append(ReExtractJobResult(
                job_id=job.id,
                title=job.title,
                success=False,
                error="No raw HTML found for this job"
            ))
            failed += 1
            continue

        try:
            # Parse S3 URL: s3://bucket/key
            s3_url = job.raw_s3_url
            if s3_url.startswith("s3://"):
                s3_url = s3_url[5:]  # Remove "s3://"
            parts = s3_url.split("/", 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""

            # Download from S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            raw_html = response["Body"].read().decode("utf-8")

            # Extract info from raw HTML
            extracted = extractor.extract_raw_info(raw_html)

            # Update job with extracted content
            job.description = extracted.get("description")
            job.requirements = extracted.get("requirements")
            job.updated_at = datetime.now(timezone.utc)

            results.append(ReExtractJobResult(
                job_id=job.id,
                title=job.title,
                success=True,
                description_length=len(job.description or ""),
                requirements_length=len(job.requirements or ""),
            ))
            successful += 1

        except Exception as e:
            logger.exception(f"Re-extract failed for job {job.id}: {e}")
            results.append(ReExtractJobResult(
                job_id=job.id,
                title=job.title,
                success=False,
                error=f"Re-extraction failed: {str(e)[:100]}"
            ))
            failed += 1

    # Commit all updates at once
    db.commit()

    logger.info(f"Re-extracted {company_name}: {successful}/{len(jobs)} successful")

    return ReExtractResponse(
        company=company_name,
        total_jobs=len(jobs),
        successful=successful,
        failed=failed,
        results=results,
    )
