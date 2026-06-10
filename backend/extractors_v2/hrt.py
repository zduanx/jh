import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class HrtExtractor(BaseExtractorV2):
    COMPANY_NAME = "hrt"
    ICON_URL = "https://www.hudsonrivertrading.com/wp-content/uploads/2023/11/cropped-HRT-Avatar-Profile-Photo-Favicon-180x180.png"
    INPUT_CAREER_URL = "https://www.hudsonrivertrading.com/careers/?job-type=full-time-experienced%2Cparent_full-time-experienced%2C&job-category=software-engineeringpython%2Cparent_software-engineeringc%2C&locations=new-york%2C"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        import re
        import html
        import json
        from urllib.parse import urlparse, parse_qs

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # Step 1: Fetch careers page to get nonce and setting
            resp = await client.get('https://www.hudsonrivertrading.com/careers/')
            text = resp.text

            # Extract nonce from inline hrtJobsAjax JS variable
            nonce_match = re.search(r'hrtJobsAjax\s*=\s*(\{[^}]+\})', text)
            nonce = None
            if nonce_match:
                ajax_data = json.loads(nonce_match.group(1))
                nonce = ajax_data.get('nonce')

            # Extract setting from data-filters-settings attribute (HTML-escaped)
            setting_match = re.search(r'data-filters-settings=["\']([^"\']+)["\']', text)
            setting = html.unescape(setting_match.group(1)) if setting_match else '{}'

            # Step 2: POST to get ALL jobs (no server-side filters)
            post_data = {
                'action': 'get_hrt_jobs_handler',
                'setting': setting,
                'nonce': nonce
            }
            resp2 = await client.post(
                'https://www.hudsonrivertrading.com/wp-admin/admin-ajax.php',
                data=post_data
            )
            jobs_raw = resp2.json()

            # Step 3: Parse each job from HTML content
            def parse_job(job):
                content = job['content']
                # Extract data-term (===separated taxonomy slugs)
                term_match = re.search(r'data-term=["\']([^"\']*)["\']', content)
                terms = set(term_match.group(1).split('===')) if term_match else set()
                # Extract data-jobid
                jobid_match = re.search(r'data-jobid=["\']([^"\']*)["\']', content)
                jobid = jobid_match.group(1) if jobid_match else str(job['ID'])
                # Extract job URL from hrt-card-title anchor
                url_match = re.search(r'class=["\']hrt-card-title["\'][^>]+href=["\']([^"\']+)["\']', content)
                if not url_match:
                    url_match = re.search(r'href=["\']([^"\']+)["\']', content)
                job_url = url_match.group(1) if url_match else ''
                # Extract location display names from first list of card info items
                loc_items = re.findall(r'<li class=["\']hrt-card-info-item["\']><span>([^<]+)</span></li>', content)
                location = ', '.join(loc_items[:3]) if loc_items else ''
                # Unescape HTML entities in title
                title = html.unescape(job['title'])
                return {
                    'id': jobid,
                    'title': title,
                    'location': location,
                    'url': job_url,
                    '_terms': terms,
                }

            all_jobs = [parse_job(j) for j in jobs_raw]

            # Step 4: Apply URL filters client-side
            parsed = urlparse(self.INPUT_CAREER_URL)
            qs = parse_qs(parsed.query)

            job_types = [s for s in qs.get('job-type', [''])[0].split(',') if s]
            job_cats  = [s for s in qs.get('job-category', [''])[0].split(',') if s]
            locations = [s for s in qs.get('locations', [''])[0].split(',') if s]

            def matches(job, filter_slugs):
                return not filter_slugs or bool(job['_terms'] & set(filter_slugs))

            filtered = [
                j for j in all_jobs
                if matches(j, job_types) and matches(j, job_cats) and matches(j, locations)
            ]

            # Remove internal _terms key before returning
            for j in filtered:
                j.pop('_terms', None)

            return filtered
