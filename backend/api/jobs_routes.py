"""
API routes for job listing and details (Phase 3A).

Endpoints:
- GET  /api/jobs           List all jobs grouped by company
- GET  /api/jobs/{job_id}  Get full job details

Interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from db.session import get_db
from db.jobs_service import get_jobs_grouped_by_company, get_job_by_id

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
