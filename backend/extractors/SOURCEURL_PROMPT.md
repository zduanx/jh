# Source URL Extractor Prompt

Use this prompt to generate or update a **source URL extractor** for a new company. This extractor fetches job listings from career page APIs and returns job metadata (id, title, location, url).

For raw info crawling and extraction, see `CRAWL_PROMPT.md` and `EXTRACT_PROMPT.md`.

---

## Usage

```
Read backend/extractors/SOURCEURL_PROMPT.md and create a source URL extractor for {company_name}
```

---

## Context

The extractor system fetches job listings from company career pages. Each extractor:
1. Queries the company's career API/page
2. Extracts job metadata (id, title, location, url)
3. Applies title filtering (include/exclude terms)
4. Returns standardized job objects

---

## Before You Start

### 1. Check for API Response Snapshots

Look in `trials/{company}/` for saved API responses:
```
trials/
├── {company}/
│   ├── {company}_api_response_snapshot.json   # Sample API response
│   └── dump_api_response.py                    # Script used to capture it
```

If snapshots exist, use them to understand the API structure. If not, you may need to:
- Inspect the careers page network requests (DevTools → Network tab)
- Save a sample response to `trials/{company}/`

### 2. Identify the API Pattern

Common patterns:

| Pattern | Example Companies | Characteristics |
|---------|-------------------|-----------------|
| REST JSON API | Amazon, Netflix, Roblox | Clean JSON, pagination via offset/page |
| GraphQL | TikTok | Query-based, nested response structure |
| HTML + JavaScript | Google | Jobs embedded in script tags, regex extraction |
| RSC (React Server Components) | Anthropic | Jobs in `__next_f.push()` calls |

### 3. Identify Key Fields

Map company-specific fields to our standard format:

| Standard Field | Purpose | Example Variations |
|----------------|---------|-------------------|
| `id` | Unique job identifier | `id`, `job_id`, `id_icims`, `requisitionId` |
| `title` | Job title for filtering | `title`, `name`, `jobTitle` |
| `location` | Job location | `location`, `office`, `city`, `locations[0].name` |
| `url` | Job application URL | Built from `job_path`, `absolute_url`, or `{prefix}/{id}` |

---

## Required Implementation

### Class Structure

```python
"""
{Company} Job URL Extractor

API: {api_url}
Pattern: {pattern_type}
Pagination: {pagination_type}

Note: {any_quirks_or_special_handling}

Sample API Response:
{sample_response_snippet}
"""

from typing import List, Dict, Any
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class {Company}Extractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from {Company} careers page

    Example:
        extractor = {Company}Extractor()
        urls = extractor.extract_source_urls_metadata()
    """
    COMPANY_NAME = Company.{COMPANY_UPPER}

    API_URL = "{api_url}"
    URL_PREFIX_JOB = "{url_prefix}"

    def __init__(self, config):
        """Initialize {Company} extractor"""
        super().__init__(config)

    def get_headers(self) -> Dict[str, str]:
        """Override with {Company}-specific headers if needed"""
        return {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
            # Add company-specific headers
        }

    def _build_params(self, ...) -> Dict[str, Any]:
        """Build query parameters with hardcoded filters"""
        params = {
            # Hardcoded search filters (employment type, location, etc.)
        }
        return params

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs (implement pagination if needed)

        Returns:
            List of standardized job objects:
            {
                'id': str,
                'title': str,
                'location': str,
                'response_data': dict  # Original API response for this job
            }
        """
        # Implementation here
        pass
```

### Required Methods

| Method | Purpose | When to Override |
|--------|---------|------------------|
| `__init__` | Initialize with config | Always (call `super().__init__(config)`) |
| `_fetch_all_jobs` | Fetch and return all jobs | Always (abstract method) |
| `get_headers` | HTTP headers for requests | If company needs special headers |
| `_build_params` | Query parameters | If API supports query params |

### URL Construction

The base class handles URL construction via `_build_url_from_job()`. It checks (in order):
1. `response_data['absolute_url']` → Use as-is (e.g., Greenhouse URLs)
2. `response_data['url']` → Use as-is
3. `response_data['job_path']` → `URL_PREFIX_JOB + job_path`
4. Otherwise → `URL_PREFIX_JOB + '/' + id`

Make sure your `response_data` includes the appropriate field for URL construction.

---

## Registry Integration

After creating the extractor, add it to `extractors/registry.py`:

```python
from .{company} import {Company}Extractor

EXTRACTORS = {
    Company.{COMPANY_UPPER}: {Company}Extractor,
    # ... other extractors
}
```

And add the company to `extractors/enums.py`:

```python
class Company(str, Enum):
    {COMPANY_UPPER} = "{company}"
    # ... other companies
```

---

## Common Patterns

### Offset-Based Pagination (Amazon, Netflix)

```python
async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
    BATCH_SIZE = 100
    all_jobs = []
    offset = 0

    # First call to get total
    jobs, total = await self._fetch_jobs_page(offset=0, result_limit=BATCH_SIZE)
    all_jobs.extend(self._standardize_jobs(jobs))
    offset = len(jobs)

    # Fetch remaining
    while offset < total:
        jobs, _ = await self._fetch_jobs_page(offset=offset, result_limit=BATCH_SIZE)
        if not jobs:
            break
        all_jobs.extend(self._standardize_jobs(jobs))
        offset += len(jobs)

    return all_jobs
```

### Page-Based Pagination (Google)

```python
async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
    all_jobs = []
    seen_ids = set()
    page = 1

    while True:
        jobs = await self._fetch_jobs_page(page)
        if not jobs:
            break

        new_jobs = [j for j in jobs if j['id'] not in seen_ids]
        if not new_jobs:
            break  # No new jobs = end of pagination

        all_jobs.extend(new_jobs)
        seen_ids.update(j['id'] for j in new_jobs)
        page += 1

    return all_jobs
```

### HTML/JavaScript Extraction (Google, Anthropic)

```python
async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
    response = await self.make_request(self.API_URL)
    html = response.text

    # Extract embedded data using regex
    pattern = r'...'  # Company-specific pattern
    matches = re.findall(pattern, html)

    jobs = []
    for match in matches:
        jobs.append({
            'id': ...,
            'title': ...,
            'location': ...,
            'response_data': {...}
        })

    return jobs
```

---

## Checklist

Before submitting the extractor:

- [ ] Class inherits from `BaseJobExtractor[TitleFilters]`
- [ ] `COMPANY_NAME`, `API_URL`, `URL_PREFIX_JOB` class variables set
- [ ] `_fetch_all_jobs()` returns standardized format with `id`, `title`, `location`, `response_data`
- [ ] `id` field is a string (not int)
- [ ] Pagination handles all results (not just first page)
- [ ] Hardcoded filters are documented in docstring
- [ ] Added to `registry.py` and `enums.py`
- [ ] Tested with: `python -c "from extractors import get_extractor; ..."`

---

## Example: Minimal Extractor

```python
"""
Acme Job URL Extractor

API: https://api.acme.com/careers/jobs
Pattern: REST JSON API
Pagination: Offset-based (offset, limit params)
"""

from typing import List, Dict, Any
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class AcmeExtractor(BaseJobExtractor[TitleFilters]):
    COMPANY_NAME = Company.ACME
    API_URL = "https://api.acme.com/careers/jobs"
    URL_PREFIX_JOB = "https://www.acme.com/careers/jobs"

    def __init__(self, config):
        super().__init__(config)

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        response = await self.make_request(self.API_URL, params={'limit': 100})
        data = response.json()

        return [
            {
                'id': str(job['id']),
                'title': job['title'],
                'location': job.get('location', ''),
                'response_data': job
            }
            for job in data.get('jobs', [])
        ]
```
