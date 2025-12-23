"""
Roblox Careers Job URL Extractor

API: https://d32kbl9jppd7az.cloudfront.net/careers/jobs.json
Pattern: Static JSON file with all jobs (no pagination needed)
Data format: Array of job objects

Sample API Response:
[
  {
    "id": "7460850",
    "title": "Software Engineer - Infrastructure",
    "employment_type": "Salaried Employee",
    "location": "San Mateo, CA, United States",
    "department": "Engineering"
  },
  {
    "id": "7369198",
    "title": "Senior Software Engineer",
    "employment_type": "Contractor",
    "location": "Remote",
    "department": "Engineering"
  }
]
"""

from typing import List, Dict, Any
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class RobloxExtractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from Roblox Careers API

    Example:
        extractor = RobloxExtractor()
        urls = extractor.extract_source_urls_metadata()
    """
    COMPANY_NAME = Company.ROBLOX

    API_URL = "https://d32kbl9jppd7az.cloudfront.net/careers/jobs.json"
    URL_PREFIX_JOB = "https://careers.roblox.com/jobs"

    def __init__(self, config):
        """Initialize Roblox extractor"""
        super().__init__(config)

    def get_headers(self) -> Dict[str, str]:
        """Override with Roblox-specific headers"""
        headers = super().get_headers()
        headers['Accept'] = 'application/json'
        return headers

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs from API and return standardized job objects

        Applies API-level filters (employment_type, location) and returns
        standardized job objects with id, title, and response_data.

        Returns:
            List of standardized job objects:
            {
                'id': str,              # Job ID for URL construction
                'title': str,           # Job title for filtering
                'response_data': dict   # Original job data from API
            }
        """
        # Hardcoded API filters for Roblox
        EMPLOYMENT_TYPE = 'Salaried Employee'
        LOCATION = 'San Mateo, CA, United States'

        try:
            response = await self.make_request(self.API_URL, timeout=10.0)
            jobs = response.json()
            if not isinstance(jobs, list):
                return []

            # Apply API filters and standardize structure
            standardized_jobs = []
            for job in jobs:
                # Check employment type
                if job.get('employment_type') != EMPLOYMENT_TYPE:
                    continue

                # Check location
                if job.get('location') != LOCATION:
                    continue

                # Create standardized job object
                standardized_job = {
                    'id': job.get('id'),
                    'title': job.get('title', ''),
                    'location': job.get('location', ''),
                    'response_data': job
                }
                standardized_jobs.append(standardized_job)

            return standardized_jobs

        except Exception as e:
            print(f"Error fetching Roblox jobs: {e}")
            return []

