# Job URL Extractors

This directory contains production-ready job URL extractors for 6 companies.

## Structure

```
extractors/
├── __init__.py           # Package exports
├── base_extractor.py     # Abstract base class
├── config.py             # TitleFilters Pydantic model
├── enums.py              # Company enum
├── registry.py           # Extractor registry + helper functions
├── google.py             # Google Careers ✅
├── amazon.py             # Amazon Jobs ✅
├── anthropic.py          # Anthropic ✅
├── tiktok.py             # TikTok ✅
├── roblox.py             # Roblox ✅
└── netflix.py            # Netflix ✅
```

## Quick Start

### Using the Registry (Recommended)

```python
from extractors import get_extractor, Company, list_companies
from extractors.config import TitleFilters

# Configure filters
filters = TitleFilters(
    include=['software', 'engineer'],
    exclude=['senior staff', 'principal']
)

# Get extractor by enum
extractor = get_extractor(Company.GOOGLE, config=filters)

# Or by string
extractor = get_extractor('google', config=filters)

# Extract job metadata
result = extractor.extract_source_urls_metadata()

print(f"Total jobs: {result['total_count']}")
print(f"Filtered out: {result['filtered_count']}")
print(f"URLs extracted: {result['urls_count']}")

# Access job metadata (included jobs)
for job in result['included_jobs']:
    print(f"{job['title']} - {job['location']}")
    print(f"  URL: {job['url']}")
```

### Direct Import

```python
from extractors.google import GoogleExtractor
from extractors.config import TitleFilters

filters = TitleFilters(exclude=['senior staff'])
extractor = GoogleExtractor(config=filters)
result = extractor.extract_source_urls_metadata()
```

## Implementing a New Extractor

### 1. Check for API Response Snapshots

**IMPORTANT**: Before implementing, check `/trials/{company}/` for API response snapshots to understand the actual API structure.

Common issues caught by snapshots:
- Amazon has TWO id fields (`id` = UUID, `id_icims` = job number for URLs)
- TikTok has nested `city_info` structure (not flat `location`)
- Anthropic uses `office` field (not `location`)

### 2. Create Extractor File

Create `src/extractors/{company}.py`:

```python
from typing import List, Dict, Any
from extractors.base_extractor import BaseJobExtractor
from extractors.enums import Company
from extractors.config import TitleFilters

class NewCompanyExtractor(BaseJobExtractor[TitleFilters]):
    """Extract job URLs from NewCompany Careers"""

    # Required class variables
    API_URL = "https://api.newcompany.com/jobs"
    URL_PREFIX_JOB = "https://newcompany.com/careers/"
    COMPANY_NAME = Company.NEWCOMPANY  # Must be enum value

    def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch all jobs from API and return standardized format

        Returns list of dicts with required keys:
            - id: str
            - title: str
            - location: str
            - url: str (optional, will be built from URL_PREFIX_JOB + id)
            - response_data: dict (original API response)
        """
        all_jobs = []
        page = 1

        while True:
            # 1. Make API request
            params = {'page': page, 'limit': 100}
            response = self._make_request(
                self.API_URL,
                method='GET',
                params=params,
                headers={'User-Agent': 'JobHunter/1.0'}
            )

            jobs = response.get('jobs', [])
            if not jobs:
                break

            # 2. Convert to standardized format
            for job in jobs:
                standardized_job = {
                    'id': str(job.get('id', '')),
                    'title': job.get('title', ''),
                    'location': job.get('location', ''),
                    'url': f"{self.URL_PREFIX_JOB}{job.get('id')}",
                    'response_data': job  # Keep original for debugging
                }
                all_jobs.append(standardized_job)

            page += 1

        return all_jobs
```

### 3. Register in Registry

Add to files:

**enums.py:**
```python
class Company(str, Enum):
    # ... existing companies ...
    NEWCOMPANY = "newcompany"
```

**registry.py:**
```python
from .newcompany import NewCompanyExtractor

COMPANY_REGISTRY: Dict[Company, Type[BaseJobExtractor]] = {
    # ... existing mappings ...
    Company.NEWCOMPANY: NewCompanyExtractor,
}
```

### 4. Company-Specific Examples

#### Amazon - Dual ID Fields

```python
# Amazon has two ID fields in API response:
# - 'id': UUID (e.g., "d42a7446-bd11-40ed-9e72-425214f6d55a")
# - 'id_icims': Job number used in URLs (e.g., "3142524")

standardized_job = {
    'id': str(job.get('id_icims', '')),  # Use id_icims, not id!
    'title': job.get('title', ''),
    'location': job.get('location', ''),
    'response_data': job
}
```

#### TikTok - Nested Location

```python
def _build_location_from_city_info(self, city_info: Dict[str, Any]) -> str:
    """
    TikTok has nested city_info structure:
    {
      "en_name": "San Jose",
      "parent": {
        "en_name": "California",
        "parent": {
          "en_name": "United States"
        }
      }
    }
    We want: "San Jose, California" (city, state only)
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

    return ', '.join(parts)

# Usage:
location = self._build_location_from_city_info(job.get('city_info', {}))
```

#### Anthropic - Location Aggregation

```python
# Anthropic API returns same job ID in multiple office locations
# We need to deduplicate by ID and aggregate locations

from collections import defaultdict

# Collect all job entries
all_job_entries = []
for office in offices:
    for dept in office.get('departments', []):
        for job in dept.get('jobs', []):
            all_job_entries.append({
                'id': job.get('id'),
                'title': job.get('title'),
                'office': office.get('name', ''),  # Note: 'office' not 'location'
                'url': job.get('absolute_url'),
            })

# Deduplicate by job ID and aggregate locations
jobs_by_id = defaultdict(list)
for entry in all_job_entries:
    jobs_by_id[entry['id']].append(entry)

results = []
for job_id, entries in jobs_by_id.items():
    job = entries[0].copy()

    # If same job in multiple offices, concatenate locations
    if len(entries) > 1:
        unique_offices = []
        seen = set()
        for entry in entries:
            if entry['office'] not in seen:
                unique_offices.append(entry['office'])
                seen.add(entry['office'])
        job['office'] = '; '.join(unique_offices)  # "SF; NYC; Seattle"

    results.append(job)
```

## Configuration

### TitleFilters

All extractors accept `TitleFilters` config:

```python
from extractors.config import TitleFilters

# Basic filtering
filters = TitleFilters(
    include=['software', 'engineer'],  # OR logic: title must contain ANY
    exclude=['intern', 'early career']  # AND logic: title must contain NONE
)

# Optional semantics for include
filters = TitleFilters(
    include=['python', 'golang'],  # Optional: if provided, title must match
    exclude=['senior staff']       # Always applied
)

# No filtering (extract all jobs)
filters = TitleFilters()
```

**Filtering Logic:**
1. `include` is **optional**: if not provided or empty, all jobs pass
2. `include` uses **OR logic**: title must contain at least ONE keyword
3. `exclude` uses **AND logic**: title must contain NONE of the keywords
4. Matching is **case-insensitive**

## Response Format

### Dictionary Structure

All extractors return a dictionary with this structure:

```python
{
    'total_count': int,        # Total jobs fetched from API
    'filtered_count': int,     # Jobs filtered out by title filters
    'urls_count': int,         # Jobs remaining after filtering
    'included_jobs': [         # Jobs that passed filters
        {
            'id': str,         # Unique job ID
            'title': str,      # Job title
            'location': str,   # Location string (e.g., "San Jose, California")
            'url': str         # Full job URL
        },
        ...
    ],
    'excluded_jobs': [         # Jobs that were filtered out
        {
            'id': str,
            'title': str,
            'location': str,
            'url': str
        },
        ...
    ]
}
```

### Example Access

```python
result = extractor.extract_source_urls_metadata()

# Access counts
print(f"Total: {result['total_count']}")
print(f"Included: {result['urls_count']}")
print(f"Excluded: {result['filtered_count']}")

# Access job data
for job in result['included_jobs']:
    print(f"{job['id']}: {job['title']} at {job['location']}")
    print(f"  URL: {job['url']}")
```

## Design Principles

1. **Abstract COMPANY_NAME**: Each extractor sets `COMPANY_NAME = Company.ENUM_VALUE`
2. **Separate Enum File**: Company enum in `enums.py` avoids circular imports
3. **Simple Registry**: Direct dictionary mapping in `registry.py`
4. **Standardized Job Format**: All extractors return same job object structure
5. **Check Trials First**: Always review API snapshots before implementing/updating extractors
6. **Location Handling**: Handle company-specific quirks (nested structures, dual IDs, etc.)
7. **Deduplication**: By job ID (not title), aggregate locations when needed
8. **Pure Functions**: Stateless, same input → same output
9. **Error Handling**: Catch exceptions, log errors, continue processing

## Testing

### Unit Test Example

```python
from extractors import get_extractor, Company
from extractors.config import TitleFilters

def test_google_extractor():
    # Test with no filters
    extractor = get_extractor(Company.GOOGLE)
    result = extractor.extract_source_urls_metadata()

    assert result['total_count'] > 0
    assert result['urls_count'] == result['total_count']  # No filtering
    assert len(result['included_jobs']) == result['urls_count']

    # Test with filters
    filters = TitleFilters(include=['software'], exclude=['senior staff'])
    extractor = get_extractor(Company.GOOGLE, config=filters)
    result = extractor.extract_source_urls_metadata()

    assert result['filtered_count'] > 0  # Some jobs filtered
    assert result['urls_count'] < result['total_count']

    # Verify all jobs have required fields
    for job in result['included_jobs']:
        assert job['id']
        assert job['title']
        assert job['url'].startswith('https://')
```

### Integration Test

```python
# Test all companies in parallel
import asyncio
from api.sourcing import extract_all_companies

async def test_all_extractors():
    results = await extract_all_companies()

    for company, result in results.items():
        print(f"✓ {company:12} | Total: {result.total_count:3} | "
              f"Filtered: {result.filtered_count:3} | URLs: {result.urls_count}")

        # Verify structure
        assert result.total_count >= result.urls_count
        assert result.filtered_count == result.total_count - result.urls_count
        assert len(result.metadata) == result.urls_count

asyncio.run(test_all_extractors())
```

## Common Patterns

### Pagination

```python
def _fetch_all_jobs(self):
    all_jobs = []
    page = 1

    while True:
        response = self._make_request(self.API_URL, params={'page': page})
        jobs = response.get('jobs', [])

        if not jobs:  # No more pages
            break

        all_jobs.extend(self._standardize_jobs(jobs))
        page += 1

    return all_jobs
```

### POST Requests

```python
def _fetch_all_jobs(self):
    payload = {
        'filters': {...},
        'limit': 100,
        'offset': 0
    }

    response = self._make_request(
        self.API_URL,
        method='POST',
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
```

### Error Handling

```python
def _fetch_all_jobs(self):
    try:
        response = self._make_request(self.API_URL)
        # ... process response ...
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return []  # Return empty list on error
```

## Supported Companies

| Company | Status | Jobs | Notes |
|---------|--------|------|-------|
| Google | ✅ | 102 | Standard API |
| Amazon | ✅ | 63 | Dual ID fields (use id_icims) |
| Anthropic | ✅ | 30 | Uses 'office' field, aggregates locations |
| TikTok | ✅ | 185 | Nested city_info structure |
| Roblox | ✅ | 60 | Standard API |
| Netflix | ✅ | 40 | Standard API |

## Next Steps

1. Add more companies (Meta, Apple, Microsoft, etc.)
2. Implement Phase 2 crawlers
3. Implement Phase 3 parsers
4. Add database/SQS integration for dynamic settings
5. Deploy to AWS Lambda
