import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class AnthropicExtractor(BaseExtractorV2):
    COMPANY_NAME = "anthropic"
    ICON_URL = "https://cdn.prod.website-files.com/67ce28cfec624e2b733f8a52/67d31dd7aa394792257596c5_webclip.png"
    INPUT_CAREER_URL = "https://www.anthropic.com/careers/jobs"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        import httpx
        from urllib.parse import urlparse, parse_qs

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                'https://boards-api.greenhouse.io/v1/boards/anthropic/jobs',
                params={'content': 'true'}
            )
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get('jobs', [])

        # Map all jobs to contract dicts
        mapped = []
        for job in jobs:
            mapped.append({
                'id': str(job['id']),
                'title': job['title'],
                'location': job.get('location', {}).get('name', ''),
                'url': job['absolute_url'],
                'response_data': job,
            })

        # Apply client-side filters from INPUT_CAREER_URL query params
        parsed = urlparse(self.INPUT_CAREER_URL)
        params = parse_qs(parsed.query)

        # Search/query filter (title substring)
        query = params.get('q', params.get('search', [None]))[0]
        if query:
            query_lower = query.lower()
            mapped = [j for j in mapped if query_lower in j['title'].lower()]

        # Department/team filter
        dept_filter = params.get('departments', params.get('Teams', params.get('job-category', [None])))[0]
        if dept_filter:
            dept_lower = dept_filter.lower()
            mapped = [
                j for j in mapped
                if any(dept_lower in d.get('name', '').lower()
                       for d in j['response_data'].get('departments', []))
            ]

        # Location filter
        loc_filter = params.get('loc', params.get('locations', [None]))[0]
        if loc_filter:
            loc_lower = loc_filter.lower()
            mapped = [j for j in mapped if loc_lower in j['location'].lower()]

        return mapped
