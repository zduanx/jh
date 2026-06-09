"""
extractors_v2_base — the self-contained base class (the agent's contract).

This is the contract the discovery agent (Phase 8C/8D) codes against. A company
extractor is a subclass that fills in a few PENDING consts/methods:

    class GoogleV2(BaseExtractorV2):
        COMPANY_NAME = Company.GOOGLE
        LOGO_URL     = "..."        # ← discovered by the agent in 8C
        async def _fetch_all_jobs(self) -> list[dict]:   # ← discovered in 8D
            ...

SELF-CONTAINED ON PURPOSE: this package imports nothing from the rest of `backend/`
(no db / config.settings / models) and uses only stdlib + httpx. That's what lets
the WHOLE package live inside the Docker sandbox (8B) with no secrets, no host code.

Pipeline (carried from v1, simplified):
  1. _fetch_all_jobs()            -> raw job dicts                  [ABSTRACT — agent fills]
  2. extract_source_urls_metadata -> filtered jobs + built URLs     [generic, here]
  3. crawl_raw_info(url)          -> raw page text                  [generic, here]
  (job-page PARSING is runtime-LLM in v2 — there is NO per-company extract_raw_info.)
"""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from .enums import Company
from .config import TitleFilters

# Browser-like headers so a plain HTTP request looks like a real browser (most
# career APIs accept this; full JS rendering / Playwright is a later add-on).
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


class BaseExtractorV2(ABC):
    """
    Base class for v2 extractors. Subclasses fill the PENDING members below.

    Class members a concrete extractor defines:
      COMPANY_NAME : Company          (required)
      LOGO_URL     : str | None       (8C — agent-discovered; None = pending)
      URL_PREFIX_JOB : str            (used to build job-detail URLs; may be "")
      _fetch_all_jobs()               (8D — agent-discovered; the hard part)
    """

    # --- PENDING members (filled by concrete subclasses / the agent) ---
    COMPANY_NAME: Company
    LOGO_URL: str | None = None          # 8C target
    URL_PREFIX_JOB: str = ""             # for building job URLs from ids

    def __init__(self, config: TitleFilters | None = None):
        if not hasattr(self.__class__, "COMPANY_NAME"):
            raise NotImplementedError(
                f"{self.__class__.__name__} must define COMPANY_NAME"
            )
        self.config = config or TitleFilters()

    # ------------------------------------------------------------------ #
    # Stage 1 — ABSTRACT: the agent discovers this (8D)
    # ------------------------------------------------------------------ #
    @abstractmethod
    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        """
        Fetch ALL jobs for this company → standardized dicts. THE thing the agent
        discovers (which API/endpoint, headers, pagination).

        Each dict:
          {
            "id": str,              # for building the job URL
            "title": str,           # for title filtering
            "location": str,        # job location
            "response_data": Any,   # raw entry (may carry a prebuilt url/absolute_url)
          }
        Should handle errors internally and return [] on failure.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Stage 2 — generic: filter + build URLs (carried, here)
    # ------------------------------------------------------------------ #
    async def extract_source_urls_metadata(self) -> dict[str, Any]:
        """Run _fetch_all_jobs, apply title filters, build URLs. The list-jobs entry point."""
        all_jobs = await self._fetch_all_jobs()
        total = len(all_jobs)
        if not all_jobs:
            return {"total_count": 0, "filtered_count": 0, "urls_count": 0,
                    "included_jobs": [], "excluded_jobs": []}

        included = self._apply_title_filters(all_jobs)
        included_ids = {j.get("id") for j in included}
        excluded = [j for j in all_jobs if j.get("id") not in included_ids]

        def meta(jobs):
            out = []
            for j in jobs:
                url = self._build_url(j)
                if url:
                    out.append({"id": str(j.get("id", "")), "title": j.get("title", ""),
                                "location": j.get("location", ""), "url": url})
            return out

        included_meta = meta(included)
        return {
            "total_count": total,
            "filtered_count": len(excluded),
            "urls_count": len(included_meta),
            "included_jobs": included_meta,
            "excluded_jobs": meta(excluded),
        }

    # ------------------------------------------------------------------ #
    # Stage 3 — generic: crawl raw page text (carried). Parsing is runtime-LLM.
    # ------------------------------------------------------------------ #
    async def crawl_raw_info(self, job_url: str) -> str:
        """Fetch the raw text (HTML/JSON) of a job page. Override only if special handling needed."""
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0,
                                     follow_redirects=True) as client:
            resp = await client.get(job_url)
            resp.raise_for_status()
            return resp.text

    # ------------------------------------------------------------------ #
    # Helpers (self-contained)
    # ------------------------------------------------------------------ #
    def _apply_title_filters(self, jobs: list[dict]) -> list[dict]:
        inc = self.config.include
        exc = self.config.exclude

        def keep(title: str) -> bool:
            t = (title or "").lower()
            if exc and any(x.lower() in t for x in exc):
                return False
            if inc is not None:
                return any(x.lower() in t for x in inc)
            return True

        return [j for j in jobs if keep(j.get("title", ""))]

    def _build_url(self, job: dict) -> str:
        """Build a job-detail URL: prefer a prebuilt url in response_data, else prefix+id."""
        rd = job.get("response_data", {})
        if isinstance(rd, dict):
            if rd.get("absolute_url"):
                return rd["absolute_url"]
            if rd.get("url"):
                return rd["url"]
            if rd.get("job_path"):
                return f"{self.URL_PREFIX_JOB}{rd['job_path']}"
        job_id = job.get("id")
        if job_id and self.URL_PREFIX_JOB:
            return f"{self.URL_PREFIX_JOB}/{job_id}"
        return str(job_id or "")

    # Convenience: a plain browser-like GET (agent trial code can use this pattern).
    @staticmethod
    async def fetch(url: str, *, timeout: float = 15.0, headers: dict | None = None) -> httpx.Response:
        async with httpx.AsyncClient(headers=headers or DEFAULT_HEADERS, timeout=timeout,
                                     follow_redirects=True) as client:
            return await client.get(url)
