import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class OpenaiExtractor(BaseExtractorV2):
    COMPANY_NAME = "openai"
    ICON_URL = "https://openai.com/favicon.ico"
    INPUT_CAREER_URL = "https://openai.com/careers/search/?q=software+engineer"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        from urllib.parse import urlparse, parse_qs

        # Parse the search query from the input URL
        parsed = urlparse(self.INPUT_CAREER_URL)
        params = parse_qs(parsed.query)
        query = params.get("q", [None])[0]

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.ashbyhq.com/posting-api/job-board/openai",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get("jobs", [])

        # Map all jobs to contract format
        mapped = []
        for j in jobs:
            mapped.append({
                "id": str(j.get("id", "")),
                "title": j.get("title", ""),
                "location": j.get("location", ""),
                "url": j.get("jobUrl", ""),
                "response_data": j,
            })

        # Apply client-side filter for ?q= search query (title substring match)
        if query:
            q_lower = query.lower()
            mapped = [j for j in mapped if q_lower in j["title"].lower()]

        return mapped
