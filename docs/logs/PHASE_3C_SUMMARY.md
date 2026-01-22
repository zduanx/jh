# Phase 3C: Fuzzy Search

**Status**: ✅ Completed
**Date**: January 15, 2026
**Goal**: Implement full-text search with fuzzy matching using PostgreSQL hybrid search (ADR-014)

---

## Overview

Phase 3C adds search functionality to the Search page. Users can search job titles and descriptions with typo tolerance using PostgreSQL's native full-text search (tsvector) combined with fuzzy matching (pg_trgm).

The implementation uses a single optimized SQL query that returns all jobs with a computed `matched` flag, allowing the backend to filter results while preserving company groupings. Search is triggered via Enter key or Search button (not debounce) for explicit user control.

**Included in this phase**:
- Database: tsvector column, GIN indexes, auto-update trigger
- Backend: `?q=` parameter on existing `GET /api/jobs` endpoint
- Frontend: Search bar with Enter-to-search, Search button, clear functionality
- UX: Select-all on focus, X/Y job count display during search

**Explicitly excluded** (deferred to Phase 4):
- Job tracking/cart functionality
- Saved searches
- Advanced filters (company, status dropdowns)

---

## Key Achievements

1. **Hybrid Search Implementation**
   - Full-text search using tsvector for stemming ("running" → "run")
   - Fuzzy search using pg_trgm for typo tolerance ("kubernets" → "kubernetes")
   - Single optimized query with computed `matched` column
   - Reference: [ADR-014](../architecture/DECISIONS.md#adr-014-use-hybrid-text-search-postgresql-full-text--fuzzy)

2. **Database Migration**
   - Added `search_vector` TSVECTOR column to jobs table
   - Created GIN indexes for both full-text and trigram search
   - Trigger auto-updates search_vector on INSERT/UPDATE of title or description
   - Weighted search: title (A) + description (B)

3. **Enter-to-Search UX**
   - Search triggered by Enter key or Search button (not debounce)
   - Gives user explicit control over when to search
   - Select-all on focus for easy query replacement
   - Shows "Showing results for X" status bar with Clear button

4. **X/Y Job Count Display**
   - Company cards show matched/total (e.g., "3/45") during search
   - Preserves original totals for comparison
   - Companies with 0 matches still visible

---

## Database Schema

**jobs table additions**:
- `search_vector` (TSVECTOR): Auto-populated weighted vector of title (A) + description (B)
- `idx_jobs_search_vector`: GIN index for full-text search
- `idx_jobs_title_trgm`: GIN trigram index for fuzzy title matching
- `jobs_search_vector_trigger`: Auto-updates search_vector on title/description changes

**Migration**: `6147d489fb1a_add_search_indexes.py`

---

## API Endpoints

**Route**: `GET /api/jobs?q={query}`
- Added optional `q` query parameter to existing endpoint
- Min 2 characters required for search
- Returns same structure with added `query` field in response
- Single DB query optimization with `matched` computed column

**Request**: `GET /api/jobs?q=kubernetes`

**Response**:
```json
{
  "companies": [
    {
      "name": "google",
      "display_name": "Google",
      "logo_url": "https://...",
      "ready_count": 3,
      "jobs": [{"id": 123, "title": "K8s Engineer", "location": "Seattle"}]
    }
  ],
  "total_ready": 8,
  "query": "kubernetes"
}
```

---

## Highlights

### Single Query Optimization

Instead of running two separate queries (one for all companies, one for matched jobs), we use a single query with a computed `matched` column:

```sql
SELECT *,
    (search_vector @@ plainto_tsquery('english', :query)
     OR similarity(title, :query) > 0.2) AS matched
FROM jobs
WHERE user_id = :user_id AND status = 'ready'
ORDER BY company, title
```

Python then filters to only include matched jobs while preserving all company groupings. This halves database round-trips.

### Whitespace Normalization

Search queries are normalized on both frontend and backend:
- Backend: `query.strip()` before DB query
- Frontend: `data.query?.trim().replace(/\s+/g, ' ')` for display
- Prevents display issues with newlines in status bar

### Select-All on Focus

Added `onFocus={(e) => e.target.select()}` to search input for better UX - clicking the search bar selects all text, making it easy to type a new query without manual clearing.

---

## Testing & Validation

**Manual Testing**:
- ✅ Search by job title returns relevant results
- ✅ Search handles typos (e.g., "kubernets" → "kubernetes")
- ✅ Search handles stemming (e.g., "engineering" → "engineer")
- ✅ Empty search clears results and shows all jobs
- ✅ X/Y count displays correctly during search
- ✅ Enter key triggers search
- ✅ Search button triggers search
- ✅ Clear button resets to full list
- ✅ Select-all on focus works

**Automated Testing**:
- Future: Unit tests for search_jobs function
- Future: Integration tests for search API

---

## Metrics

- **Migration**: 1 (search indexes + trigger)
- **Backend changes**: 2 files (jobs_service.py, jobs_routes.py)
- **Frontend changes**: 2 files (SearchPage.js, SearchPage.css)
- **New model field**: 1 (search_vector TSVECTOR)
- **New indexes**: 2 (GIN tsvector, GIN trigram)

---

## Next Steps → Phase 4

Phase 4 will focus on job tracking and application management.

**Key Features**:
- Add jobs to tracked list ("cart")
- Track page with saved jobs
- Application status tracking (applied, interviewing, etc.)
- Timeline visualization

**Target**: Enable users to track their job application progress

---

## File Structure

```
backend/
├── api/
│   └── jobs_routes.py              # Added q parameter, updated list_jobs
├── db/
│   └── jobs_service.py             # Added get_jobs_with_search function
├── models/
│   └── job.py                      # Added search_vector column
└── alembic/versions/
    └── 6147d489fb1a_add_search_indexes.py

frontend/src/pages/search/
├── SearchPage.js                   # Search state, handlers, UI
└── SearchPage.css                  # Search button styles
```

**Key Files**:
- [jobs_service.py](../../backend/db/jobs_service.py) - `get_jobs_with_search()` function
- [jobs_routes.py](../../backend/api/jobs_routes.py) - `q` parameter handling
- [SearchPage.js](../../frontend/src/pages/search/SearchPage.js) - Search UI and state

---

## Key Learnings

### PostgreSQL Hybrid Search
Combining tsvector (full-text with stemming) and pg_trgm (fuzzy matching) provides comprehensive search without external services. The OR combination catches both semantic matches and typos.

**Reference**: [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)

### Single Query Optimization
Using a computed column in SQL (`... AS matched`) and filtering in Python is more efficient than multiple round-trips, especially for grouped results where we need all companies regardless of match count.

---

## References

**External Documentation**:
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html) - tsvector, tsquery, ts_rank
- [pg_trgm Extension](https://www.postgresql.org/docs/current/pgtrgm.html) - Trigram similarity matching
- [GIN Indexes](https://www.postgresql.org/docs/current/gin.html) - Generalized Inverted Index for full-text

**Related Phases**:
- [Phase 3A: Basic Job Display](./PHASE_3A_SUMMARY.md) - Prerequisite
- [Phase 3B: Sync & Re-Extract](./PHASE_3B_SUMMARY.md) - Prerequisite
