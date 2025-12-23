"""
API routes for ingestion workflow.

Endpoints:
- GET  /api/ingestion/companies       List available companies from extractor registry
- GET  /api/ingestion/settings        Get user's configured company settings
- POST /api/ingestion/settings        Batch create/update/delete company settings
- POST /api/ingestion/dry-run         Extract job URLs for enabled companies (preview)

Interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Running locally:
    cd backend
    uvicorn main:app --reload
"""

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from typing import Optional, Literal, Any
from datetime import datetime
from sqlalchemy.orm import Session
import httpx
from auth.dependencies import get_current_user
from db.session import get_db
from db.company_settings_service import (
    get_user_settings,
    get_enabled_settings,
    batch_operations,
)
from extractors.registry import list_companies, get_extractor
from extractors.config import TitleFilters

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


def _map_extractor_error(e: Exception) -> str:
    """Map exception to user-friendly error message."""
    if isinstance(e, httpx.TimeoutException):
        return "Request timed out - career site may be slow"
    elif isinstance(e, httpx.ConnectError):
        return "Could not connect to career site"
    elif isinstance(e, httpx.HTTPStatusError):
        status_code = e.response.status_code
        if status_code == 403:
            return "Access denied - site may be blocking requests"
        elif status_code == 429:
            return "Rate limited - try again later"
        elif status_code >= 500:
            return "Career site is temporarily unavailable"
        else:
            return f"HTTP error: {status_code}"
    elif isinstance(e, (KeyError, TypeError, ValueError)):
        return "Unexpected response format - API may have changed"
    else:
        # Generic fallback - don't expose internal details
        return f"Extraction failed: {type(e).__name__}"


async def _run_extractor(company_name: str, title_filters: dict) -> dict:
    """
    Run extractor for a single company.

    Returns dict with status and results or error.
    """
    try:
        config = TitleFilters.from_dict(title_filters)
        extractor = get_extractor(company_name, config=config)
        result = await extractor.extract_source_urls_metadata()

        return {
            "status": "success",
            "total_count": result["total_count"],
            "filtered_count": result["filtered_count"],
            "urls_count": result["urls_count"],
            "included_jobs": result["included_jobs"],
            "excluded_jobs": result["excluded_jobs"],
            "error_message": None,
        }
    except Exception as e:
        logger.exception(f"Extractor failed for {company_name}: {e}")
        return {
            "status": "error",
            "total_count": 0,
            "filtered_count": 0,
            "urls_count": 0,
            "included_jobs": [],
            "excluded_jobs": [],
            "error_message": _map_extractor_error(e),
        }


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

    # Run extractors in parallel using asyncio.gather
    tasks = [
        _run_extractor(setting.company_name, setting.title_filters)
        for setting in settings
    ]
    company_names = [setting.company_name for setting in settings]

    # Execute all tasks concurrently
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    # Build results dict
    results: dict[str, Any] = {}
    for company_name, result in zip(company_names, results_list):
        if isinstance(result, Exception):
            # Should not happen since _run_extractor catches exceptions
            logger.exception(f"Unexpected error for {company_name}: {result}")
            results[company_name] = {
                "status": "error",
                "total_count": 0,
                "filtered_count": 0,
                "urls_count": 0,
                "included_jobs": [],
                "excluded_jobs": [],
                "error_message": "Unexpected error occurred",
            }
        else:
            results[company_name] = result

    return results
