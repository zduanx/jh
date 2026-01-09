"""
Google Careers Job URL Extractor

Pattern: HTML with embedded JavaScript data (AF_initDataCallback)
Pagination: URL parameter 'page' (1, 2, 3, ...)
Data format: Job IDs embedded in HTML (15-20 digit numbers)

Note: Google doesn't expose a clean JSON API. Jobs are embedded in HTML
via AF_initDataCallback JavaScript calls. We extract job IDs using regex.

Sample HTML Structure:
<script>
AF_initDataCallback({
  ...
  "jobs/results/123456789012345678": {...},
  "123456789012345678": "Software Engineer"
  ...
});
</script>
"""

from typing import List, Dict, Any
import re
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class GoogleExtractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from Google Careers

    Example:
        extractor = GoogleExtractor()
        urls = extractor.extract_source_urls_metadata()

    Note: Google doesn't support title filtering, so CONFIG_URL_SOURCING is empty.
          All filtering is done via API parameters.
    """

    COMPANY_NAME = Company.GOOGLE
    API_URL = "https://www.google.com/about/careers/applications/jobs/results"
    URL_PREFIX_JOB = "https://www.google.com/about/careers/applications/jobs/results"

    def __init__(self, config):
        """Initialize Google extractor"""
        super().__init__(config)

    def _build_params(self, page: int = None) -> Dict[str, Any]:
        """
        Build query parameters

        Args:
            page: Page number (1-indexed, None for first page)

        Returns:
            Query parameters dict
        """
        # Hardcoded filters for Google
        params = {
            'employment_type': 'FULL_TIME',
            'company': ['Google', 'YouTube'],
            'location': ['California, USA'],
            'q': '"Software Engineer"',  # Quoted for exact phrase match
            'target_level': 'ADVANCED',
        }

        if page and page > 1:
            params['page'] = page

        return params

    def _extract_jobs_from_html(self, html: str) -> List[Dict[str, str]]:
        """
        Extract job data (ID, title, location) from HTML

        Uses pattern: ["<job_id>","<title>","<url>", ...]

        Args:
            html: HTML response

        Returns:
            List of job objects with 'id', 'title', and 'location' fields
        """
        jobs = []
        seen_ids = set()

        # Pattern: ["job_id","title","url", ...]
        # Job IDs are 15-20 digits
        # Note: We use a simpler pattern to avoid escape issues
        pattern = r'\["(\d{15,20})","([^"]*?)","https://www\.google\.com/about/careers'
        matches = re.findall(pattern, html)

        for job_id, title in matches:
            if job_id not in seen_ids:
                # Use hardcoded location from filters (California, USA)
                location = "California, USA"  # Matches the filter
                jobs.append({'id': job_id, 'title': title, 'location': location})
                seen_ids.add(job_id)

        return jobs

    async def _fetch_jobs_page(self, page: int = 1) -> List[Dict[str, str]]:
        """
        Fetch one page of jobs

        Args:
            page: Page number (1-indexed)

        Returns:
            List of job objects with 'id' and 'title' fields
        """
        params = self._build_params(page)

        try:
            response = await self.make_request(
                self.API_URL,
                params=params,
                timeout=10.0
            )

            jobs = self._extract_jobs_from_html(response.text)
            return jobs

        except Exception as e:
            print(f"Error fetching Google jobs page {page}: {e}")
            return []

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs using pagination

        Stops automatically when:
        - No jobs are returned
        - No new jobs are found (all duplicates)

        Returns:
            List of job objects with standardized structure:
            {
                'id': str,
                'title': str,
                'response_data': dict  # Contains original data from HTML
            }
        """
        all_jobs = []
        seen_ids = set()
        page = 1

        while True:
            jobs = await self._fetch_jobs_page(page)

            if not jobs:
                # No jobs found, stop
                break

            # Add only new jobs (deduplicate by ID)
            new_jobs = []
            for job in jobs:
                job_id = job.get('id')
                if job_id and job_id not in seen_ids:
                    # Convert to standardized format
                    standardized_job = {
                        'id': job_id,
                        'title': job.get('title', ''),
                        'location': job.get('location', 'California, USA'),
                        'response_data': job  # Preserve original data
                    }
                    new_jobs.append(standardized_job)
                    seen_ids.add(job_id)

            all_jobs.extend(new_jobs)

            # Stop if no new jobs (reached end of pagination)
            if len(new_jobs) == 0:
                break

            page += 1

        return all_jobs

    def extract_raw_info(self, raw_content: str) -> dict:
        """
        Extract structured job details from Google Careers job page HTML.

        Google job pages have h3 sections:
        - About the job (paragraph text)
        - Responsibilities (ul list)
        - Minimum qualifications: (ul list)
        - Preferred qualifications: (ul list)

        Args:
            raw_content: Raw HTML string from crawl_raw_info()

        Returns:
            {'description': str, 'requirements': str}

        Raises:
            ValueError: If content cannot be parsed
        """
        if not raw_content:
            raise ValueError("No content to extract from")

        def strip_html(html: str) -> str:
            """Strip HTML tags and normalize whitespace"""
            text = re.sub(r'<br\s*/?>', '\n', html)
            text = re.sub(r'<li[^>]*>', '\n- ', text)  # Convert list items
            text = re.sub(r'</li>', '', text)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'&amp;', '&', text)
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'&#39;', "'", text)
            text = re.sub(r'&quot;', '"', text)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n +', '\n', text)
            text = re.sub(r'\\n', '\n', text)  # Escaped newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\n\n- ', '\n- ', text)  # No blank lines between list items
            return text.strip()

        def extract_section(header_pattern: str) -> str:
            """Extract content after h3 header until next h3 or section end"""
            # Pattern: <h3>Header</h3> followed by content until next <h3> or </div>
            pattern = rf'<h3[^>]*>{header_pattern}[^<]*</h3>(.*?)(?=<h3|</div><div class="|$)'
            match = re.search(pattern, raw_content, re.DOTALL | re.IGNORECASE)
            if match:
                return strip_html(match.group(1))
            return ''

        # Build description from About the job and Responsibilities
        description_parts = []

        about_job = extract_section('About the job')
        if about_job:
            description_parts.append(about_job)

        responsibilities = extract_section('Responsibilities')
        if responsibilities:
            description_parts.append(f"Responsibilities:{responsibilities}")

        # Build requirements from qualifications sections
        requirements_parts = []

        min_qual = extract_section('Minimum qualifications')
        if min_qual:
            requirements_parts.append(f"Minimum Qualifications:{min_qual}")

        pref_qual = extract_section('Preferred qualifications')
        if pref_qual:
            requirements_parts.append(f"Preferred Qualifications:{pref_qual}")

        return {
            'description': '\n\n'.join(description_parts),
            'requirements': '\n\n'.join(requirements_parts),
        }
