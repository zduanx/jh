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

    def extract_raw_info(self, raw_content: str) -> dict:
        """
        Extract structured job details from Roblox careers page HTML.

        Roblox job pages have content between content-intro and description divs,
        with sections marked by <strong> tags:
        - "You Will:" - Responsibilities (description)
        - "You Have:" or "You Are" - Requirements

        Args:
            raw_content: Raw HTML string from crawl_raw_info()

        Returns:
            {'description': str, 'requirements': str}

        Raises:
            ValueError: If content cannot be parsed
        """
        import re
        import html

        if not raw_content:
            raise ValueError("No content to extract from")

        def strip_html(text: str) -> str:
            """Strip HTML tags and normalize whitespace"""
            text = re.sub(r'<br\s*/?>', '\n', text)
            text = re.sub(r'<li[^>]*>', '\n- ', text)
            text = re.sub(r'</li>', '', text)
            text = re.sub(r'<p[^>]*>', '\n', text)
            text = re.sub(r'</p>', '\n', text)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = html.unescape(text)  # Decode &#x27; etc.
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n +', '\n', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\n\n- ', '\n- ', text)  # No blank lines between list items
            return text.strip()

        # Extract main job content (between content-intro and description div)
        content_match = re.search(
            r'<div class="content-intro">(.*?)<div class="description"',
            raw_content,
            re.DOTALL
        )

        if not content_match:
            raise ValueError("Could not find job content section")

        job_content = content_match.group(1)

        # Extract description (You Will section)
        description_parts = []

        # Look for intro sections before "You Will" or "You Are"
        # Pattern handles both <p><strong> and <h2><strong> wrappers
        intro_match = re.search(
            r'</div>(.*?)(?:<(?:p|h2)>)?<strong>You (?:Will|Are)',
            job_content,
            re.DOTALL | re.IGNORECASE
        )
        if intro_match:
            intro_text = strip_html(intro_match.group(1))
            if intro_text and len(intro_text) > 50:  # Skip if too short
                description_parts.append(intro_text)

        # You Will section (responsibilities)
        # Handles both <strong>You Will</strong> and <h2><strong>You Will</strong></h2>
        you_will_match = re.search(
            r'<strong>You Will:?</strong>(?:</h2>)?(.*?)(?:(?:<(?:p|h2)>)?<strong>You (?:Have|Are)|$)',
            job_content,
            re.DOTALL | re.IGNORECASE
        )
        if you_will_match:
            you_will = strip_html(you_will_match.group(1))
            if you_will:
                description_parts.append(f"Responsibilities:\n{you_will}")

        # Extract requirements (You Have or You Are section)
        requirements_parts = []

        # You Have section
        you_have_match = re.search(
            r'<strong>You Have:?</strong>(?:</h2>)?(.*?)(?:(?:<(?:p|h2)>)?<strong>|<div class="description"|$)',
            job_content,
            re.DOTALL | re.IGNORECASE
        )
        if you_have_match:
            you_have = strip_html(you_have_match.group(1))
            if you_have:
                requirements_parts.append(you_have)

        # You Are section (alternative format)
        you_are_match = re.search(
            r'<strong>You Are[^<]*</strong>(?:</h2>)?(.*?)(?:(?:<(?:p|h2)>)?<strong>You Will|$)',
            job_content,
            re.DOTALL | re.IGNORECASE
        )
        if you_are_match:
            you_are = strip_html(you_are_match.group(1))
            if you_are:
                requirements_parts.append(you_are)

        return {
            'description': '\n\n'.join(description_parts),
            'requirements': '\n\n'.join(requirements_parts),
        }

