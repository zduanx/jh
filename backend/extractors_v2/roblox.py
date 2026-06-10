import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class RobloxExtractor(BaseExtractorV2):
    COMPANY_NAME = "roblox"
    ICON_URL = "https://images.rbxcdn.com/905bd722ee0a6ceda3caacde54c0b081.png"
    INPUT_CAREER_URL = "https://careers.roblox.com/jobs?disciplines=engineering&type=full-time&loc=headquarters"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        import httpx
        from urllib.parse import urlparse, parse_qs

        # Parse filters from the input URL
        parsed = urlparse(self.INPUT_CAREER_URL)
        params = parse_qs(parsed.query)
        disciplines = [d.lower() for d in params.get('disciplines', [])]
        job_type = params.get('type', [None])[0]
        loc = params.get('loc', [None])[0]

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get('https://boards-api.greenhouse.io/v1/boards/roblox/jobs?content=true')
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get('jobs', [])

        def get_meta(job, name):
            for m in job.get('metadata', []):
                if m['name'] == name:
                    return m.get('value')
            return None

        results = []
        for job in jobs:
            dept_names = [d['name'].lower() for d in job.get('departments', [])]
            office_names = [o['name'] for o in job.get('offices', [])]
            time_type = get_meta(job, 'Time Type')

            # Filter by disciplines (e.g. 'engineering' -> department name contains 'engineering')
            if disciplines:
                if not any(disc in dept for disc in disciplines for dept in dept_names):
                    continue

            # Filter by type (e.g. 'full-time' -> Time Type = 'Full Time')
            if job_type:
                normalized_type = job_type.replace('-', ' ').lower()
                if not time_type or time_type.lower() != normalized_type:
                    continue

            # Filter by loc (e.g. 'headquarters' -> San Mateo, CA)
            if loc:
                loc_lower = loc.lower()
                if loc_lower == 'headquarters':
                    if not any('san mateo' in o.lower() for o in office_names):
                        continue
                else:
                    if not any(loc_lower in o.lower() for o in office_names):
                        continue

            results.append({
                'id': str(job['id']),
                'title': job['title'],
                'location': job['location']['name'],
                'url': job['absolute_url'],
                'response_data': job
            })

        return results
