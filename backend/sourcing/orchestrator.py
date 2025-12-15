"""
Async orchestrator for parallel job URL extraction across multiple companies
"""

import asyncio
import sys
import os
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from src.extractors import TitleFilters
from src.extractors.registry import get_extractor, Company
from .models import CompanyResult


async def extract_company_urls(company: Company, config: TitleFilters) -> CompanyResult:
    """
    Extract URLs for a single company (async wrapper for sync extractor)

    Args:
        company: Company enum value
        config: TitleFilters configuration for this company

    Returns:
        CompanyResult with extraction data or error
    """
    loop = asyncio.get_event_loop()

    def _run_extraction():
        """Run extraction in thread pool (extractors are synchronous)"""
        try:
            extractor = get_extractor(company, config)
            result = extractor.extract_source_urls_metadata()
            return CompanyResult(
                company=company.value,
                total_count=result['total_count'],
                filtered_count=result['filtered_count'],
                urls_count=result['urls_count'],
                included_jobs=result['included_jobs'],
                excluded_jobs=result['excluded_jobs'],
                error=None
            )
        except Exception as e:
            # Return error result instead of raising
            return CompanyResult(
                company=company.value,
                total_count=0,
                filtered_count=0,
                urls_count=0,
                included_jobs=[],
                excluded_jobs=[],
                error=str(e)
            )

    # Run blocking extraction in thread pool
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, _run_extraction)

    return result


async def extract_all_companies(settings: Dict[Company, TitleFilters]) -> List[CompanyResult]:
    """
    Extract URLs from all companies in parallel

    Args:
        settings: Dict mapping Company enum to their TitleFilters

    Returns:
        List of CompanyResult objects (one per company)

    Example:
        >>> settings = {
        ...     Company.GOOGLE: TitleFilters(include=None, exclude=['senior staff']),
        ...     Company.AMAZON: TitleFilters(include=None, exclude=[])
        ... }
        >>> results = await extract_all_companies(settings)
        >>> print(f"Total companies: {len(results)}")
        Total companies: 2
    """
    # Create async tasks for all companies
    tasks = [
        extract_company_urls(company, config)
        for company, config in settings.items()
    ]

    # Run all extractions in parallel
    results = await asyncio.gather(*tasks)

    return list(results)


def extract_all_companies_sync(settings: Dict[Company, TitleFilters]) -> List[CompanyResult]:
    """
    Synchronous wrapper for extract_all_companies (for non-async contexts)

    Args:
        settings: Dict mapping Company enum to their TitleFilters

    Returns:
        List of CompanyResult objects

    Example:
        >>> settings = get_user_sourcing_settings()
        >>> results = extract_all_companies_sync(settings)
        >>> print(f"Extracted {len(results)} companies")
    """
    return asyncio.run(extract_all_companies(settings))
