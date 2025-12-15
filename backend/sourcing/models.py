"""
Pydantic models for job URL sourcing API
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class SourceUrlsRequest(BaseModel):
    """Request model for source URLs endpoint"""

    dry_run: bool = Field(
        default=True,
        description="If true, return results. If false, send to SQS queue."
    )


class JobMetadata(BaseModel):
    """Metadata for a single job"""

    id: str = Field(description="Job ID")
    title: str = Field(description="Job title")
    location: str = Field(description="Job location")
    url: str = Field(description="Job URL")


class CompanyResult(BaseModel):
    """Result from a single company extraction"""

    company: str = Field(description="Company name (lowercase)")
    total_count: int = Field(description="Total jobs from API")
    filtered_count: int = Field(description="Jobs filtered OUT (rejected)")
    urls_count: int = Field(description="Jobs included (passed filter)")
    included_jobs: List[JobMetadata] = Field(description="Jobs that passed filter")
    excluded_jobs: List[JobMetadata] = Field(description="Jobs that were filtered out")
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")


class SummaryStats(BaseModel):
    """Summary statistics across all companies"""

    total_jobs: int = Field(description="Total jobs across all companies")
    total_filtered_jobs: int = Field(description="Total jobs filtered out")
    total_included_jobs: int = Field(description="Total jobs included")
    total_companies: int = Field(description="Number of companies processed")


class SourceUrlsResponse(BaseModel):
    """Response model for source URLs endpoint"""

    summary: SummaryStats = Field(description="Summary statistics")
    results: List[CompanyResult] = Field(description="Results from each company")
    dry_run: bool = Field(description="Whether this was a dry run")
    message: Optional[str] = Field(default=None, description="Additional info message")
