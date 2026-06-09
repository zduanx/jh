import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class HrtExtractor(BaseExtractorV2):
    COMPANY_NAME = "hrt"
    ICON_URL = "https://www.hudsonrivertrading.com/wp-content/uploads/2023/11/cropped-HRT-Avatar-Profile-Photo-Favicon-180x180.png"
    INPUT_CAREER_URL = "https://www.hudsonrivertrading.com/careers/?job-type=full-time-experienced%2Cparent_full-time-experienced%2C&job-category=software-engineeringpython%2Cparent_software-engineeringc%2C&locations=new-york%2C"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        import re
        import html as html_module
        import json
        from urllib.parse import urlparse, parse_qs

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # Fetch careers page to get fresh nonce and setting
            resp = await client.get('https://www.hudsonrivertrading.com/careers/')
            page_html = resp.text

            # Extract hrtJobsAjax (ajaxurl + nonce)
            hrt_ajax_match = re.search(r'hrtJobsAjax\s*=\s*(\{[^}]+\})', page_html)
            hrt_ajax = json.loads(hrt_ajax_match.group(1))
            ajaxurl = hrt_ajax['ajaxurl']
            nonce = hrt_ajax['nonce']

            # Extract data-filters-settings (HTML-encoded in DOM, jQuery .attr() decodes it)
            filters_match = re.search(r'data-filters-settings=\"([^\"]+)\"', page_html)
            setting_raw = filters_match.group(1) if filters_match else None
            setting_decoded = html_module.unescape(setting_raw) if setting_raw else None

            # POST to admin-ajax with no filters to get ALL jobs
            post_resp = await client.post(
                ajaxurl,
                data={
                    'action': 'get_hrt_jobs_handler',
                    'setting': setting_decoded,
                    'nonce': nonce,
                }
            )
            jobs_raw = json.loads(post_resp.text)

        # Parse URL filters from self.INPUT_CAREER_URL
        parsed_url = urlparse(self.INPUT_CAREER_URL)
        qs = parse_qs(parsed_url.query)

        def split_filter(val):
            # values like "full-time-experienced,parent_full-time-experienced,"
            parts = [v.strip() for v in val.split(',') if v.strip()]
            return parts

        job_type_filter = split_filter(qs.get('job-type', [''])[0])
        job_category_filter = split_filter(qs.get('job-category', [''])[0])
        location_filter = split_filter(qs.get('locations', [''])[0])

        # Map and filter jobs
        mapped_jobs = []
        for job in jobs_raw:
            content = job.get('content', '')

            # Extract data-term (===separated list of taxonomy terms)
            term_match = re.search(r'data-term=\"([^\"]+)\"', content)
            data_term = term_match.group(1) if term_match else ''
            terms = set(data_term.split('===')) if data_term else set()

            # Extract data-jobid
            jobid_match = re.search(r'data-jobid=\"([^\"]+)\"', content)
            job_id = jobid_match.group(1) if jobid_match else str(job.get('ID', ''))

            # Extract job URL
            url_match = re.search(r'href=\"(https://www\.hudsonrivertrading\.com/hrt-job/[^\"]+)\"', content)
            job_url = url_match.group(1) if url_match else ''

            # Extract locations from first <ul class="hrt-card-info-list">
            ul_sections = re.findall(r'<ul class=\"hrt-card-info-list[^\"]*\">(.*?)</ul>', content, re.DOTALL)
            locations = []
            if ul_sections:
                loc_items = re.findall(r'<span>([^<]+)</span>', ul_sections[0])
                locations = loc_items

            title = html_module.unescape(job.get('title', ''))

            mapped = {
                'id': job_id,
                'title': title,
                'location': ', '.join(locations),
                'url': job_url,
                'response_data': job,
                '_terms': terms,
            }
            mapped_jobs.append(mapped)

        # Apply client-side filters
        filtered = []
        for j in mapped_jobs:
            terms = j['_terms']
            if job_type_filter and not any(t in terms for t in job_type_filter):
                continue
            if job_category_filter and not any(t in terms for t in job_category_filter):
                continue
            if location_filter and not any(t in terms for t in location_filter):
                continue
            # Remove internal _terms key before returning
            out = {k: v for k, v in j.items() if k != '_terms'}
            filtered.append(out)

        return filtered
