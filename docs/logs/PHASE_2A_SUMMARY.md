# Phase 2A: Job URL Extractor Architecture

**Status**: ✅ Completed
**Date**: December 15, 2025
**Goal**: Design and implement a scalable extractor framework for sourcing job URLs from company career pages

---

## Overview

Phase 2A established a production-ready extractor framework capable of sourcing job URLs from multiple companies. The architecture supports company-specific implementations via abstract base class, centralized registration, configurable title filtering, and standardized API response handling.

**Included in this phase**:
- Abstract base extractor class with shared utilities
- Registry pattern for dynamic extractor selection
- Title filtering configuration (Pydantic-based)
- 6 production extractors (Google, Amazon, Anthropic, TikTok, Roblox, Netflix)
- Exploratory approach to discover undocumented APIs

**Explicitly excluded** (deferred to Phase 2B+):
- Full job crawling (descriptions, requirements, posted dates)
- Database persistence
- SQS/Lambda integration
- Frontend UI

---

## Key Achievements

### 1. Extractor Framework Design
- **Abstract base class**: Enforces consistent interface across implementations
- **Registry pattern**: Centralized discovery and instantiation by company enum
- **Standardized output**: All extractors return same job metadata structure
- **External configuration**: Title filters passed via constructor (not hardcoded)
- **Preserve raw data**: Keep original API responses for future phases

### 2. API Discovery Process
- **Exploratory research**: Browser DevTools, network monitoring, "Copy as cURL"
- **Pattern identification**: Static HTML vs. API-based extraction
- **Snapshot creation**: Save API responses in `trials/` for reference
- **Quirk documentation**: Amazon dual IDs, TikTok nested locations, Anthropic aggregation

### 3. Title Filtering System
- **Pydantic model**: `TitleFilters` with include/exclude lists
- **OR logic**: `include` filters (match at least ONE keyword)
- **AND logic**: `exclude` filters (must contain NONE)
- **Case-insensitive**: Matching works regardless of case
- **Example**: 1,100 jobs → ~300 relevant matches after filtering

### 4. Six Production Extractors
- **Google**: 102 jobs via standard REST API (~3s)
- **Amazon**: 63 jobs via API with dual ID quirk (~4s)
- **Anthropic**: 30 jobs with location aggregation (~2s)
- **TikTok**: 185 jobs via API with custom headers (~5s)
- **Roblox**: 60 jobs via static HTML parsing (~4s)
- **Netflix**: 40 jobs via standard REST API (~2s)

Reference: [Extractor README](../../backend/extractors/README.md)

---

## Highlights

### API Patterns Discovered

**Pattern 1 - Static HTML Extraction** (Roblox):
- All job IDs embedded in initial page source
- Simple regex extraction from HTML
- No API calls or pagination needed
- Fast and reliable (~4 seconds)

**Pattern 2 - Public API with Custom Requirements** (TikTok):
- Direct API calls with company-specific headers
- POST requests with pagination
- Custom authentication or header requirements (e.g., `website-path: tiktok`)
- ~5 seconds per company

**Pattern 3 - Standard REST API** (Google, Netflix):
- GET requests with standard query parameters (page, limit)
- Straightforward pagination
- Most common pattern among tech companies
- ~2-3 seconds per company

### Company-Specific Quirks

**Amazon Dual IDs**:
- API returns UUID (`id`) and job number (`id_icims`)
- URLs require `id_icims`, not `id`
- Prevented 100% broken URLs by checking trials snapshots

**TikTok Nested Locations**:
- Location deeply nested: `city_info.parent.parent`
- Custom parser extracts city + state only
- Result: Clean "San Jose, California" not full hierarchy

**Anthropic Location Aggregation**:
- Same job ID appears in multiple office locations
- Deduplicate by ID, concatenate locations
- Result: Single job entry with "SF; NYC; Seattle"

### Exploratory Development Workflow
1. Test extraction methods on 2-3 companies
2. Identify common patterns and unique quirks
3. Extract base class with shared logic
4. Refactor implementations to use base class
5. Add remaining companies quickly

**Result**: 6 extractors built in ~2 days

---

## Testing & Validation

**Manual Testing**:
- ✅ URL extraction for all 6 companies
- ✅ Job count validation (ranges match expectations)
- ✅ URL formatting correctness
- ✅ Title filtering accuracy (include/exclude logic)
- ✅ Location standardization

**Automated Testing**:
- Future: Unit tests for base class, mock responses, integration tests

---

## Metrics

- **Companies supported**: 6 (Google, Amazon, Anthropic, TikTok, Roblox, Netflix)
- **Total jobs sourced**: ~1,100 (varies by day)
- **Lines of code**: ~1,500 (base + registry + all extractors)
- **Average extraction time**: 2-5 seconds per company
- **Code reuse**: 70% (base class + registry shared by all)
- **Discovery time**: ~2 days for 6 companies

---

## Next Steps → Phase 2B

Phase 2B will add database integration and user management:
- PostgreSQL database setup (Neon)
- SQLAlchemy models and migrations (Alembic)
- User table with OAuth data
- Frontend UI skeleton (React Router, dashboard layout)

**Target**: Database foundation ready for Phase 2C ingestion workflow

---

## File Structure

```
backend/extractors/
├── __init__.py           # Package exports
├── base_extractor.py     # Abstract base class
├── config.py             # TitleFilters Pydantic model
├── enums.py              # Company enum (avoids circular imports)
├── registry.py           # Extractor registry + helpers
├── google.py             # Company extractors
├── amazon.py
├── anthropic.py
├── tiktok.py
├── roblox.py
├── netflix.py
├── example_usage.py      # Usage examples
└── README.md             # Documentation
```

**Key Files**:
- [base_extractor.py](../../backend/extractors/base_extractor.py) - Abstract base class
- [registry.py](../../backend/extractors/registry.py) - Extractor discovery
- [config.py](../../backend/extractors/config.py) - Title filtering configuration
- [README.md](../../backend/extractors/README.md) - Usage guide

---

## Key Learnings

### Trials Folder Importance
API response snapshots in `trials/{company}/` critical for understanding actual structure vs. documentation. Prevented multiple bugs (Amazon dual IDs, TikTok nested locations).

### DevTools Essential
Network tab, "Copy as cURL", XHR filtering reduced discovery time from hours to minutes per company.

### API Quirks Universal
Every company has unique quirks: dual IDs, nested structures, custom headers, field inconsistencies. Flexible base class allows overrides without breaking abstraction.

---

## References

**External Documentation**:
- [requests Library](https://requests.readthedocs.io/) - HTTP client
- [Pydantic](https://docs.pydantic.dev/) - Data validation

---

**Status**: Ready for Phase 2B
