# New Extractor Skill

Creates or enhances a company job extractor following the established patterns.

## Usage

```
/new-extractor {company}
```

## Workflow

### Step 1: Check if extractor exists

```bash
ls backend/extractors/{company}.py
```

- **If exists**: Implement `extract_raw_info()` (see EXTRACTOR_PROMPT.md)
- **If new**: Create full extractor from template

### Step 2: Gather sample data

```bash
cd backend

# Get sample URLs
python3 extractors/test_extractor_raw.py urls {company}

# Crawl raw content to understand structure
python3 extractors/test_extractor_raw.py crawl {company} "<url>"
```

### Step 3: Check trials folder for API snapshots

```bash
ls trials/{company}/
```

Review any existing API response snapshots before implementing.

### Step 4: Implement

Reference files:
- Pattern: `@backend/extractors/base_extractor.py`
- Example: `@backend/extractors/anthropic.py`
- Full guide: `@backend/extractors/EXTRACTOR_PROMPT.md`

Required class variables:
- `COMPANY_NAME`: Company enum value
- `API_URL`: Career page API endpoint
- `URL_PREFIX_JOB`: URL prefix for job detail pages

Required methods:
- `_fetch_all_jobs()`: Fetch and standardize job listings
- `extract_raw_info()`: Parse description/requirements from raw HTML/JSON

### Step 5: Register in enum and registry

1. Add to `backend/extractors/enums.py`:
```python
class Company(str, Enum):
    ...
    {COMPANY} = "{company}"
```

2. Add to `backend/extractors/registry.py`:
```python
from .{company} import {Company}Extractor

EXTRACTORS = {
    ...
    Company.{COMPANY}: {Company}Extractor,
}
```

### Step 6: Test

```bash
cd backend

# Test URL extraction
python3 extractors/test_extractor_raw.py urls {company}

# Test raw info extraction
python3 extractors/test_extractor_raw.py extract {company} "<url>"
```

### Step 7: Save output for inspection

Save to `backend/extractors/.temp/{company}_raw.html` and `{company}_extracted.txt` for user review.

## Common Quirks

| Company | Issue | Solution |
|---------|-------|----------|
| Amazon | Dual IDs (id_icims, id_amazon) | Use job_path from response |
| TikTok | Nested location objects | Flatten location hierarchy |
| Anthropic | Office field instead of location | Map office → location |
| Google | Data in AF_initDataCallback | Parse embedded JS |
