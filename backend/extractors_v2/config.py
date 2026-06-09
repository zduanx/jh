"""
Title filtering config for extractors_v2.

Carried from v1 — already dependency-free (stdlib dataclasses only), so it works
unchanged inside the Docker sandbox.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TitleFilters:
    """
    Which job titles to include/exclude after fetching.

      include: None = include all; a list = OR logic (keep if title matches ANY)
      exclude: AND logic (drop if title matches ANY)

    Examples:
        TitleFilters()                                   # no filtering
        TitleFilters(exclude=["intern"])                 # drop interns
        TitleFilters(include=["software engineer"])      # only SWE titles
    """

    include: Optional[List[str]] = None
    exclude: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[str]]:
        return {"include": self.include or [], "exclude": self.exclude}

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> "TitleFilters":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("title_filters must be a dict")
        include = data.get("include")
        exclude = data.get("exclude", [])
        if include is not None:
            if not isinstance(include, list) or not all(isinstance(x, str) for x in include):
                raise ValueError("title_filters.include must be a list of strings or null")
            if len(include) == 0:
                include = None
        if not isinstance(exclude, list) or not all(isinstance(x, str) for x in exclude):
            raise ValueError("title_filters.exclude must be a list of strings")
        return cls(include=include, exclude=exclude)
