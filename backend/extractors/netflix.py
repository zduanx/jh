"""
Netflix Job URL Extractor

API: https://explore.jobs.netflix.net/api/apply/v2/jobs
Pattern: Standard REST API with pagination (start/num)

Sample API Response:
{
  "count": 40,
  "positions": [
    {
      "id": "790313240022",
      "name": "Full Stack Software Engineer - Ads Measurement Platform",
      "canonicalPositionUrl": "https://explore.jobs.netflix.net/careers/job/790313240022",
      "location": "Los Gatos, California"
    }
  ]
}
"""

from typing import List, Dict, Any
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class NetflixExtractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from Netflix careers API

    Example:
        extractor = NetflixExtractor()
        urls = extractor.extract_source_urls_metadata()
    """
    COMPANY_NAME = Company.NETFLIX

    API_URL = "https://explore.jobs.netflix.net/api/apply/v2/jobs"
    URL_PREFIX_JOB = "https://jobs.netflix.com/jobs"

    def __init__(self, config):
        """Initialize Netflix extractor"""
        super().__init__(config)

    def get_headers(self) -> Dict[str, str]:
        """Override with Netflix-specific headers"""
        return {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'referer': 'https://explore.jobs.netflix.net/careers',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }

    def _build_params(self, start: int, num: int) -> Dict[str, Any]:
        """
        Build query parameters

        Args:
            start: Starting position (0-indexed)
            num: Number of jobs to fetch

        Returns:
            Query parameters dict
        """
        # Hardcoded filters for Netflix
        params = {
            'domain': 'netflix.com',
            'sort_by': 'relevance',
            'start': start,
            'num': num,
            'Teams': 'Engineering',
            'Work Type': 'onsite',
            'Region': 'ucan',
        }

        return params

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs using pagination and return standardized job objects

        Applies API-level filters (Teams, Work Type, Region) through hardcoded params
        and returns standardized job objects with id, title, and response_data.

        Returns:
            List of standardized job objects:
            {
                'id': str,              # Job ID for URL construction
                'title': str,           # Job title for filtering
                'response_data': dict   # Original job data from API
            }
        """
        # Hardcoded batch size
        BATCH_SIZE = 50

        all_standardized_jobs = []
        start = 0

        try:
            # First call to get total count
            params = self._build_params(start=0, num=BATCH_SIZE)
            response = await self.make_request(
                self.API_URL,
                params=params,
                timeout=10.0
            )

            data = response.json()
            positions = data.get('positions', [])
            total = data.get('count', 0)

            if not positions:
                return []

            # Process first batch
            for position in positions:
                standardized_job = {
                    'id': position.get('id'),
                    'title': position.get('name', ''),
                    'location': position.get('location', ''),
                    'response_data': position
                }
                all_standardized_jobs.append(standardized_job)

            start = len(positions)

            # Fetch remaining pages
            while start < total:
                params = self._build_params(start=start, num=BATCH_SIZE)
                response = await self.make_request(
                    self.API_URL,
                    params=params,
                    timeout=10.0
                )

                data = response.json()
                positions = data.get('positions', [])

                if not positions:
                    break

                # Process batch
                for position in positions:
                    standardized_job = {
                        'id': position.get('id'),
                        'title': position.get('name', ''),
                        'location': position.get('location', ''),
                        'response_data': position
                    }
                    all_standardized_jobs.append(standardized_job)

                start += len(positions)

            return all_standardized_jobs

        except Exception as e:
            print(f"Error fetching Netflix jobs: {e}")
            return []

