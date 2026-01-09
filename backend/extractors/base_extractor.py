"""
Base extractor class for job extraction pipeline

This module provides the abstract base class that all company-specific
extractors must implement. The pipeline has three stages:

1. Source URL extraction: Fetch job listings from career page APIs
2. Raw info crawling: Fetch full job page content (generic, in base class)
3. Raw info extraction: Parse description/requirements (company-specific, abstract)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic, TYPE_CHECKING
import httpx

if TYPE_CHECKING:
    from .enums import Company

# Generic type for config
ConfigType = TypeVar('ConfigType')


class BaseJobExtractor(ABC, Generic[ConfigType]):
    """
    Abstract base class for job URL extractors

    Architecture:
    - Each company implements _fetch_all_jobs() to return standardized job objects
    - Base class handles title filtering and URL construction uniformly
    - This is Phase 1 of the pipeline: URL extraction only

    Each company extractor must define:
    1. API_URL: The API endpoint or base URL for the company's careers page
    2. URL_PREFIX_JOB: The URL prefix for constructing individual job URLs
    3. COMPANY_NAME: Company enum value (e.g., Company.GOOGLE)
    4. _fetch_all_jobs(): Method to fetch and extract job objects
    5. extract_raw_info(): Method to parse description/requirements from raw content

    Title filtering configuration is always passed externally via __init__(config=...)

    Pipeline stages:
    - Stage 1: extract_source_urls_metadata() → job list with URLs
    - Stage 2: crawl_raw_info(url) → raw HTML/JSON content (generic, in base class)
    - Stage 3: extract_raw_info(raw_content) → {description, requirements} (abstract)
    """

    # Abstract class variables - must be defined by each concrete extractor
    API_URL: str
    URL_PREFIX_JOB: str
    COMPANY_NAME: 'Company'  # Must be set to Company enum value in concrete classes

    def __init__(self, config: ConfigType):
        """
        Initialize extractor with configuration

        Args:
            config: Title filtering configuration (TitleFilters).
                   Must be provided externally (no defaults).

        Each concrete extractor defines these as class variables:
        - API_URL: Endpoint for fetching jobs
        - URL_PREFIX_JOB: Prefix for building job URLs

        Example:
            # With filtering
            filters = TitleFilters(exclude=['senior staff'])
            extractor = GoogleExtractor(config=filters)

            # No filtering
            extractor = GoogleExtractor(config=TitleFilters())
        """
        # Verify that subclass defined required class variables
        required_vars = ['API_URL', 'URL_PREFIX_JOB', 'COMPANY_NAME']
        for var in required_vars:
            if not hasattr(self.__class__, var):
                raise NotImplementedError(
                    f"{self.__class__.__name__} must define {var} class variable"
                )

        # Always use provided config
        self.config = config

    @abstractmethod
    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs and return standardized job objects

        Each company implements this method to:
        1. Make API/HTTP requests to fetch jobs
        2. Extract job data from responses
        3. Return standardized job objects

        Implementation notes:
        - Handle pagination if necessary
        - Apply API-level filters (employment type, location, etc.)
        - Extract id, title, and response_data for each job
        - Handle errors gracefully (return empty list on failure)

        Returns:
            List of job objects, each with structure:
            {
                'id': str,              # Job ID for URL construction
                'title': str,           # Job title for filtering
                'location': str,        # Job location (city, state, country)
                'response_data': Any    # Raw response data (dict, str, etc.)
            }

            Example: [
                {
                    'id': '123456',
                    'title': 'Software Engineer',
                    'location': 'New York, NY, USA',
                    'response_data': {'location': 'NYC', 'department': 'Eng', ...}
                },
                ...
            ]

        Raises:
            This method should handle exceptions internally and return empty list
            on failure. Optionally, can raise exceptions for caller to handle.
        """
        pass

    async def extract_source_urls_metadata(self) -> Dict[str, Any]:
        """
        Extract job URLs with full metadata (included and excluded jobs)

        Returns:
            Dictionary with structure:
            {
                'total_count': int,              # Total jobs from API
                'filtered_count': int,           # Jobs filtered OUT
                'urls_count': int,               # Jobs included (passed filter)
                'included_jobs': [               # Jobs that passed filter
                    {'id': str, 'title': str, 'location': str, 'url': str},
                    ...
                ],
                'excluded_jobs': [               # Jobs that were filtered out
                    {'id': str, 'title': str, 'location': str, 'url': str},
                    ...
                ]
            }
        """
        # Step 1: Fetch all jobs
        all_jobs = await self._fetch_all_jobs()
        total_count = len(all_jobs)

        if not all_jobs:
            return {
                'total_count': 0,
                'filtered_count': 0,
                'urls_count': 0,
                'included_jobs': [],
                'excluded_jobs': []
            }

        # Step 2: Apply title filtering and separate included/excluded
        included_jobs = self._apply_title_filters(all_jobs)

        # Find excluded jobs (those that didn't pass filter)
        included_ids = {job.get('id') for job in included_jobs}
        excluded_jobs = [job for job in all_jobs if job.get('id') not in included_ids]

        # Step 3: Build metadata for included jobs
        included_metadata = []
        for job in included_jobs:
            url = self._build_url_from_job(job)
            if url:  # Only include if URL was successfully built
                included_metadata.append({
                    'id': str(job.get('id', '')),  # Convert to string
                    'title': job.get('title', ''),
                    'location': job.get('location', ''),
                    'url': url
                })

        # Step 4: Build metadata for excluded jobs
        excluded_metadata = []
        for job in excluded_jobs:
            url = self._build_url_from_job(job)
            if url:  # Only include if URL can be built
                excluded_metadata.append({
                    'id': str(job.get('id', '')),  # Convert to string
                    'title': job.get('title', ''),
                    'location': job.get('location', ''),
                    'url': url
                })

        return {
            'total_count': total_count,
            'filtered_count': len(excluded_jobs),
            'urls_count': len(included_metadata),
            'included_jobs': included_metadata,
            'excluded_jobs': excluded_metadata
        }

    async def crawl_raw_info(self, job_url: str) -> str:
        """
        Fetch raw content from a job page URL (Stage 2 of pipeline).

        This is a generic implementation that works for most companies.
        Override in concrete extractors if company needs special handling
        (e.g., different headers, API endpoints, or JavaScript parsing).

        Args:
            job_url: Full URL to the job posting page

        Returns:
            Raw content as string (HTML or JSON text)

        Raises:
            Exception: On HTTP errors or connection failures
        """
        response = await self.make_request(
            job_url,
            timeout=15.0  # Longer timeout for full page
        )
        return response.text

    @abstractmethod
    def extract_raw_info(self, raw_content: str) -> Dict[str, str]:
        """
        Extract structured job details from raw content (Stage 3 of pipeline).

        Each company must implement this method with company-specific parsing logic.

        Args:
            raw_content: Raw HTML/JSON string from crawl_raw_info()

        Returns:
            {
                'description': str,      # Job description text
                'requirements': str,     # Job requirements/qualifications
            }

        Raises:
            ValueError: If content cannot be parsed

        Note:
            Fields match Job model schema (description, requirements as Text columns).
        """
        pass

    def _apply_title_filters(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply title filtering to job objects

        Args:
            jobs: List of job objects with 'title' field

        Returns:
            Filtered list of job objects
        """
        if not jobs:
            return []

        # Extract titles
        titles = [job.get('title', '') for job in jobs]

        # Use base class filter_by_title method
        matches = self.filter_by_title(
            titles,
            include_terms=self.config.include,
            exclude_terms=self.config.exclude
        )

        # Return only matching jobs
        return [job for job, match in zip(jobs, matches) if match]

    def _build_url_from_job(self, job: Dict[str, Any]) -> str:
        """
        Build URL from a single job object

        Args:
            job: Job object with 'id' and 'response_data'

        Returns:
            Job URL string, or empty string if URL cannot be built
        """
        job_id = job.get('id')
        response_data = job.get('response_data', {})

        # Case 1: Pre-built full URL in response_data
        if isinstance(response_data, dict):
            # Check for absolute_url (Anthropic/Greenhouse)
            if 'absolute_url' in response_data:
                return response_data['absolute_url']
            # Check for url field
            elif 'url' in response_data:
                return response_data['url']
            # Check for job_path (Amazon)
            elif 'job_path' in response_data:
                return f"{self.URL_PREFIX_JOB}{response_data['job_path']}"

        # Case 2: Construct URL from prefix + id
        if job_id:
            return f"{self.URL_PREFIX_JOB}/{job_id}"

        return ''

    def _build_urls_from_jobs(self, jobs: List[Dict[str, Any]]) -> List[str]:
        """
        Build URLs from job objects

        Handles multiple cases:
        1. If response_data contains 'absolute_url', use that (e.g., Anthropic)
        2. If response_data contains 'url', use that
        3. If response_data contains 'job_path', use URL_PREFIX_JOB + job_path (e.g., Amazon)
        4. Otherwise, construct URL from URL_PREFIX_JOB + id

        Args:
            jobs: List of job objects

        Returns:
            List of job URLs
        """
        urls = []

        for job in jobs:
            job_id = job.get('id')
            response_data = job.get('response_data', {})

            # Case 1: Pre-built full URL in response_data
            if isinstance(response_data, dict):
                # Check for absolute_url (Anthropic/Greenhouse)
                if 'absolute_url' in response_data:
                    urls.append(response_data['absolute_url'])
                    continue
                # Check for url field
                elif 'url' in response_data:
                    urls.append(response_data['url'])
                    continue
                # Check for job_path (Amazon)
                elif 'job_path' in response_data:
                    urls.append(f"{self.URL_PREFIX_JOB}{response_data['job_path']}")
                    continue

            # Case 2: Construct URL from prefix + id
            if job_id:
                urls.append(f"{self.URL_PREFIX_JOB}/{job_id}")

        return urls

    def get_headers(self) -> Dict[str, str]:
        """
        Get default HTTP headers for requests

        Override this method if company needs specific headers.

        Returns:
            Dict of HTTP headers
        """
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/141.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    async def make_request(
        self,
        url: str,
        method: str = 'GET',
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: float = 10.0
    ) -> httpx.Response:
        """
        Helper method to make HTTP requests with consistent error handling

        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            json: JSON body (for POST requests)
            headers: Additional headers (merged with default headers)
            timeout: Request timeout in seconds

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPStatusError: On HTTP error responses
            httpx.TimeoutException: On request timeout
            httpx.ConnectError: On connection failure
        """
        request_headers = self.get_headers()
        if headers:
            request_headers.update(headers)

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=request_headers,
                timeout=timeout
            )
            response.raise_for_status()
            return response

    def filter_by_title(
        self,
        titles: List[str],
        include_terms: Optional[List[str]] = None,
        exclude_terms: Optional[List[str]] = None
    ) -> List[bool]:
        """
        Helper method to filter job titles

        Args:
            titles: List of job titles
            include_terms: Terms that must be present (OR logic).
                          None = include all (no restriction)
            exclude_terms: Terms that must NOT be present (AND logic)

        Returns:
            List of booleans indicating which titles match filters

        Example:
            titles = ["Software Engineer", "Senior Staff Engineer", "Intern"]
            include_terms = None  # Include all
            exclude_terms = ["senior staff", "intern"]

            Returns: [True, False, False]
        """
        exclude_terms = exclude_terms or []

        results = []
        for title in titles:
            if not title:
                results.append(False)
                continue

            title_lower = title.lower()

            # Check exclude list first (if excluded, reject immediately)
            excluded = False
            for term in exclude_terms:
                if term.lower() in title_lower:
                    excluded = True
                    break

            if excluded:
                results.append(False)
                continue

            # Check include list (OR logic - must match at least one)
            if include_terms is not None:
                # Explicit include filter (not None)
                included = False
                for term in include_terms:
                    if term.lower() in title_lower:
                        included = True
                        break
                results.append(included)
            else:
                # None means include all (that weren't excluded)
                results.append(True)

        return results

    def __repr__(self) -> str:
        """String representation of extractor"""
        return f"{self.__class__.__name__}(company={self.COMPANY_NAME}, config={self.config})"
