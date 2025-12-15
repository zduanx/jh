"""
Anthropic Job URL Extractor

Pattern: Server-Side Rendering (SSR) with React Server Components (RSC)
Data format: JSON embedded in HTML via __next_f.push() calls
Structure: Office/Location → Department/Team → Jobs

Note: Anthropic uses absolute_url field from API response (full Greenhouse URL),
not a hardcoded prefix.

Sample RSC Data Structure:
{
  "id": 4001218008,
  "name": "San Francisco, CA",
  "departments": [
    {
      "id": 4019632008,
      "name": "Software Engineering - Infrastructure",
      "jobs": [
        {
          "id": 123456,
          "title": "Software Engineer",
          "absolute_url": "https://boards.greenhouse.io/anthropic/jobs/123456"
        }
      ]
    }
  ]
}
"""

from typing import List, Dict, Any
import re
import json
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class AnthropicExtractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from Anthropic careers page

    Example:
        extractor = AnthropicExtractor()
        urls = extractor.extract_source_urls_metadata()

    Note: Anthropic returns absolute_url in API response (Greenhouse URLs),
          so URL_PREFIX_JOB is not used for URL construction.
    """
    COMPANY_NAME = Company.ANTHROPIC

    API_URL = "https://www.anthropic.com/jobs"
    URL_PREFIX_JOB = "https://boards.greenhouse.io/anthropic/jobs"  # Not used, URLs come from API

    def __init__(self, config):
        """Initialize Anthropic extractor"""
        super().__init__(config)

    def _build_url(self) -> str:
        """
        Build URL for Anthropic jobs page

        Note: URL parameters don't filter server-side. Anthropic always returns
        all jobs regardless of query parameters. Filtering is done client-side.

        Returns:
            Base URL without query parameters
        """
        return self.API_URL

    def _extract_rsc_payload(self, html: str) -> str:
        """
        Extract RSC (React Server Components) payload from HTML

        Args:
            html: HTML response

        Returns:
            RSC data string (or None if not found)
        """
        pushes = re.findall(r'self\.__next_f\.push\((.*?)\)(?:</script>|;)', html, re.DOTALL)

        for push in pushes:
            if 'greenhouse.io/anthropic/jobs' in push:
                try:
                    data = json.loads(push)
                    if len(data) >= 2:
                        return data[1]  # The actual data string
                except:
                    continue

        return None

    def _parse_offices(self, rsc_data: str) -> List[Dict]:
        """
        Parse office objects from RSC data

        Args:
            rsc_data: RSC payload string

        Returns:
            List of office objects with structure:
            {
              "id": office_id,
              "name": "San Francisco, CA",
              "departments": [
                {
                  "id": dept_id,
                  "name": "Software Engineering",
                  "jobs": [{"id": ..., "title": ..., "absolute_url": ...}]
                }
              ]
            }
        """
        offices = []

        # Find all office objects
        pattern = r'"id":(\d+),"name":"([^"]+)","departments":\['
        matches = list(re.finditer(pattern, rsc_data))

        for i, match in enumerate(matches):
            office_id = int(match.group(1))
            office_name = match.group(2)

            # Find start of this office's JSON
            start_pos = match.start() - 1
            while start_pos > 0 and rsc_data[start_pos] != '{':
                start_pos -= 1

            # Find end using bracket matching
            if i < len(matches) - 1:
                next_office_start = matches[i+1].start() - 1
                while next_office_start > 0 and rsc_data[next_office_start] != '{':
                    next_office_start -= 1
                end_pos = next_office_start
            else:
                end_pos = len(rsc_data)

            office_chunk = rsc_data[start_pos:end_pos]

            # Use bracket matching to find exact end
            depth = 0
            actual_end = 0
            for j, char in enumerate(office_chunk):
                if char in '{[':
                    depth += 1
                elif char in '}]':
                    depth -= 1
                    if depth == 0:
                        actual_end = j + 1
                        break

            office_json = office_chunk[:actual_end]

            try:
                office_obj = json.loads(office_json)
                offices.append(office_obj)
            except:
                continue

        return offices

    def _filter_jobs(
        self,
        offices: List[Dict],
        team_ids: List[int] = None,
        office_ids: List[int] = None,
        unique_titles: bool = True
    ) -> List[Dict]:
        """
        Filter jobs by team and office

        Args:
            offices: List of office objects
            team_ids: Team/department IDs to filter by (None = all teams)
            office_ids: Office IDs to filter by (None = all offices)
            unique_titles: If True, deduplicate by job ID (same job in multiple locations)

        Returns:
            List of job objects with 'id', 'title', 'url', 'office', 'department'

        Note: When the same job ID appears in multiple offices, locations are
              concatenated (e.g., "San Francisco, CA; New York City, NY")
        """
        from collections import defaultdict

        # Collect all job entries (may have duplicates across offices)
        all_job_entries = []

        for office in offices:
            office_id = office['id']
            office_name = office['name']

            # Filter by office
            if office_ids and office_id not in office_ids:
                continue

            for dept in office.get('departments', []):
                dept_id = dept.get('id')
                dept_name = dept.get('name')

                # Filter by team
                if team_ids and dept_id not in team_ids:
                    continue

                for job in dept.get('jobs', []):
                    all_job_entries.append({
                        'id': job.get('id'),
                        'title': job.get('title'),
                        'url': job.get('absolute_url'),
                        'office': office_name,
                        'office_id': office_id,
                        'department': dept_name,
                        'department_id': dept_id
                    })

        # Deduplicate by job ID and aggregate locations
        if unique_titles:
            jobs_by_id = defaultdict(list)
            for entry in all_job_entries:
                jobs_by_id[entry['id']].append(entry)

            results = []
            for job_id, entries in jobs_by_id.items():
                # Use first entry as base
                job = entries[0].copy()

                # If job appears in multiple locations, concatenate them
                if len(entries) > 1:
                    unique_offices = []
                    seen = set()
                    for entry in entries:
                        if entry['office'] not in seen:
                            unique_offices.append(entry['office'])
                            seen.add(entry['office'])
                    job['office'] = '; '.join(unique_offices)

                results.append(job)
        else:
            results = all_job_entries

        return results

    def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs from Anthropic careers page

        Returns:
            List of job objects with standardized structure:
            {
                'id': str,
                'title': str,
                'response_data': dict  # Contains absolute_url, office, department, etc.
            }
        """
        # Hardcoded filters for Anthropic
        TEAM_IDS = [4019632008, 4050633008]
        OFFICE_IDS = [4001218008, 4001219008, 4001217008]
        UNIQUE_TITLES = True

        # Build URL (note: URL params don't filter server-side, we filter client-side)
        url = self._build_url()

        try:
            # Fetch page
            response = self.make_request(url, timeout=10)

            # Extract RSC payload
            rsc_data = self._extract_rsc_payload(response.text)
            if not rsc_data:
                print("Could not extract RSC payload from Anthropic page")
                return []

            # Parse offices
            offices = self._parse_offices(rsc_data)
            if not offices:
                print("Could not parse offices from RSC data")
                return []

            # Filter jobs by team and office (client-side filtering)
            jobs = self._filter_jobs(offices, TEAM_IDS, OFFICE_IDS, UNIQUE_TITLES)

            # Convert to standardized format
            standardized_jobs = []
            for job in jobs:
                standardized_job = {
                    'id': str(job.get('id', '')),
                    'title': job.get('title', ''),
                    'location': job.get('office', ''),  # Anthropic uses 'office' field for location
                    'response_data': job  # Contains absolute_url, office, department, etc.
                }
                standardized_jobs.append(standardized_job)

            return standardized_jobs

        except Exception as e:
            print(f"Error extracting Anthropic jobs: {e}")
            return []
