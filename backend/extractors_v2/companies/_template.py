"""
Template for a v2 company extractor — the shape the agent produces.

The agent (8C/8D) creates `companies/{company}.py` from this shape and fills the
PENDING members. A class is "done" when LOGO_URL is set and _fetch_all_jobs works.
"""

from typing import Any

from ..base import BaseExtractorV2
from ..enums import Company


class TemplateExtractor(BaseExtractorV2):
    COMPANY_NAME = Company.GOOGLE          # ← set to the real company

    # 8C — agent fills this (the company's logo image URL):
    LOGO_URL: str | None = None            # PENDING

    # Used to build job-detail URLs from ids (8D may set this):
    URL_PREFIX_JOB = ""                     # PENDING (if needed)

    # 8D — agent discovers + fills this (the hard part: how to list ALL jobs):
    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        # PENDING — the agent writes the real fetch logic here.
        # Must return: [{"id","title","location","response_data"}, ...]
        raise NotImplementedError("agent has not discovered _fetch_all_jobs yet")
