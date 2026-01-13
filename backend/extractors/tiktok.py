"""
TikTok Job URL Extractor

API: https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts
Pattern: POST request with pagination (offset-based)

Sample API Response:
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 450,
    "job_post_list": [
      {
        "id": "7123456789",
        "title": "Software Engineer - Backend",
        "location": "San Jose, CA",
        "department": "Engineering"
      }
    ]
  }
}
"""

from typing import List, Dict, Any
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class TikTokExtractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from TikTok API

    Example:
        extractor = TikTokExtractor()
        urls = extractor.extract_source_urls_metadata()
    """
    COMPANY_NAME = Company.TIKTOK

    API_URL = "https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts"
    URL_PREFIX_JOB = "https://lifeattiktok.com/search"

    def __init__(self, config):
        """Initialize TikTok extractor"""
        super().__init__(config)

    def get_headers(self) -> Dict[str, str]:
        """Override with TikTok-specific headers"""
        return {
            'accept': '*/*',
            'accept-language': 'en-US',
            'content-type': 'application/json',
            'origin': 'https://lifeattiktok.com',
            'referer': 'https://lifeattiktok.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'website-path': 'tiktok',
        }

    def _build_location_from_city_info(self, city_info: Dict[str, Any]) -> str:
        """
        Build location string from TikTok's nested city_info structure

        Args:
            city_info: Nested city info dict with structure:
                {
                    "en_name": "San Jose",
                    "parent": {
                        "en_name": "California",
                        "parent": {
                            "en_name": "United States of America"
                        }
                    }
                }

        Returns:
            Location string like "San Jose, California" (city, state only - no country)
        """
        if not city_info:
            return ''

        parts = []

        # City (depth 1)
        if city_info.get('en_name'):
            parts.append(city_info['en_name'])

        # State (depth 2)
        state = city_info.get('parent', {})
        if state and state.get('en_name'):
            parts.append(state['en_name'])

        # Skip country (depth 3) - we only want city and state

        return ', '.join(parts)

    def _build_payload(self, limit: int, offset: int) -> Dict[str, Any]:
        """
        Build request payload

        Args:
            limit: Number of jobs to fetch
            offset: Starting position

        Returns:
            Request payload
        """
        # Hardcoded filters for TikTok
        return {
            'recruitment_id_list': ['1'],
            'job_category_id_list': ['6704215862603155720'],
            'subject_id_list': [],
            'location_code_list': ['CT_157', 'CT_75', 'CT_1103355'],
            'keyword': '',
            'limit': limit,
            'offset': offset,
        }

    async def _fetch_jobs_page(self, limit: int, offset: int) -> tuple[List[Dict], int]:
        """
        Fetch one page of jobs

        Args:
            limit: Number of jobs to fetch
            offset: Starting position

        Returns:
            Tuple of (jobs list, total count)
        """
        payload = self._build_payload(limit, offset)

        try:
            response = await self.make_request(
                self.API_URL,
                method='POST',
                json=payload,
                timeout=10.0
            )

            data = response.json()

            if data.get('code') == 0:
                jobs = data.get('data', {}).get('job_post_list', [])
                total = data.get('data', {}).get('count', 0)
                return jobs, total
            else:
                print(f"TikTok API error: {data.get('message')}")
                return [], 0

        except Exception as e:
            print(f"Error fetching TikTok jobs: {e}")
            return [], 0

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs using pagination

        Returns:
            List of job objects with standardized structure:
            {
                'id': str,
                'title': str,
                'response_data': dict  # Contains all API fields
            }
        """
        # Hardcoded batch size
        BATCH_SIZE = 100

        all_jobs = []
        offset = 0

        # First call to get total
        jobs, total = await self._fetch_jobs_page(limit=BATCH_SIZE, offset=0)
        if not jobs:
            return []

        all_jobs.extend(jobs)
        offset = BATCH_SIZE

        # Fetch remaining pages
        while offset < total:
            jobs, _ = await self._fetch_jobs_page(limit=BATCH_SIZE, offset=offset)
            if not jobs:
                break
            all_jobs.extend(jobs)
            offset += BATCH_SIZE

        # Convert to standardized format
        standardized_jobs = []
        for job in all_jobs:
            # Build location from nested city_info structure
            city_info = job.get('city_info', {})
            location = self._build_location_from_city_info(city_info)

            standardized_job = {
                'id': str(job.get('id', '')),
                'title': job.get('title', ''),
                'location': location,
                'response_data': job  # Preserve all API fields
            }
            standardized_jobs.append(standardized_job)

        return standardized_jobs

    def extract_raw_info(self, raw_content: str) -> dict:
        """
        Extract structured job details from TikTok job page HTML.

        TikTok uses two formats:
        1. Next.js RSC format: Content in self.__next_f.push() calls with T<hex> blocks
        2. Direct HTML format: Content in Tailwind-styled <p> tags with tt-text class

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
            text = html.unescape(text)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n +', '\n', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\n\n- ', '\n- ', text)  # No blank lines between list items
            return text.strip()

        # Try Format 2 first: Direct HTML with Tailwind classes
        # Pattern: <p class="text-[32px]...">Section</p><p class="tt-text...">content</p>
        responsibilities_match = re.search(
            r'>Responsibilities</p>\s*<p[^>]*class="[^"]*tt-text[^"]*"[^>]*>(.*?)</p>',
            raw_content,
            re.DOTALL | re.IGNORECASE
        )
        qualifications_match = re.search(
            r'>Qualifications</p>\s*<p[^>]*class="[^"]*tt-text[^"]*"[^>]*>(.*?)</p>',
            raw_content,
            re.DOTALL | re.IGNORECASE
        )

        if responsibilities_match or qualifications_match:
            # Direct HTML format
            description = ''
            requirements = ''

            if responsibilities_match:
                description = strip_html(responsibilities_match.group(1))

            if qualifications_match:
                requirements = strip_html(qualifications_match.group(1))
                # Normalize bullet points
                requirements = requirements.replace('•', '-')

            return {
                'description': description,
                'requirements': requirements,
            }

        # Format 1: Next.js RSC format
        pieces = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', raw_content, re.DOTALL)
        if not pieces:
            raise ValueError("Could not find job content in any supported format")

        full = ''.join(pieces)
        # Unescape JSON string escapes (double-escaped in RSC format)
        full = full.replace('\\\\n', '\n').replace('\\n', '\n')
        full = full.replace('\\"', '"')
        # Handle JSON unicode escapes like \u0026 -> &
        full = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), full)
        full = html.unescape(full)

        # Extract description - first text block (Team Intro + Responsibilities)
        # Format: 30:T5f5,<content>
        desc_match = re.search(r'\d+:T[a-f0-9]+,(.*?)(?=\d+:T[a-f0-9]+,|\d+:\[|$)', full, re.DOTALL)
        if not desc_match:
            raise ValueError("Could not find description text block")

        description = desc_match.group(1).strip()

        # Extract qualifications - inline in RSC JSON
        # Look for "Minimum Qualifications" followed by bullet points
        qual_match = re.search(
            r'(Minimum Qualifications:?.*?Preferred Qualifications:?.*?)(?:"|\\}|\])',
            full,
            re.DOTALL | re.IGNORECASE
        )

        requirements = ''
        if qual_match:
            requirements = qual_match.group(1)
            # Clean up escape sequences
            requirements = requirements.replace('\\n', '\n').replace('\\', '')
            # Normalize bullet points (• to -)
            requirements = requirements.replace('•', '-')
            requirements = strip_html(requirements)

        # Clean up description
        description = strip_html(description)

        # Format with section headers if not already present
        if requirements and not requirements.startswith('Minimum'):
            requirements = f"Minimum Qualifications:\n{requirements}"

        return {
            'description': description,
            'requirements': requirements,
        }
