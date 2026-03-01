# Company Extractor Prompt

Use this prompt to create a **complete job extractor** for a new company. This covers the full pipeline: source URL extraction, raw content crawling, and job info parsing.

---

## Usage

```
Read backend/extractors/EXTRACTOR_PROMPT.md and create an extractor for {company_name}
```

---

## Pipeline Overview

Each extractor implements a 3-stage pipeline:

| Stage | Method | Purpose |
|-------|--------|---------|
| 1 | `_fetch_all_jobs()` → `extract_source_urls_metadata()` | Fetch job listings, apply filters, return URLs |
| 2 | `crawl_raw_info(job_url)` | Fetch raw HTML/JSON from job page (base class, override if needed) |
| 3 | `extract_raw_info(raw_content)` | Parse description/requirements from raw content |

---

## Before You Start

### 1. Check for API Response Snapshots

Look in `backend/trials/{company}/` for saved API responses:
```
backend/trials/
├── {company}/
│   ├── {company}_api_response_snapshot.json   # Sample API response
│   └── dump_api_response.py                    # Script used to capture it
```

If snapshots exist, use them to understand the API structure. If not, you need to:
- Inspect the careers page network requests (DevTools → Network tab)
- Try common job board APIs (Greenhouse, Ashby, Lever, Workday)
- Save a sample response to `backend/trials/{company}/`

**Important:** When making any trial requests (curl, Python scripts, etc.), always use full browser headers (User-Agent, Accept, Accept-Language, etc.) to avoid being blocked by bot detection. Many career pages return 403 without browser-like headers.

### 2. Identify the API Pattern

Common patterns:

| Pattern | Example Companies | Characteristics |
|---------|-------------------|-----------------|
| REST JSON API | Amazon, Netflix, Roblox | Clean JSON, pagination via offset/page |
| Ashby | OpenAI | `api.ashbyhq.com/posting-api/job-board/{company}`, all jobs in one response |
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
| `url` | Job application URL | Built from `job_path`, `absolute_url`, `jobUrl`, or `{prefix}/{id}` |

### 4. Analyze Job Page Structure

Fetch a sample job page and look for:
- **JSON-LD** (`<script type="application/ld+json">`) — most common, contains `description` field
- **Embedded JSON** in script tags
- **HTML sections** with identifiable headers (`<strong>`, `<h2>`) for description vs requirements

---

## Required Implementation

### Class Structure

```python
"""
{Company} Job Extractor

API: {api_url}
Pattern: {pattern_type}
Pagination: {pagination_type}

Sample API Response:
{sample_response_snippet}
"""

import re
import html

from typing import List, Dict, Any
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company


class {Company}Extractor(BaseJobExtractor[TitleFilters]):
    """
    Extract job URLs from {Company} careers page

    Example:
        extractor = {Company}Extractor(config=TitleFilters())
        result = extractor.extract_source_urls_metadata()
    """
    COMPANY_NAME = Company.{COMPANY_UPPER}

    API_URL = "{api_url}"
    URL_PREFIX_JOB = "{url_prefix}"

    def __init__(self, config):
        """Initialize {Company} extractor"""
        super().__init__(config)

    def get_headers(self) -> Dict[str, str]:
        """Override with {Company}-specific headers if needed"""
        headers = super().get_headers()
        headers['Accept'] = 'application/json'
        return headers

    async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs and return standardized job objects.

        Returns:
            List of standardized job objects:
            {
                'id': str,
                'title': str,
                'location': str,
                'response_data': dict  # Must include 'url' or 'absolute_url' for URL building
            }
        """
        # Implementation here
        pass

    def extract_raw_info(self, raw_content: str) -> dict:
        """
        Extract structured job details from raw HTML content.

        Args:
            raw_content: Raw HTML string from crawl_raw_info()

        Returns:
            {'description': str, 'requirements': str}

        Raises:
            ValueError: If content cannot be parsed
        """
        # Implementation here
        pass
```

### Required Methods

| Method | Purpose | When to Override |
|--------|---------|------------------|
| `__init__` | Initialize with config | Always (call `super().__init__(config)`) |
| `_fetch_all_jobs` | Fetch and return all jobs | Always (abstract method) |
| `extract_raw_info` | Parse description/requirements | Always (abstract method) |
| `get_headers` | HTTP headers for requests | If company needs special headers |
| `crawl_raw_info` | Fetch raw job page content | Only if URL needs transformation (e.g., Netflix) |

### URL Construction

The base class handles URL construction via `_build_url_from_job()`. It checks (in order):
1. `response_data['absolute_url']` → Use as-is (e.g., Greenhouse URLs)
2. `response_data['url']` → Use as-is
3. `response_data['job_path']` → `URL_PREFIX_JOB + job_path`
4. Otherwise → `URL_PREFIX_JOB + '/' + id`

Make sure your `response_data` includes the appropriate field for URL construction.

### extract_raw_info Implementation

Most job pages embed content in **JSON-LD** (`<script type="application/ld+json">`). The description field contains HTML with section headers (`<strong>`, `<h2>`).

Parsing strategy:
1. Extract the description HTML from JSON-LD
2. Unescape JSON string escapes (`\"`, `\\n`, `\\\\`)
3. Find the requirements section boundary (look for section headers like "Qualifications", "You might thrive in this role if", etc.)
4. Split into description and requirements
5. Strip HTML tags and normalize whitespace

**Tip:** Before implementing, fetch 3-5 sample job pages to identify the common section header patterns for the company. Watch out for smart quotes (`'` U+2019 vs `'`) in header text.

---

## Registry Integration

After creating the extractor, add it to two files:

**`extractors/enums.py`:**
```python
class Company(str, Enum):
    {COMPANY_UPPER} = "{company}"
    # ... other companies
```

**`extractors/registry.py`:**
```python
from .{company} import {Company}Extractor

COMPANY_REGISTRY = {
    Company.{COMPANY_UPPER}: {Company}Extractor,
    # ... other extractors
}
```

---

## Common Patterns

### Single Response / No Pagination (Roblox, OpenAI)

```python
async def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
    response = await self.make_request(self.API_URL, timeout=15.0)
    data = response.json()
    jobs = data.get('jobs', [])

    return [
        {
            'id': str(job['id']),
            'title': job['title'],
            'location': job.get('location', ''),
            'response_data': job
        }
        for job in jobs
    ]
```

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
            break

        all_jobs.extend(new_jobs)
        seen_ids.update(j['id'] for j in new_jobs)
        page += 1

    return all_jobs
```

### JSON-LD Extraction (Netflix, OpenAI/Ashby)

```python
def extract_raw_info(self, raw_content: str) -> dict:
    if not raw_content:
        raise ValueError("No content to extract from")

    def strip_html(text: str) -> str:
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

    # Extract from JSON-LD
    desc_match = re.search(r'"description":\s*"(.*?)"(?=,\s*")', raw_content, re.DOTALL)
    if not desc_match:
        raise ValueError("Could not find job description in JSON-LD")

    raw_desc = desc_match.group(1)
    raw_desc = raw_desc.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
    desc_html = html.unescape(raw_desc)

    # Find requirements section and split
    # ... company-specific section header patterns ...
```

---

## Validation (Required)

After implementing the extractor and registering it, you **must** run the following validation steps. All results are saved to `backend/trials/{company}/` for inspection.

### Step 1: Validate `extract_source_urls_metadata()`

```bash
cd backend
python3 -c "
import asyncio, json
from extractors.registry import get_extractor
from extractors.config import TitleFilters

async def main():
    extractor = get_extractor('{company}', config=TitleFilters())
    result = await extractor.extract_source_urls_metadata()

    print(f'Total jobs from API: {result[\"total_count\"]}')
    print(f'Included (passed filter): {result[\"urls_count\"]}')
    print(f'Excluded (filtered out): {result[\"filtered_count\"]}')
    print()
    print('Sample included jobs:')
    for job in result['included_jobs'][:5]:
        print(f'  {job[\"title\"]} | {job[\"location\"]} | {job[\"url\"]}')

    # Save result summary (without full job lists for readability)
    summary = {
        'total_count': result['total_count'],
        'urls_count': result['urls_count'],
        'filtered_count': result['filtered_count'],
        'sample_included': result['included_jobs'][:5],
        'sample_excluded': result['excluded_jobs'][:5],
    }
    with open('trials/{company}/{company}_source_urls_result.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f'\nSaved to trials/{company}/{company}_source_urls_result.json')

asyncio.run(main())
"
```

**Expected**: Non-zero `total_count`, valid URLs, correct job titles.

### Step 2: Validate `crawl_raw_info()` + `extract_raw_info()`

```bash
cd backend
python3 -c "
import asyncio, json
from extractors.registry import get_extractor
from extractors.config import TitleFilters

async def main():
    extractor = get_extractor('{company}', config=TitleFilters())
    result = await extractor.extract_source_urls_metadata()
    job = result['included_jobs'][0]
    url = job['url']

    print(f'Testing job: {job[\"title\"]}')
    print(f'URL: {url}')
    print()

    # Crawl raw content
    raw = await extractor.crawl_raw_info(url)
    print(f'Raw content: {len(raw)} chars')

    # Save raw HTML
    with open('trials/{company}/{company}_sample_raw.html', 'w') as f:
        f.write(raw)
    print(f'Saved raw HTML to trials/{company}/{company}_sample_raw.html')
    print()

    # Extract structured info
    info = extractor.extract_raw_info(raw)
    print(f'Description: {len(info[\"description\"])} chars')
    print(f'Requirements: {len(info[\"requirements\"])} chars')
    print()
    print('--- Description (first 300 chars) ---')
    print(info['description'][:300])
    print()
    print('--- Requirements (first 300 chars) ---')
    print(info['requirements'][:300])

    # Save extracted result
    extracted = {
        'url': url,
        'title': job['title'],
        'description': info['description'],
        'requirements': info['requirements'],
    }
    with open('trials/{company}/{company}_extracted_sample.json', 'w') as f:
        json.dump(extracted, f, indent=2)
    print(f'\nSaved to trials/{company}/{company}_extracted_sample.json')

asyncio.run(main())
"
```

**Expected**: Both `description` and `requirements` should be non-empty with meaningful content.

### Validation Checklist

- [ ] `extract_source_urls_metadata()` returns non-zero `total_count`
- [ ] Job URLs are valid and accessible
- [ ] `extract_raw_info()` returns non-empty `description`
- [ ] `extract_raw_info()` returns non-empty `requirements`
- [ ] Results saved to `backend/trials/{company}/`:
  - `{company}_source_urls_result.json`
  - `{company}_sample_raw.html`
  - `{company}_extracted_sample.json`

---

## Full Checklist

### Implementation
- [ ] Class inherits from `BaseJobExtractor[TitleFilters]`
- [ ] `COMPANY_NAME`, `API_URL`, `URL_PREFIX_JOB` class variables set
- [ ] `_fetch_all_jobs()` returns standardized format with `id`, `title`, `location`, `response_data`
- [ ] `id` field is a string (not int)
- [ ] Pagination handles all results (not just first page)
- [ ] `extract_raw_info()` parses description and requirements from raw HTML
- [ ] Hardcoded filters are documented in docstring
- [ ] Added to `registry.py` and `enums.py`

### Validation
- [ ] Step 1 passed: source URLs extracted successfully
- [ ] Step 2 passed: raw info extracted with non-empty description and requirements
- [ ] All trial outputs saved to `backend/trials/{company}/`
