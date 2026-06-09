"""
extractors_v2 — self-contained extractor framework for the Phase 8 discovery agent.

Imports nothing from the rest of `backend/` (stdlib + httpx only), so the whole
package can run inside the Docker sandbox. See docs/logs/PHASE_8A_SUMMARY.md.
"""

from .base import BaseExtractorV2
from .enums import Company
from .config import TitleFilters

__all__ = ["BaseExtractorV2", "Company", "TitleFilters"]
