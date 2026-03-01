"""
OpenAI Job URL Extractor

API: https://api.ashbyhq.com/posting-api/job-board/openai
Pattern: Ashby REST JSON API (single request, no pagination)
All jobs returned in one response under "jobs" key.

Sample API Response:
{
  "apiVersion": 1,
  "jobs": [
    {
      "id": "240d459b-696d-43eb-8497-fab3e56ecd9b",
      "title": "Research Engineer",
      "department": "Research",
      "team": "Research",
      "employmentType": "FullTime",
      "location": "San Francisco",
      "jobUrl": "https://jobs.ashbyhq.com/openai/240d459b-...",
      "applyUrl": "https://jobs.ashbyhq.com/openai/240d459b-.../application",
      "descriptionHtml": "...",
      "descriptionPlain": "..."
    }
  ]
}
"""

import re
import html

from typing import List, Dict, Any
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class OpenAIExtractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from OpenAI careers (Ashby platform)

    Example:
        extractor = OpenAIExtractor(config=TitleFilters())
        urls = extractor.extract_source_urls_metadata()
    """
    COMPANY_NAME = Company.OPENAI

    API_URL = "https://api.ashbyhq.com/posting-api/job-board/openai"
    URL_PREFIX_JOB = "https://jobs.ashbyhq.com/openai"

    def __init__(self, config):
        """Initialize OpenAI extractor"""
        super().__init__(config)

    def get_headers(self) -> Dict[str, str]:
        """Override with Ashby-specific headers"""
        headers = super().get_headers()
        headers['Accept'] = 'application/json'
        return headers

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs from Ashby API (no pagination needed).

        Returns:
            List of standardized job objects:
            {
                'id': str,
                'title': str,
                'location': str,
                'response_data': dict
            }
        """
        try:
            response = await self.make_request(self.API_URL, timeout=15.0)
            data = response.json()
            jobs = data.get('jobs', [])

            if not isinstance(jobs, list):
                return []

            standardized_jobs = []
            for job in jobs:
                # Put jobUrl into response_data so base class uses it for URL building
                job_data = dict(job)
                job_data['url'] = job.get('jobUrl', '')

                standardized_jobs.append({
                    'id': str(job.get('id', '')),
                    'title': job.get('title', ''),
                    'location': job.get('location', ''),
                    'response_data': job_data
                })

            return standardized_jobs

        except Exception as e:
            print(f"Error fetching OpenAI jobs: {e}")
            return []

    def extract_raw_info(self, raw_content: str) -> dict:
        """
        Extract structured job details from OpenAI/Ashby job page HTML.

        Ashby job pages embed job data in JSON-LD (schema.org JobPosting).
        Description uses <strong> tags for section headers.

        Args:
            raw_content: Raw HTML string from crawl_raw_info()

        Returns:
            {'description': str, 'requirements': str}

        Raises:
            ValueError: If content cannot be parsed
        """
        if not raw_content:
            raise ValueError("No content to extract from")

        def strip_html(text: str) -> str:
            """Strip HTML tags and normalize whitespace"""
            text = re.sub(r'<br\s*/?>', '\n', text)
            text = re.sub(r'<li[^>]*>\s*<p[^>]*>', '\n- ', text)
            text = re.sub(r'</p>\s*</li>', '', text)
            text = re.sub(r'<li[^>]*>', '\n- ', text)
            text = re.sub(r'</li>', '', text)
            text = re.sub(r'<p[^>]*>', '\n', text)
            text = re.sub(r'</p>', '\n', text)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = html.unescape(text)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n +', '\n', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\n\n- ', '\n- ', text)
            return text.strip()

        # Extract description from JSON-LD JobPosting
        desc_match = re.search(
            r'"description":\s*"(.*?)"(?=,\s*")',
            raw_content,
            re.DOTALL
        )
        if not desc_match:
            raise ValueError("Could not find job description in JSON-LD")

        # Unescape JSON string escapes first, then HTML entities
        raw_desc = desc_match.group(1)
        raw_desc = raw_desc.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
        desc_html = html.unescape(raw_desc)

        description_parts = []
        requirements_parts = []

        # OpenAI/Ashby uses <strong> for section headers
        qual_patterns = [
            r'<(?:strong|b)[^>]*>\s*(?:About the Role|About the Team|About the role|About the team)\s*</(?:strong|b)>',
            r'<(?:strong|b)[^>]*>\s*(?:What you\'ll do|What You\'ll Do|Responsibilities)\s*</(?:strong|b)>',
        ]

        req_patterns = [
            r'<(?:strong|b)[^>]*>\s*You might thrive in this role if[^<]*</(?:strong|b)>',
            r'<(?:strong|b)[^>]*>\s*We[\'\u2019]re looking for[^<]*</(?:strong|b)>',
            r'<(?:strong|b)[^>]*>\s*(?:We expect you to|Qualifications?|Requirements?)\s*:?\s*</(?:strong|b)>',
            r'<(?:strong|b)[^>]*>\s*(?:What we[\'\u2019]re looking for|About you|About You|You should have)\s*:?\s*</(?:strong|b)>',
        ]

        nice_to_have_patterns = [
            r'<(?:strong|b)[^>]*>\s*(?:Nice to have|Bonus|Preferred|Nice-to-have)\s*:?\s*</(?:strong|b)>',
        ]

        end_patterns = [
            r'<(?:strong|b)[^>]*>\s*About OpenAI\s*</(?:strong|b)>',
            r'<(?:strong|b)[^>]*>\s*(?:Compensation|Benefits|Location|We offer|Our tech stack)\s*:?\s*</(?:strong|b)>',
        ]

        # Find start of requirements section
        req_start = None
        for pattern in req_patterns:
            match = re.search(pattern, desc_html, re.IGNORECASE)
            if match:
                req_start = match.start()
                break

        if req_start:
            desc_part = desc_html[:req_start]
            req_part = desc_html[req_start:]

            description_parts.append(strip_html(desc_part))

            # Find end of requirements (compensation/about section)
            req_end = len(req_part)
            for pattern in end_patterns:
                match = re.search(pattern, req_part, re.IGNORECASE)
                if match:
                    req_end = match.start()
                    break

            req_part = req_part[:req_end]

            # Check for nice-to-have within requirements
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
            # No clear requirements section
            description_parts.append(strip_html(desc_html))

        return {
            'description': '\n\n'.join(description_parts),
            'requirements': '\n\n'.join(requirements_parts),
        }
