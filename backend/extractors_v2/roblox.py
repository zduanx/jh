import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class RobloxExtractor(BaseExtractorV2):
    COMPANY_NAME = "roblox"
    ICON_URL = "https://careers.roblox.com/icons/apple-icon-180x180.png"
    INPUT_CAREER_URL = "https://careers.roblox.com/jobs?disciplines=engineering&type=full-time&loc=headquarters"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        from urllib.parse import urlparse, parse_qs

        # Engineering department id and its children
        ENGINEERING_DEPT_IDS = {66439, 90905, 90906, 271725, 90907, 90063, 90909, 90908}

        # Parse filters from INPUT_CAREER_URL
        parsed = urlparse(self.INPUT_CAREER_URL)
        params = parse_qs(parsed.query)
        disciplines = [d.lower() for d in params.get('disciplines', [])]
        job_type = [t.lower() for t in params.get('type', [])]
        loc = [l.lower() for l in params.get('loc', [])]

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get('https://boards-api.greenhouse.io/v1/boards/roblox/jobs?content=true')
            resp.raise_for_status()
            data = resp.json()

        jobs = data.get('jobs', [])
        results = []

        for job in jobs:
            job_dept_ids = {d['id'] for d in job.get('departments', [])}

            # Filter: disciplines=engineering
            if disciplines:
                if 'engineering' in disciplines:
                    if not (job_dept_ids & ENGINEERING_DEPT_IDS):
                        continue

            # Filter: type=full-time -> Employment Type = Salaried Employee
            if job_type:
                if 'full-time' in job_type:
                    is_fulltime = any(
                        m['name'] == 'Employment Type' and m['value'] == 'Salaried Employee'
                        for m in job.get('metadata', [])
                    )
                    if not is_fulltime:
                        continue

            # Filter: loc=headquarters -> San Mateo, CA
            if loc:
                if 'headquarters' in loc:
                    if not any(o['name'] == 'San Mateo, CA' for o in job.get('offices', [])):
                        continue

            results.append({
                'id': str(job['id']),
                'title': job['title'],
                'location': job['location']['name'],
                'url': job['absolute_url'],
                'response_data': job
            })

        return results
