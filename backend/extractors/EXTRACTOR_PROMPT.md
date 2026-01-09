# Extractor Enhancement Prompt

Use this prompt to implement **raw info extraction** for an existing company extractor.

For creating new source URL extractors, see `SOURCEURL_PROMPT.md`.

---

## Usage

```
Read backend/extractors/EXTRACTOR_PROMPT.md and implement extract_raw_info for {company}.py
```

---

## Overview

The base class `BaseJobExtractor` provides a 3-stage pipeline:

| Stage | Method | Location | Purpose |
|-------|--------|----------|---------|
| 1 | `extract_source_urls_metadata()` | Base class | Get job URLs |
| 2 | `crawl_raw_info(job_url)` | Base class (generic) | Fetch raw HTML/JSON |
| 3 | `extract_raw_info(raw_content)` | **Each extractor (abstract)** | Parse description/requirements |

**Your task**: Implement `extract_raw_info()` for the target company.

---

## Before You Start

### 1. Use the Test Script

```bash
cd backend

# Get sample URLs for the company
python3 extractors/test_extractor_raw.py urls {company}

# Crawl raw content from a URL (to see the HTML/JSON structure)
python3 extractors/test_extractor_raw.py crawl {company} "<url>"

# Test extraction (will fail until implemented)
python3 extractors/test_extractor_raw.py extract {company} "<url>"
```

### 2. Analyze Raw Content

Run the `crawl` command and examine the HTML/JSON structure to understand how to parse it.

---

## Raw Info Crawling (Base Class)

The base class provides a generic `crawl_raw_info()` that works for most companies:

```python
# Already implemented in BaseJobExtractor
async def crawl_raw_info(self, job_url: str) -> str:
    """Returns raw HTML/JSON as string. Raises exception on error."""
```

### Override When Needed

Override `crawl_raw_info()` only if the company needs special handling:

| Company | Override Needed | Reason |
|---------|-----------------|--------|
| Amazon | Different headers | Job detail API needs specific headers |
| Google | Parse embedded JS | Job details in `AF_initDataCallback` |

Example override:

```python
async def crawl_raw_info(self, job_url: str) -> str:
    """Override for company-specific crawling logic"""
    # Custom implementation here
    # Must return raw content as string
```

---

## Raw Info Extraction (Your Task)

Each extractor has a placeholder `extract_raw_info()` that raises `NotImplementedError`.
Your task is to implement the parsing logic.

### Method Signature

```python
def extract_raw_info(self, raw_content: str) -> dict:
    """
    Extract structured job details from raw content.

    Args:
        raw_content: Raw HTML/JSON string from crawl_raw_info()

    Returns:
        {
            'description': str,      # Job description text
            'requirements': str,     # Job requirements/qualifications
        }

    Raises:
        ValueError: If content cannot be parsed

    Note: Fields match Job model schema (description, requirements as Text columns).
    """
```

### Implementation Template

```python
def extract_raw_info(self, raw_content: str) -> dict:
    """Extract job details from {Company} job page"""
    if not raw_content:
        raise ValueError("No content to extract from")

    # TODO: Company-specific parsing logic
    description = ''
    requirements = ''

    # For HTML: use regex to find sections
    # For JSON: json.loads() then navigate structure

    return {
        'description': description,
        'requirements': requirements,
    }
```

### Parsing Strategy

1. **For HTML content**: Use regex to find relevant sections, strip HTML tags
2. **For JSON content**: Navigate the structure to extract fields

### Example: HTML Parsing

```python
def extract_raw_info(self, raw_content: str) -> dict:
    """Extract job details from HTML"""
    import re

    if not raw_content:
        raise ValueError("No content to extract from")

    # Extract description (adjust selectors for company)
    description = ''
    desc_match = re.search(r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>', raw_content, re.DOTALL)
    if desc_match:
        description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

    # Extract requirements
    requirements = ''
    req_match = re.search(r'<div[^>]*class="[^"]*requirements[^"]*"[^>]*>(.*?)</div>', raw_content, re.DOTALL)
    if req_match:
        requirements = re.sub(r'<[^>]+>', '', req_match.group(1)).strip()

    return {
        'description': description,
        'requirements': requirements,
    }
```

---

## Testing

Use the provided test script:

```bash
cd backend

# Step 1: Get sample URLs
python3 extractors/test_extractor_raw.py urls {company}

# Step 2: Crawl to see raw content structure
python3 extractors/test_extractor_raw.py crawl {company} "<url>"

# Step 3: Test extraction (after implementing)
python3 extractors/test_extractor_raw.py extract {company} "<url>"
```

### Expected Output for `extract`

```
Extracting info for {company}...
URL: https://...

Step 1: Crawling raw content...
  Status: 200
  Content: HTML (12345 chars)

Step 2: Extracting structured info...

============================================================
EXTRACTED INFO
============================================================

Description (1234 chars):
----------------------------------------
Job description text here...

Requirements (567 chars):
----------------------------------------
- Requirement 1
- Requirement 2
...

============================================================
Test completed!
```

---

## Implementation Checklist

- [ ] Ran `crawl` command to see raw content structure
- [ ] Implemented `extract_raw_info()` with company-specific parsing
- [ ] Parsing extracts: description, requirements
- [ ] `extract` command runs successfully
- [ ] Edge cases handled (missing sections, different page layouts)
- [ ] (Optional) Override `crawl_raw_info()` if needed

---

## Workflow for Claude

When implementing for a specific company:

1. **Read existing extractor** - Understand current structure
2. **Get sample URL** - `python3 extractors/test_extractor_raw.py urls {company}`
3. **Analyze raw content** - `python3 extractors/test_extractor_raw.py crawl {company} "<url>"`
4. **Implement extraction** - Replace the `NotImplementedError` in `extract_raw_info()`
5. **Test extraction** - `python3 extractors/test_extractor_raw.py extract {company} "<url>"`
6. **Save output for inspection** - Save raw HTML and extracted text to `.temp/` folder
7. **Handle edge cases** - Test with multiple jobs, handle missing sections
8. **(Optional)** Override `crawl_raw_info()` if company needs special crawling logic

---

## Save Output for Inspection

After implementing, save output to `.temp/` folder for user inspection:

```python
# Run this to save raw and extracted content
cd backend
python3 -c "
import asyncio
from extractors import get_extractor
from extractors.config import TitleFilters

async def main():
    extractor = get_extractor('{company}', config=TitleFilters())
    url = '<sample_url>'

    # Crawl and save raw
    raw = await extractor.crawl_raw_info(url)
    with open('extractors/.temp/{company}_raw.html', 'w') as f:
        f.write(raw)

    # Extract and save
    result = extractor.extract_raw_info(raw)
    with open('extractors/.temp/{company}_extracted.txt', 'w') as f:
        f.write(f'=== URL ===\n\n{url}\n\n')
        f.write('=== DESCRIPTION ===\n\n')
        f.write(result['description'])
        f.write('\n\n=== REQUIREMENTS ===\n\n')
        f.write(result['requirements'])

    print('Saved to extractors/.temp/')

asyncio.run(main())
"
```

Output files (gitignored):
- `extractors/.temp/{company}_raw.html` - Raw HTML for debugging
- `extractors/.temp/{company}_extracted.txt` - Extracted description + requirements
