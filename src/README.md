# Job Hunter - Production Source Code

This directory contains production-ready code for the job extraction pipeline.

## Directory Structure

```
/Users/duan/coding/jh/
├── backend/              # API backend (authentication, etc.)
├── frontend/             # Web frontend
├── trials/               # Experimental/prototype extractors + API snapshots
├── docs/                 # Learning documentation
└── src/                  # Production code
    ├── extractors/       # Phase 1: URL extraction (✅ Complete)
    │   ├── __init__.py           # Package exports
    │   ├── base_extractor.py     # Abstract base class
    │   ├── config.py             # TitleFilters config
    │   ├── enums.py              # Company enum
    │   ├── registry.py           # Extractor registry + helpers
    │   ├── google.py             # Google Careers ✅
    │   ├── amazon.py             # Amazon Jobs ✅
    │   ├── anthropic.py          # Anthropic ✅
    │   ├── tiktok.py             # TikTok ✅
    │   ├── roblox.py             # Roblox ✅
    │   └── netflix.py            # Netflix ✅
    │
    ├── api/              # FastAPI endpoints (✅ Complete)
    │   └── sourcing.py   # /api/sourcing endpoint
    │
    ├── crawlers/         # Phase 2: Raw content fetching (future)
    ├── parsers/          # Phase 3: Structured data extraction (future)
    └── wrappers/         # Orchestration for Lambda deployment (future)
```

## Design Philosophy

### 1. Separation from Trials

- **`/trials/`**: Experimental code, quick prototypes, API response snapshots
- **`/src/`**: Production-ready, well-tested, deployable code

**Important**: Before updating extractor logic, always check `/trials/{company}/` for API response snapshots to understand actual API structure.

### 2. Three-Phase Pipeline

```
Phase 1: URL Extraction (✅ current)
  Input:  Company name + filters
  Output: Full job metadata (id, title, location, url)

Phase 2: Crawling (future)
  Input:  Job URL
  Output: Raw HTML/JSON content

Phase 3: Parsing (future)
  Input:  Raw content
  Output: Structured job data
```

### 3. Base Class Pattern

Each phase has a base class that defines the interface:

```python
# Phase 1: URL Extraction
class BaseJobExtractor(ABC, Generic[ConfigType]):
    # Abstract class variables - must be defined by concrete extractors
    API_URL: str
    URL_PREFIX_JOB: str
    COMPANY_NAME: 'Company'  # Must be Company enum value

    @abstractmethod
    def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all jobs from API and return standardized format"""
        pass

    def extract_source_urls(self, unique_titles: bool = True) -> CompanyResult:
        """Main entry point - returns full metadata"""
        pass

# Phase 2: Crawling (future)
class BaseCrawler(ABC):
    @abstractmethod
    def crawl(self, url: str) -> str:
        pass

# Phase 3: Parsing (future)
class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw_content: str) -> Dict:
        pass
```

### 4. Standardized Job Object

All extractors return jobs in this format:

```python
{
    'id': str,           # Unique job ID
    'title': str,        # Job title
    'location': str,     # Location string (city, state)
    'url': str,          # Full job URL
    'response_data': {}  # Original API response (for debugging)
}
```

**Company-Specific Notes:**
- **Amazon**: Uses `id_icims` (job number) not `id` (UUID) for URL construction
- **TikTok**: Builds location from nested `city_info` structure (city, state only)
- **Anthropic**: Uses `office` field (not `location`), aggregates multiple locations for same job ID

### 5. Configuration via Pydantic Models

All company-specific settings passed via Pydantic config:

```python
from extractors.config import TitleFilters

filters = TitleFilters(
    include=['software', 'engineer'],  # OR logic
    exclude=['senior staff', 'principal']  # AND logic
)

extractor = GoogleExtractor(config=filters)
```

### 6. Company Registry

Extractors registered via enum in a simple registry dictionary:

```python
from extractors import Company, get_extractor, COMPANY_REGISTRY

# Get extractor by enum
extractor = get_extractor(Company.GOOGLE, config=filters)

# Or by string
extractor = get_extractor('google', config=filters)

# Direct access to registry
ExtractorClass = COMPANY_REGISTRY[Company.GOOGLE]

# List all companies
companies = list_companies()  # ['google', 'amazon', 'anthropic', ...]
```

**Architecture**: Company enum is in separate `enums.py` file to avoid circular imports.

## Current Status

### ✅ Phase 1 Complete (URL Extraction)

1. **Base Infrastructure**:
   - `BaseJobExtractor` abstract class
   - `TitleFilters` Pydantic config
   - Company enum in `enums.py`
   - Registry dictionary with helper functions
   - Standardized job object format

2. **All 6 Extractors Implemented**:
   - ✅ Google Careers (102 jobs)
   - ✅ Amazon Jobs (63 jobs)
   - ✅ Anthropic (30 jobs)
   - ✅ TikTok (185 jobs after filtering)
   - ✅ Roblox (60 jobs after filtering)
   - ✅ Netflix (40 jobs)

3. **FastAPI Endpoint**:
   - `/api/sourcing` - Parallel extraction across all companies
   - Returns full metadata with statistics

### 🔮 Future Work

1. Phase 2: Crawlers (fetch raw HTML/JSON)
2. Phase 3: Parsers (extract structured data)
3. Wrappers for orchestration
4. Lambda deployment scripts
5. Database/SQS integration for settings

## Extractor Implementation Pattern

All extractors follow this pattern:

```python
from extractors.base_extractor import BaseJobExtractor
from extractors.registry import Company
from extractors.config import TitleFilters
from typing import List, Dict, Any

class GoogleExtractor(BaseJobExtractor[TitleFilters]):
    """Extract job URLs from Google Careers"""

    # Required class variables
    API_URL = "https://careers.google.com/api/v3/search"
    URL_PREFIX_JOB = "https://www.google.com/about/careers/applications/jobs/results/"
    COMPANY_NAME = Company.GOOGLE  # Enum value, not string

    def _fetch_all_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all jobs and return standardized format"""
        all_jobs = []
        page = 1

        while True:
            # 1. Make API request
            response = self._make_request(...)
            jobs = response.get('jobs', [])

            if not jobs:
                break

            # 2. Standardize each job
            for job in jobs:
                standardized_job = {
                    'id': str(job.get('id', '')),
                    'title': job.get('title', ''),
                    'location': job.get('location', ''),
                    'url': f"{self.URL_PREFIX_JOB}{job.get('id')}",
                    'response_data': job
                }
                all_jobs.append(standardized_job)

            page += 1

        return all_jobs
```

**Key Requirements:**
1. Set `COMPANY_NAME` to enum value (e.g., `Company.GOOGLE`)
2. Implement `_fetch_all_jobs()` returning standardized job objects
3. Check `/trials/{company}/` for API response snapshots before implementation

## Testing

Test extractors via FastAPI endpoint:

```python
# src/api/test_sourcing.py
import asyncio
from api.sourcing import extract_all_companies

async def test():
    results = await extract_all_companies()

    for company, result in results.items():
        print(f"✓ {company:12} | Total: {result.total_count:3} | "
              f"Filtered: {result.filtered_count:3} | URLs: {result.urls_count}")

asyncio.run(test())
```

**Expected Output:**
```
✓ GOOGLE       | Total: 117 | Filtered:  15 | URLs: 102
✓ AMAZON       | Total:  63 | Filtered:   0 | URLs:  63
✓ ANTHROPIC    | Total:  30 | Filtered:   0 | URLs:  30
✓ TIKTOK       | Total: 565 | Filtered: 380 | URLs: 185
✓ ROBLOX       | Total: 189 | Filtered: 129 | URLs:  60
✓ NETFLIX      | Total:  40 | Filtered:   0 | URLs:  40
```

## Local Development

Run extractors locally:

```bash
# Test single company
python -c "from extractors import get_extractor, Company; \
           result = get_extractor(Company.GOOGLE).extract_source_urls_metadata(); \
           print(f\"Found {result['urls_count']} URLs\")"

# Test all companies
python backend/tests/test_sourcing.py
```

## Deployment

Ready for Lambda deployment:
- All extractors tested and working
- FastAPI endpoint for orchestration
- Async/parallel extraction for performance
- Standardized response format

**Next Steps:**
1. Create Lambda wrapper
2. Add database/SQS integration for settings
3. Deploy to AWS
