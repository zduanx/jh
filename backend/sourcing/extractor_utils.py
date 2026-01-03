"""
Utility functions for running extractors.

Provides both async and sync interfaces for running extractors against
company career pages.
"""

import asyncio
import logging
from typing import Any
from dataclasses import dataclass

from extractors.registry import get_extractor
from extractors.config import TitleFilters

logger = logging.getLogger(__name__)


@dataclass
class ExtractorResult:
    """Result from running an extractor for a single company."""
    company: str
    status: str  # "success" or "error"
    total_count: int
    filtered_count: int
    urls_count: int
    included_jobs: list[dict]  # [{id, title, location, url}, ...]
    excluded_jobs: list[dict]
    error_message: str | None


def _map_extractor_error(e: Exception) -> str:
    """Map extractor exceptions to user-friendly error messages."""
    import httpx

    if isinstance(e, httpx.TimeoutException):
        return "Request timed out - career site may be slow"
    elif isinstance(e, httpx.HTTPStatusError):
        status_code = e.response.status_code
        if status_code == 403:
            return "Access denied - site may have rate limiting"
        elif status_code == 404:
            return "Career page not found - URL may have changed"
        elif status_code >= 500:
            return "Career site server error - try again later"
        else:
            return f"HTTP error: {status_code}"
    elif isinstance(e, (KeyError, TypeError, ValueError)):
        return "Unexpected response format - API may have changed"
    else:
        return f"Extraction failed: {type(e).__name__}"


async def run_extractor_async(company_name: str, title_filters: dict) -> ExtractorResult:
    """
    Run extractor for a single company (async).

    Args:
        company_name: Company identifier (e.g., "google", "amazon")
        title_filters: Title filter configuration dict

    Returns:
        ExtractorResult with status and job data
    """
    try:
        config = TitleFilters.from_dict(title_filters)
        extractor = get_extractor(company_name, config=config)
        result = await extractor.extract_source_urls_metadata()

        return ExtractorResult(
            company=company_name,
            status="success",
            total_count=result["total_count"],
            filtered_count=result["filtered_count"],
            urls_count=result["urls_count"],
            included_jobs=result["included_jobs"],
            excluded_jobs=result["excluded_jobs"],
            error_message=None,
        )
    except Exception as e:
        logger.exception(f"Extractor failed for {company_name}: {e}")
        return ExtractorResult(
            company=company_name,
            status="error",
            total_count=0,
            filtered_count=0,
            urls_count=0,
            included_jobs=[],
            excluded_jobs=[],
            error_message=_map_extractor_error(e),
        )


async def run_extractors_async(
    settings: list,
) -> dict[str, ExtractorResult]:
    """
    Run extractors for multiple companies in parallel (async).

    Args:
        settings: List of company settings with company_name and title_filters

    Returns:
        Dict mapping company_name to ExtractorResult
    """
    tasks = [
        run_extractor_async(setting.company_name, setting.title_filters)
        for setting in settings
    ]

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[str, ExtractorResult] = {}
    for setting, result in zip(settings, results_list):
        if isinstance(result, Exception):
            logger.exception(f"Unexpected error for {setting.company_name}: {result}")
            results[setting.company_name] = ExtractorResult(
                company=setting.company_name,
                status="error",
                total_count=0,
                filtered_count=0,
                urls_count=0,
                included_jobs=[],
                excluded_jobs=[],
                error_message="Unexpected error occurred",
            )
        else:
            results[setting.company_name] = result

    return results


def run_extractors_sync(settings: list) -> dict[str, ExtractorResult]:
    """
    Run extractors for multiple companies in parallel (sync wrapper).

    This is for use in Lambda workers where we don't have an async context.

    Args:
        settings: List of company settings with company_name and title_filters

    Returns:
        Dict mapping company_name to ExtractorResult
    """
    return asyncio.run(run_extractors_async(settings))
