import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class NetflixExtractor(BaseExtractorV2):
    COMPANY_NAME = "netflix"
    ICON_URL = "https://assets.nflxext.com/us/ffe/siteui/common/icons/nficon2016.png"
    INPUT_CAREER_URL = "https://explore.jobs.netflix.net/careers?pid=790315922662&Teams=Engineering&domain=netflix.com&sort_by=relevance&triggerGoButton=false"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        import httpx
        from urllib.parse import urlparse, parse_qs

        # Parse filters from the input URL
        parsed = urlparse(self.INPUT_CAREER_URL)
        qs = parse_qs(parsed.query)
        pid = qs.get('pid', ['790315922662'])[0]
        domain = qs.get('domain', ['netflix.com'])[0]
        teams_filter = qs.get('Teams', [None])[0]  # e.g. 'Engineering'

        base_url = f"https://{parsed.netloc}/api/apply/v2/jobs"

        all_positions = []
        start = 0
        total = None

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            while True:
                params = {
                    "domain": domain,
                    "pid": pid,
                    "start": start,
                    "num": 100,
                    "sort_by": "relevance"
                }
                resp = await client.get(base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                positions = data.get('positions', [])
                if total is None:
                    total = data.get('count', 0)
                if not positions:
                    break
                all_positions.extend(positions)
                start += len(positions)
                if len(all_positions) >= total:
                    break

        # Map to contract dicts
        jobs = [
            {
                "id": str(p.get('id', '')),
                "title": p.get('name', ''),
                "location": p.get('location', ''),
                "url": p.get('canonicalPositionUrl', ''),
                "response_data": p
            }
            for p in all_positions
        ]

        # Apply client-side filter for Teams= URL param (maps to department field)
        if teams_filter:
            jobs = [j for j in jobs if j['response_data'].get('department', '').lower() == teams_filter.lower()]

        return jobs
