import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class RobloxExtractor(BaseExtractorV2):
    COMPANY_NAME = "roblox"
    ICON_URL = "https://images.rbxcdn.com/905bd722ee0a6ceda3caacde54c0b081.png"
    INPUT_CAREER_URL = "https://careers.roblox.com/jobs?disciplines=engineering&type=full-time&loc=headquarters"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        from urllib.parse import urlparse, parse_qs

        # Parse filters from INPUT_CAREER_URL
        parsed = urlparse(self.INPUT_CAREER_URL)
        params = parse_qs(parsed.query)
        disciplines = [d.lower() for d in params.get('disciplines', [])]
        job_type = [t.lower() for t in params.get('type', [])]
        loc = [l.lower() for l in params.get('loc', [])]

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get('https://boards-api.greenhouse.io/v1/boards/roblox/jobs?content=true')
            data = r.json()
            jobs = data.get('jobs', [])

        # Filter: disciplines=engineering -> departments containing 'engineering' or 'machine learning'
        engineering_keywords = ['engineering', 'machine learning']

        def is_engineering(job):
            if not disciplines:
                return True
            if 'engineering' in disciplines:
                for d in job.get('departments', []):
                    name = d.get('name', '').lower()
                    if any(kw in name for kw in engineering_keywords):
                        return True
                return False
            return True

        # Filter: type=full-time -> Employment Type metadata = 'Salaried Employee'
        def is_full_time(job):
            if not job_type:
                return True
            if 'full-time' in job_type:
                for m in job.get('metadata', []):
                    if m['name'] == 'Employment Type' and m['value'] == 'Salaried Employee':
                        return True
                return False
            return True

        # Filter: loc=headquarters -> offices containing 'san mateo'
        def is_hq(job):
            if not loc:
                return True
            if 'headquarters' in loc:
                for o in job.get('offices', []):
                    if 'san mateo' in o.get('name', '').lower():
                        return True
                return False
            return True

        filtered = [j for j in jobs if is_engineering(j) and is_full_time(j) and is_hq(j)]

        result = []
        for j in filtered:
            result.append({
                'id': str(j['id']),
                'title': j.get('title', ''),
                'location': j.get('location', {}).get('name', ''),
                'url': j.get('absolute_url', ''),
                'response_data': j
            })
        return result
