"""
Title filtering configuration for job extractors

Each extractor uses TitleFilters to specify which job titles to include/exclude.
Company-specific filters (employment type, location, etc.) are hardcoded in the
extractor implementation.

This provides:
- Simple, consistent configuration across all extractors
- IDE autocomplete
- Type checking
"""

from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class TitleFilters:
    """
    Title filtering configuration

    Used by all extractors for post-API title filtering

    Examples:
        # Include all jobs, exclude senior staff
        config = TitleFilters(include=None, exclude=['senior staff'])

        # Only software engineer titles, exclude interns
        config = TitleFilters(include=['software engineer'], exclude=['intern'])

        # No filtering at all
        config = TitleFilters()
    """
    include: Optional[List[str]] = None  # None = include all, List = OR logic (match any)
    exclude: List[str] = field(default_factory=list)  # AND logic: reject all
