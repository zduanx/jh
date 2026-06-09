"""
Template for a GENERATED v2 company extractor — the shape the agent produces.

IMPORTANT: generated extractors live in `extractors_v2/{company}.py` (the agent's
OUTPUT, what production imports), NOT here. This file in `extractors_v2_base/` is
just the reference shape. Generated code imports the framework from
`extractors_v2_base` (this package, which is baked into the Docker sandbox image).

The agent fills the PENDING members:
  - ICON_URL        (8C)
  - _fetch_all_jobs (8D)
A class is "done" when ICON_URL is set and _fetch_all_jobs works.
"""

from typing import Any

from extractors_v2_base import BaseExtractorV2


class TemplateExtractor(BaseExtractorV2):
    COMPANY_NAME = "google"                 # ← set to the real company slug (a string)

    # 8C — agent fills this (the company's icon image URL):
    ICON_URL: str | None = None            # PENDING

    # Used to build job-detail URLs from ids (8D may set this):
    URL_PREFIX_JOB = ""                     # PENDING (if needed)

    # 8D — agent discovers + fills this (the hard part: how to list ALL jobs):
    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        # PENDING — the agent writes the real fetch logic here.
        # Must return: [{"id","title","location","response_data"}, ...]
        raise NotImplementedError("agent has not discovered _fetch_all_jobs yet")
