"""
Amazon Jobs URL Extractor

API: https://amazon.jobs/en/search.json
Pattern: Standard REST API with pagination (offset-based)

Note: Amazon API returns two ID fields:
  - id: UUID format (e.g., "d42a7446-bd11-40ed-9e72-425214f6d55a")
  - id_icims: Job number used in URLs (e.g., "3142524")

We use id_icims for URL construction since it matches the job_path.

Sample API Response:
{
  "hits": 150,
  "jobs": [
    {
      "id": "d42a7446-bd11-40ed-9e72-425214f6d55a",
      "id_icims": "3142524",
      "title": "Software Development Engineer II",
      "job_path": "/en/jobs/3142524/software-development-engineer-ii",
      "location": "Seattle, WA, USA",
      "job_category": "Software Development"
    }
  ]
}
"""

from typing import List, Dict, Any
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class AmazonExtractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from Amazon Jobs API

    Example:
        extractor = AmazonExtractor()
        urls = extractor.extract_source_urls_metadata()
    """
    COMPANY_NAME = Company.AMAZON

    API_URL = "https://amazon.jobs/en/search.json"
    URL_PREFIX_JOB = "https://amazon.jobs"

    def __init__(self, config):
        """Initialize Amazon extractor"""
        super().__init__(config)

    def get_headers(self) -> Dict[str, str]:
        """Override with Amazon-specific headers"""
        return {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }

    def _build_params(self, offset: int, result_limit: int) -> Dict[str, Any]:
        """
        Build query parameters

        Args:
            offset: Starting position
            result_limit: Number of jobs to fetch

        Returns:
            Query parameters dict
        """
        # Hardcoded filters for Amazon
        params = {
            'offset': offset,
            'result_limit': result_limit,
            'sort': 'relevant',
            'base_query': 'software engineer 3',
            'category[]': ['software-development'],
            'business_category[]': ['amazon-web-services'],
        }

        return params

    async def _fetch_jobs_page(self, offset: int, result_limit: int) -> tuple[List[Dict], int]:
        """
        Fetch one page of jobs

        Args:
            offset: Starting position
            result_limit: Number of jobs to fetch

        Returns:
            Tuple of (jobs list, total count)
        """
        params = self._build_params(offset, result_limit)

        try:
            response = await self.make_request(
                self.API_URL,
                params=params,
                timeout=10.0
            )

            data = response.json()
            jobs = data.get('jobs', [])
            total = data.get('hits', 0)
            return jobs, total

        except Exception as e:
            print(f"Error fetching Amazon jobs: {e}")
            return [], 0

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs using pagination

        Returns:
            List of job objects with standardized structure:
            {
                'id': str,
                'title': str,
                'response_data': dict  # Contains job_path, location, category, etc.
            }
        """
        # Hardcoded batch size
        BATCH_SIZE = 100

        all_jobs = []
        offset = 0

        # First call to get total
        jobs, total = await self._fetch_jobs_page(offset=0, result_limit=BATCH_SIZE)
        if not jobs:
            return []

        # Convert to standardized format
        for job in jobs:
            standardized_job = {
                'id': str(job.get('id_icims', '')),  # Use id_icims (job number) not id (UUID)
                'title': job.get('title', ''),
                'location': job.get('location', ''),
                'response_data': job  # Preserve all fields (job_path, location, etc.)
            }
            all_jobs.append(standardized_job)

        offset = len(jobs)

        # Fetch remaining pages
        while offset < total:
            jobs, _ = await self._fetch_jobs_page(offset=offset, result_limit=BATCH_SIZE)
            if not jobs:
                break

            # Convert to standardized format
            for job in jobs:
                standardized_job = {
                    'id': str(job.get('id_icims', '')),  # Use id_icims (job number) not id (UUID)
                    'title': job.get('title', ''),
                    'location': job.get('location', ''),
                    'response_data': job
                }
                all_jobs.append(standardized_job)

            offset += len(jobs)

        return all_jobs

    def extract_raw_info(self, raw_content: str) -> dict:
        """
        Extract structured job details from Amazon job page HTML.

        Amazon job pages have sections like:
        <div class="section"><h2>Description</h2>...</div>
        <div class="section"><h2>Basic Qualifications</h2>...</div>
        <div class="section"><h2>Preferred Qualifications</h2>...</div>

        Args:
            raw_content: Raw HTML string from crawl_raw_info()

        Returns:
            {'description': str, 'requirements': str}

        Raises:
            ValueError: If content cannot be parsed
        """
        import re

        if not raw_content:
            raise ValueError("No content to extract from")

        def strip_html(html: str) -> str:
            """Strip HTML tags and normalize whitespace"""
            text = re.sub(r'<br\s*/?>', '\n', html)  # Convert <br> to newline
            text = re.sub(r'<[^>]+>', ' ', text)  # Strip other tags
            text = re.sub(r'&amp;', '&', text)  # Decode &amp;
            text = re.sub(r'&lt;', '<', text)
            text = re.sub(r'&gt;', '>', text)
            text = re.sub(r'[ \t]+', ' ', text)  # Collapse spaces
            text = re.sub(r'\n +', '\n', text)  # Remove leading spaces after newline
            text = re.sub(r'\n{3,}', '\n\n', text)  # Collapse multiple newlines
            return text.strip()

        # Extract sections by <h2> headers
        sections = re.findall(
            r'<div class="section"><h2>(.*?)</h2>(.*?)</div>',
            raw_content,
            re.DOTALL
        )

        description = ''
        requirements_parts = []

        for title, content in sections:
            title_lower = title.lower().strip()
            text = strip_html(content)

            if 'description' in title_lower:
                description = text
            elif 'basic qualifications' in title_lower:
                requirements_parts.insert(0, f"Basic Qualifications:\n{text}")
            elif 'preferred qualifications' in title_lower:
                requirements_parts.append(f"Preferred Qualifications:\n{text}")

        return {
            'description': description,
            'requirements': '\n\n'.join(requirements_parts),
        }
