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

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TitleFilters:
    """
    Title filtering configuration.

    Used by:
    - Extractors for post-API title filtering (as object)
    - DB/API for JSONB storage (via to_dict/from_dict)

    Examples:
        # Include all jobs, exclude senior staff
        config = TitleFilters(include=None, exclude=['senior staff'])

        # Only software engineer titles, exclude interns
        config = TitleFilters(include=['software engineer'], exclude=['intern'])

        # No filtering at all
        config = TitleFilters()

        # From DB/API dict
        config = TitleFilters.from_dict({"include": ["engineer"], "exclude": []})

        # To DB/API dict
        data = config.to_dict()
    """
    include: Optional[List[str]] = None  # None = include all, List = OR logic (match any)
    exclude: List[str] = field(default_factory=list)  # AND logic: reject all

    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dict for API response. Always returns [] instead of None."""
        return {"include": self.include or [], "exclude": self.exclude}

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> "TitleFilters":
        """
        Create from dict (DB/API deserialization).

        Args:
            data: Dict with include/exclude keys, or None

        Returns:
            TitleFilters instance

        Raises:
            ValueError: If data structure is invalid
        """
        if data is None:
            return cls()

        if not isinstance(data, dict):
            raise ValueError("title_filters must be a dict")

        include = data.get("include")
        exclude = data.get("exclude", [])

        # Validate include
        if include is not None:
            if not isinstance(include, list):
                raise ValueError("title_filters.include must be a list or null")
            if not all(isinstance(item, str) for item in include):
                raise ValueError("title_filters.include items must be strings")
            # Normalize empty list to None (empty list = include all)
            if len(include) == 0:
                include = None

        # Validate exclude
        if not isinstance(exclude, list):
            raise ValueError("title_filters.exclude must be a list")
        if not all(isinstance(item, str) for item in exclude):
            raise ValueError("title_filters.exclude items must be strings")

        return cls(include=include, exclude=exclude)
