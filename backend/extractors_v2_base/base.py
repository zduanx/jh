"""
extractors_v2_base — the self-contained base class (the agent's contract).

This is the contract the discovery agent (Phase 8C/8D) codes against. A company
extractor is a subclass that fills in a few PENDING consts/methods:

    class GoogleV2(BaseExtractorV2):
        COMPANY_NAME = "google"
        ICON_URL     = "..."        # ← discovered by the agent in 8C
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
      COMPANY_NAME : str              (required — the company slug, e.g. "anthropic")
      ICON_URL     : str | None       (8C — agent-discovered; None = pending)
      INPUT_CAREER_URL : str | None   (provenance — the careers URL used to generate this)
      _fetch_all_jobs()               (8D — agent-discovered; the hard part; each job
                                       dict carries its full `url`)

    Note: COMPANY_NAME is a plain string (NOT an enum) — companies are an open,
    growing set (the discovery agent adds new ones). The registry is the source of
    truth for "what companies exist", not a hardcoded enum.
    """

    # --- PENDING members (filled by concrete subclasses / the agent) ---
    COMPANY_NAME: str
    ICON_URL: str | None = None          # 8C target
    INPUT_CAREER_URL: str | None = None  # provenance: the URL the agent was given

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
            "id": str,              # the job's id
            "title": str,           # for title filtering
            "location": str,        # job location
            "url": str,             # the FULL job-detail (JD landing) URL — REQUIRED.
                                    #   the agent extracts this per-ATS; it is NOT built
                                    #   from a prefix (URLs vary: id-based, slug-based, ...)
            "response_data": Any,   # the raw entry (for debugging / future fields)
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
        """The job-detail URL. The agent now puts the full URL in the explicit `url`
        field; fall back to common locations in response_data for older extractors."""
        if job.get("url"):
            return job["url"]
        rd = job.get("response_data", {})
        if isinstance(rd, dict):
            for k in ("url", "absolute_url", "canonicalPositionUrl", "jobUrl"):
                if rd.get(k):
                    return rd[k]
        return str(job.get("id") or "")

    # Convenience: a plain browser-like GET (agent trial code can use this pattern).
    @staticmethod
    async def fetch(url: str, *, timeout: float = 15.0, headers: dict | None = None) -> httpx.Response:
        async with httpx.AsyncClient(headers=headers or DEFAULT_HEADERS, timeout=timeout,
                                     follow_redirects=True) as client:
            return await client.get(url)
