import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class HrtExtractor(BaseExtractorV2):
    COMPANY_NAME = "hrt"
    ICON_URL = "https://www.hudsonrivertrading.com/wp-content/uploads/2023/11/cropped-HRT-Avatar-Profile-Photo-Favicon-180x180.png"
    INPUT_CAREER_URL = "https://www.hudsonrivertrading.com/careers/?job-type=full-time-experienced%2Cparent_full-time-experienced%2C&job-category=software-engineeringpython%2Cparent_software-engineeringc%2C&locations=new-york%2C"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        from urllib.parse import urlparse, parse_qs

        # Parse filter params from the input URL
        parsed = urlparse(self.INPUT_CAREER_URL)
        params = parse_qs(parsed.query)

        raw_job_types = [s.strip().rstrip(',') for s in ','.join(params.get('job-type', [])).split(',') if s.strip().rstrip(',')]
        raw_job_cats = [s.strip().rstrip(',') for s in ','.join(params.get('job-category', [])).split(',') if s.strip().rstrip(',')]
        raw_locations = [s.strip().rstrip(',') for s in ','.join(params.get('locations', [])).split(',') if s.strip().rstrip(',')]

        def slug_to_job_type(slug):
            slug = slug.lower().replace('parent_', '')
            mapping = {
                'full-time-experienced': 'Full-Time: Experienced',
                'full-time-new-grad': 'Full-Time: New Grad',
                'temporary': 'Temporary',
            }
            return mapping.get(slug)

        def slug_to_job_category(slug):
            slug = slug.lower().replace('parent_', '')
            mapping = {
                'software-engineeringpython': 'Software Engineering:Python',
                'software-engineeringc': 'Software Engineering:C++',
                'finance': 'Finance',
                'hardware-engineering': 'Hardware Engineering',
                'information-security': 'Information Security',
                'legal-compliance': 'Legal & Compliance',
                'people-operations': 'People Operations',
                'risk': 'Risk',
                'strategy-development': 'Strategy Development',
                'systems-and-networking': 'Systems and Networking',
                'trade-operations': 'Trade Operations',
                'business-development': 'Business Development',
            }
            return mapping.get(slug)

        filter_job_types = set(filter(None, (slug_to_job_type(s) for s in raw_job_types)))
        filter_job_cats = set(filter(None, (slug_to_job_category(s) for s in raw_job_cats)))
        filter_locations = [s.replace('-', ' ').lower() for s in raw_locations]

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get('https://boards-api.greenhouse.io/v1/boards/wehrtyou/jobs?content=true')
            resp.raise_for_status()
            data = resp.json()

        jobs = data.get('jobs', [])

        def get_meta_values(job, field_name):
            for meta in job.get('metadata', []):
                if meta['name'] == field_name and meta['value']:
                    return meta['value']
            return []

        def matches_location(job, loc_filters):
            if not loc_filters:
                return True
            loc = job['location']['name'].lower()
            return any(lf in loc for lf in loc_filters)

        results = []
        for job in jobs:
            if filter_job_types:
                jt_vals = get_meta_values(job, 'Job Type')
                if not any(v in filter_job_types for v in jt_vals):
                    continue
            if filter_job_cats:
                jc_vals = get_meta_values(job, 'Job Category')
                if not any(v in filter_job_cats for v in jc_vals):
                    continue
            if not matches_location(job, filter_locations):
                continue
            results.append({
                'id': str(job['id']),
                'title': job['title'],
                'location': job['location']['name'],
                'url': job['absolute_url'],
                'response_data': job,
            })

        return results
