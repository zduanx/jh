# Phase 2I: Extractor Flow Improvements

**Status**: ✅ Completed
**Date**: January 8, 2026
**Goal**: Enhance extractors with raw info crawling and content extraction for job details

---

## Overview

Phase 2I extends the extractor architecture to support full job detail extraction. Previously, extractors only extracted source info (job ID, title, URL from career page APIs). This phase adds two new capabilities:

1. **Raw Info Crawling**: Fetch full job page content via HTTP requests
2. **Raw Info Extraction**: Parse job requirements and description from raw HTML/JSON

Each company's job page has unique structure. We created reusable Claude prompts that generate company-specific extraction code, documented in EXTRACTOR_PROMPT.md.

**Included in this phase**:
- Raw info crawling (`crawl_raw_info()` method in base class)
- Raw info extraction (`extract_raw_info()` method for all 6 companies)
- Claude prompt template for extractor generation
- Test script for manual verification
- Netflix URL sourcing fix (use canonicalPositionUrl)

**Explicitly excluded** (deferred to Phase 2J):
- SQS queues for job distribution
- Lambda workers (Crawler, Extractor)
- S3 storage for raw HTML
- SimHash deduplication

---

## Key Achievements

### 1. Three-Stage Extraction Pipeline
- Stage 1: `_fetch_all_jobs()` → Job list with IDs/URLs (existing)
- Stage 2: `crawl_raw_info()` → Fetch full page content
- Stage 3: `extract_raw_info()` → Parse requirements, description

### 2. Company-Specific Extractors
- **Google**: JSON-LD schema.org JobPosting in script tag
- **Amazon**: JSON embedded in `<script type="application/json">` tag
- **Anthropic**: HTML with `<h3>` section headers (Responsibilities, Requirements)
- **Netflix**: JSON-LD JobPosting with HTML description containing `<strong>` markers
- **Roblox**: HTML between content-intro div with `<strong>You Will/Have</strong>` sections
- **TikTok**: Next.js RSC format with `self.__next_f.push()` data blocks

### 3. Claude Prompt Template
- Created EXTRACTOR_PROMPT.md with step-by-step implementation guide
- Documents HTML structure patterns for each company
- Includes test script for manual verification

### 4. URL Sourcing Fixes
- Netflix: Fixed URL mismatch (jobs.netflix.com vs explore.jobs.netflix.net)
- Added `url` field from `canonicalPositionUrl` in response_data

---

## Highlights

### Content Structure Patterns

| Company | Data Source | Key Markers |
|---------|-------------|-------------|
| Google | JSON-LD | `"@type": "JobPosting"` |
| Amazon | Script JSON | `<script type="application/json">` |
| Anthropic | HTML | `<h3>Responsibilities</h3>`, `<h3>Requirements</h3>` |
| Netflix | JSON-LD + HTML | `"description":` with `<strong>qualifications</strong>` |
| Roblox | HTML | `<strong>You Will:</strong>`, `<strong>You Have:</strong>` |
| TikTok | Next.js RSC | `self.__next_f.push([1,"..."])` with `T<hex>,<text>` blocks |

### strip_html() Helper Function
Each extractor uses a local `strip_html()` function that:
- Converts `<br>`, `<p>`, `<li>` to newlines/bullets
- Strips remaining HTML tags
- Decodes HTML entities (`&amp;`, `&#x27;`, etc.)
- Normalizes whitespace and removes extra blank lines

### TikTok RSC Format
TikTok uses React Server Components with double-escaped JSON:
```
self.__next_f.push([1,"30:T5f5,Team Intro\\nThe team..."])
```
- `T5f5` = hex length prefix
- `\\n` = double-escaped newlines
- `\u0026` = JSON unicode escapes

---

## Testing & Validation

**Manual Testing**:
```bash
cd backend

# Get sample URLs
python3 extractors/test_extractor_raw.py urls google

# Test extraction
python3 extractors/test_extractor_raw.py extract google "<url>"
```

**Output Files** (gitignored):
- `extractors/.temp/{company}_raw.html` - Raw HTML for debugging
- `extractors/.temp/{company}_extracted.txt` - Extracted description + requirements

**Validation Results**:
- All 6 companies successfully extract description and requirements
- List items formatted with `-` bullets, no extra blank lines
- Unicode entities properly decoded

---

## Metrics

| Metric | Value |
|--------|-------|
| Companies implemented | 6 (Google, Amazon, Anthropic, Netflix, Roblox, TikTok) |
| New base class methods | 2 (`crawl_raw_info`, `extract_raw_info`) |
| Extraction fields | 2 (description, requirements) |
| Test script commands | 3 (urls, crawl, extract) |

---

## Next Steps → Phase 2J

Phase 2J implements the production infrastructure:
- SQS queues for job distribution
- CrawlerLambda and ExtractorLambda workers
- S3 storage for raw HTML
- SimHash deduplication

---

## File Structure

```
backend/
├── extractors/
│   ├── base_extractor.py      # crawl_raw_info() base method
│   ├── google.py              # extract_raw_info() implemented
│   ├── amazon.py              # extract_raw_info() implemented
│   ├── anthropic.py           # extract_raw_info() implemented
│   ├── netflix.py             # extract_raw_info() + URL fix
│   ├── roblox.py              # extract_raw_info() implemented
│   ├── tiktok.py              # extract_raw_info() implemented
│   ├── test_extractor_raw.py  # Manual test script
│   ├── EXTRACTOR_PROMPT.md    # Claude prompt template
│   └── .temp/                 # Test output (gitignored)
│       ├── {company}_raw.html
│       └── {company}_extracted.txt
```

**Key Files**:
- [base_extractor.py](../../backend/extractors/base_extractor.py) - Base class with crawl method
- [EXTRACTOR_PROMPT.md](../../backend/extractors/EXTRACTOR_PROMPT.md) - Implementation guide
- [test_extractor_raw.py](../../backend/extractors/test_extractor_raw.py) - Test script

---

## References

**External Documentation**:
- [httpx Documentation](https://www.python-httpx.org/) - Async HTTP client
- [JSON-LD Schema.org](https://schema.org/JobPosting) - JobPosting schema
