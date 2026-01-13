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
                # Add 'url' from canonicalPositionUrl for base class URL building
                position['url'] = position.get('canonicalPositionUrl', '')
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
                    # Add 'url' from canonicalPositionUrl for base class URL building
                    position['url'] = position.get('canonicalPositionUrl', '')
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

    async def crawl_raw_info(self, job_url: str) -> str:
        """
        Fetch raw content from Netflix job page.

        Netflix URLs (jobs.netflix.com/jobs/ID) need to be converted to
        explore.jobs.netflix.net/careers/job/ID for actual content.

        Args:
            job_url: Full URL to the job posting page

        Returns:
            Raw HTML string

        Raises:
            Exception: On HTTP errors or connection failures
        """
        import re

        # Convert jobs.netflix.com URL to explore.jobs.netflix.net
        job_id_match = re.search(r'/jobs/(\d+)', job_url)
        if job_id_match:
            job_id = job_id_match.group(1)
            actual_url = f"https://explore.jobs.netflix.net/careers/job/{job_id}"
        else:
            actual_url = job_url

        response = await self.make_request(
            actual_url,
            timeout=15.0
        )
        return response.text

    def extract_raw_info(self, raw_content: str) -> dict:
        """
        Extract structured job details from Netflix job page HTML.

        Netflix embeds job data in JSON-LD (schema.org JobPosting) within a script tag.
        The description field contains HTML with optional section headers:
        - <h2> tags for major sections (Job Summary, About the Team)
        - <strong> tags for subsections (qualifications, nice to have)

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
            # Handle list items: <li><p>content</p></li> -> \n- content
            text = re.sub(r'<li[^>]*>\s*<p[^>]*>', '\n- ', text)  # li+p combo
            text = re.sub(r'</p>\s*</li>', '', text)  # Close li+p combo
            text = re.sub(r'<li[^>]*>', '\n- ', text)  # Standalone li
            text = re.sub(r'</li>', '', text)
            text = re.sub(r'<p[^>]*>', '\n', text)
            text = re.sub(r'</p>', '\n', text)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = html.unescape(text)  # Decode &#39; etc.
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n +', '\n', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\n\n- ', '\n- ', text)  # No blank lines between list items
            return text.strip()

        # Extract description from JSON-LD JobPosting
        desc_match = re.search(r'"description":\s*"(.*?)"(?=,\s*")', raw_content, re.DOTALL)
        if not desc_match:
            raise ValueError("Could not find job description in JSON-LD")

        desc_html = html.unescape(desc_match.group(1))

        # Try to split into description and requirements sections
        description_parts = []
        requirements_parts = []

        # Look for qualifications section markers
        # Netflix uses various patterns:
        # - <b><span>Qualifications:</span></b>
        # - <strong>Qualifications:</strong>
        # - <h2>Who you are</h2>
        # - "We're Eager to Talk to You If:" (plain text in <p>)
        qual_patterns = [
            r'<(?:strong|b)[^>]*>\s*<span>\s*Qualifications?:?\s*</span>\s*</(?:strong|b)>',  # Netflix: <b><span>Qualifications:</span></b>
            r'<(?:strong|b)[^>]*>\s*(?:We are looking for individuals with the following )?qualifications?:?\s*</(?:strong|b)>',
            r'<h2[^>]*>\s*(?:Required )?Qualifications?:?\s*</h2>',
            r'<(?:strong|b)[^>]*>\s*Requirements?:?\s*</(?:strong|b)>',
            r'<h2[^>]*>\s*<span>\s*Who you are\s*</span>\s*</h2>',  # Netflix variant
            r'<h2[^>]*>\s*Who you are\s*</h2>',  # Netflix variant without span
            r"<p>We&#39;re Eager to Talk to You If:?</p>",  # Netflix variant: plain text requirement header
            r"<p>We're Eager to Talk to You If:?</p>",  # Netflix variant: decoded
        ]

        nice_to_have_patterns = [
            r'<(?:strong|b)[^>]*>\s*Nice to have:?\s*</(?:strong|b)>',
            r'<(?:strong|b)[^>]*>\s*Preferred:?\s*</(?:strong|b)>',
            r'<h2[^>]*>\s*Nice to have:?\s*</h2>',
            r'<h2[^>]*>\s*<span>\s*What sets you apart\s*</span>\s*</h2>',  # Netflix variant
            r'<h2[^>]*>\s*What sets you apart\s*</h2>',  # Netflix variant without span
            r'<li>Some nice to haves:',  # Netflix variant: inline in list item
        ]

        # Patterns that mark end of requirements (back to description content)
        end_req_patterns = [
            r'<(?:strong|b)[^>]*>\s*What (?:will you|you will) learn',
            r'<(?:strong|b)[^>]*>\s*The (?:Summer )?Internship',
            r'<(?:strong|b)[^>]*>\s*About (?:the|this)',
            r'<h2[^>]*>\s*A few more things about us\s*</h2>',  # Netflix compensation section
            r'<p>Our compensation structure',  # Netflix: compensation section starts
        ]

        # Find the start of qualifications section
        qual_start = None
        for pattern in qual_patterns:
            match = re.search(pattern, desc_html, re.IGNORECASE)
            if match:
                qual_start = match.start()
                break

        if qual_start:
            # Split at qualifications
            desc_part = desc_html[:qual_start]
            req_part = desc_html[qual_start:]

            description_parts.append(strip_html(desc_part))

            # Find end of requirements section (if there's more description after)
            req_end = len(req_part)
            for pattern in end_req_patterns:
                match = re.search(pattern, req_part, re.IGNORECASE)
                if match:
                    req_end = match.start()
                    # Add remaining content back to description
                    remaining = req_part[match.start():]
                    description_parts.append(strip_html(remaining))
                    break

            req_part = req_part[:req_end]

            # Check for "nice to have" within requirements
            nice_start = None
            for pattern in nice_to_have_patterns:
                match = re.search(pattern, req_part, re.IGNORECASE)
                if match:
                    nice_start = match.start()
                    break

            if nice_start:
                required_part = req_part[:nice_start]
                preferred_part = req_part[nice_start:]
                requirements_parts.append(f"Required:\n{strip_html(required_part)}")
                requirements_parts.append(f"Preferred:\n{strip_html(preferred_part)}")
            else:
                requirements_parts.append(strip_html(req_part))
        else:
            # No clear requirements section - put everything in description
            description_parts.append(strip_html(desc_html))

        return {
            'description': '\n\n'.join(description_parts),
            'requirements': '\n\n'.join(requirements_parts),
        }

