"""
API routes for job URL sourcing
"""

from fastapi import APIRouter, Depends
from typing import List
from auth.dependencies import get_current_user
from auth.models import UserInfo
from .models import SourceUrlsRequest, SourceUrlsResponse, CompanyResult, SummaryStats
from .config import get_user_sourcing_settings
from .orchestrator import extract_all_companies
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from src.extractors.registry import Company

router = APIRouter()


@router.post("/source-urls", response_model=SourceUrlsResponse)
async def source_urls(
    request: SourceUrlsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Extract job URLs from company career pages

    This endpoint:
    1. Retrieves user's sourcing settings from database (currently hardcoded)
    2. Runs parallel extraction across all configured companies
    3. If dry_run=true: Returns results to user
    4. If dry_run=false: Sends results to SQS queue (future implementation)

    Requires valid JWT token in Authorization header:
        Authorization: Bearer <jwt_token>

    Args:
        request: SourceUrlsRequest with dry_run flag
        current_user: Current user from JWT (injected by dependency)

    Returns:
        SourceUrlsResponse with extraction results

    Example:
        POST /api/sourcing/source-urls
        {
            "dry_run": true
        }

        Response:
        {
            "results": [
                {
                    "company": "google",
                    "total_count": 150,
                    "filtered_count": 145,
                    "urls_count": 145,
                    "urls": ["https://...", ...],
                    "error": null
                },
                ...
            ],
            "total_jobs": 287,
            "dry_run": true,
            "message": "Dry run completed successfully"
        }
    """
    # Get user's email from JWT
    user_email = current_user.get('email')

    # Get user's sourcing settings (currently hardcoded, will query DB in future)
    # TODO: Pass user_email to get_user_sourcing_settings when DB is implemented
    settings = get_user_sourcing_settings()

    # Run parallel extraction across all companies
    results = await extract_all_companies(settings)

    # Calculate summary statistics
    total_jobs = sum(r.total_count for r in results)
    total_filtered_jobs = sum(r.filtered_count for r in results)
    total_included_jobs = sum(r.urls_count for r in results)

    summary = SummaryStats(
        total_jobs=total_jobs,
        total_filtered_jobs=total_filtered_jobs,
        total_included_jobs=total_included_jobs,
        total_companies=len(results)
    )

    if request.dry_run:
        # Dry run: return results to user
        return SourceUrlsResponse(
            summary=summary,
            results=results,
            dry_run=True,
            message="Dry run completed successfully"
        )
    else:
        # Production mode: send to SQS queue
        # TODO: Implement SQS sending
        # await send_to_sqs_queue(results)

        return SourceUrlsResponse(
            summary=summary,
            results=results,
            dry_run=False,
            message=f"Sent {total_included_jobs} jobs to processing queue (SQS not yet implemented)"
        )


@router.get("/companies", response_model=List[str])
async def get_available_companies():
    """
    Get list of all available companies for job URL sourcing

    This endpoint returns all companies that have extractors implemented.
    No authentication required as this is public information.

    Returns:
        List of company names (lowercase strings)

    Example:
        GET /api/sourcing/companies

        Response:
        ["google", "amazon", "anthropic", "tiktok", "roblox", "netflix"]
    """
    return [company.value for company in Company]
