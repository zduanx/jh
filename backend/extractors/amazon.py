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
