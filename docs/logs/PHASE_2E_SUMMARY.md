# Phase 2E: Dry Run Implementation (Stage 2)

**Status**: ✅ Complete
**Date**: December 22, 2025
**Goal**: Enable URL extraction preview to validate company configurations before full ingestion

---

## Overview

Phase 2E implements Stage 2 of the ingestion workflow, providing a dry run feature that extracts job URLs without crawling full job details. This validation step allows users to preview exactly which jobs will be ingested and verify their company configurations are correct before committing to the full crawl.

**Included in this phase**:
- Dry run backend endpoint integrating Phase 2A extractors
- Stage 2 UI with expandable URL preview
- Per-company extraction results with error handling
- Confirmation modal before starting full ingestion
- Partial success support (some companies succeed, others fail)

**Explicitly excluded** (deferred to Phase 2F):
- Job archiving (Stage 3)
- Full job crawling (Stage 4)
- Ingestion runs persistence
- Results display (Stage 5)

---

## Key Achievements

### 1. Async HTTP Migration (httpx)
- **Migration**: Replaced `requests` library with `httpx` async client
- **Parallelism**: `ThreadPoolExecutor` → `asyncio.gather()` for concurrent extraction
- **Scope**: All 6 extractors + base class + dry-run endpoint converted to async
- **ADR**: [ADR-015](../architecture/DECISIONS.md#adr-015-use-httpx-with-asyncio-for-http-requests)

### 2. Extractor Integration
- **Reuse Phase 2A framework**: Registry pattern, title filtering, standardized metadata
- **Dry run vs full crawl**: Extract URLs + basic metadata only (not descriptions)
- **Extractor factory**: Route URLs to appropriate extractor by domain pattern
- Reference: [PHASE_2A_SUMMARY.md](./PHASE_2A_SUMMARY.md)

### 3. Backend Dry Run Endpoint
- **Route**: POST /api/ingestion/dry-run
- **Process**: Iterate companies, extract URLs, apply title filters, return grouped results
- **Error handling**: Capture per-company failures without blocking others
- **Partial success**: Return results even if some companies fail

### 4. Stage 2 Preview UI
- **Summary statistics**: Total URLs, company count, status breakdown
- **Two-column layout**: Company cards (left 1/4) | job details (right 3/4)
- **Expandable job lists**: Show first 10 jobs, "... and N more" for large lists
- **Color-coded status**: Green (success), red (error), gray (pending)
- **Inline filter editing**: Edit filters directly from Stage 2 via FilterModal
- **Navigation**: Back / Save Settings / Dry Run (Rerun) / Start Ingestion

### 5. Validation & Error Feedback
- **Early issue detection**: Invalid URLs, no jobs found, rate limiting, timeouts
- **Clear error messages**: Per-company error display with recovery guidance
- **Dirty state tracking**: Warn when filters changed, require save before dry-run
- **Stale results warning**: Show when results don't match current filter settings

### 6. Confirmation Modal
- **Purpose**: Prevent accidental ingestion runs
- **Content**: Company count, job count, duration warning
- **Actions**: Cancel (stay on Stage 2) or Confirm (proceed to Stage 3)

### 7. Filter Normalization Fix
- **Bug**: `include=[]` caused all jobs to be excluded (treated as "match none")
- **Fix**: Backend normalizes `[]` to `None` in `TitleFilters.from_dict()`
- **API contract**: Backend always returns `[]` (never `null`) for consistent frontend handling
- **Comparison**: Both stages use `normalizeFilters()` to sort arrays before comparison

---

## API Endpoints

**POST `/api/ingestion/dry-run`**:
- Purpose: Extract job URLs for configured companies without full crawl
- Request: User's enabled company settings (from user_company_settings table)
- Response: Dict mapping company_name to result (status, counts, included_jobs, excluded_jobs)
- Validation: At least one enabled company required
- Auth: JWT required

Reference: [API_DESIGN.md](../architecture/API_DESIGN.md)

---

## Highlights

### Why Separate Dry Run from Full Ingestion?
**Alternative**: Start ingestion immediately without preview

**Chosen**: Dedicated dry run stage with URL preview

**Rationale**: Users want verification before committing, prevents wasted crawl time on misconfigured filters, builds trust through transparency, allows iteration on filters

### Why Show URLs Instead of Just Counts?
**Alternative**: Display only job counts per company

**Chosen**: Show expandable URL lists (first 10 visible)

**Rationale**: Users can spot-check URLs to verify correctness, helps debug filter issues, increases confidence, minimal performance cost

### Why Allow Partial Success?
**Alternative**: Fail entire dry run if any company fails

**Chosen**: Return partial results with per-company errors

**Rationale**: One misconfigured company shouldn't block others, users can start ingestion for successful companies, can fix failed companies later

### Error Handling Strategy
**Per-company isolation**: Each company's extraction runs independently, failures don't cascade

**Timeout thresholds**: 30 seconds per company, 5 minutes total request

**User guidance**: Clear recovery instructions for each error type (invalid URL, no jobs found, rate limiting, timeout)

---

## Testing & Validation

**Manual Testing**:

*Success cases*:
- Add 3 companies → Run dry run → Verify URLs displayed
- No title filters → Verify all jobs shown
- Company with 100+ jobs → Verify "and N more" displays correctly
- Confirmation modal → Verify displays correctly, cancel works
- Edit filters in Stage 2 → Save → Rerun → Verify new results

*Failure/edge cases*:
- No enabled companies → Verify 400 error with clear message
- Network disconnected → Verify error message per company
- Overly restrictive filters → Verify 0 included jobs shown
- Edit filters without saving → Verify "Save settings first" warning
- Run dry-run → Edit filters → Verify "Rerun" warning (stale results)
- Click Start Ingestion without dry-run → Verify button disabled
- Mixed success (some companies fail) → Verify partial results shown

**Automated Testing**:
- `api/__tests__/test_dry_run.py` - 9 integration tests for dry-run endpoint
  - Auth validation (401 without token)
  - No enabled companies (400 error)
  - Single/multiple company success
  - Partial failure handling
  - Error mapping (timeout, connect, rate limit, format errors)

---

## Metrics

- **API Endpoints**: 1 (POST /api/ingestion/dry-run)
- **Frontend Components**: 2 (Stage2Preview with inline confirmation modal, reuses FilterModal)
- **Error Types Handled**: 4 (timeout, connect error, rate limiting, format error)
- **Automated Tests**: 9 integration tests

---

## Next Steps → Phase 2F

Phase 2F will implement **Stages 3-5**:
- Stage 3: Job archiving logic (remove outdated jobs)
- Stage 4: Async job crawling via SQS + Lambda
- Stage 5: Results display and ingestion history
- Ingestion runs table for persistence
- Stale run detection and recovery

**Target**: Complete end-to-end ingestion workflow with async processing

---

## File Structure

```
backend/
├── api/
│   ├── ingestion_routes.py          # Dry-run endpoint
│   └── __tests__/test_dry_run.py    # Integration tests
└── extractors/
    └── config.py                    # TitleFilters normalization

frontend/src/pages/ingest/
├── Stage2Preview.js                 # Main Stage 2 component (includes confirmation modal)
├── Stage2Preview.css                # Styles
└── components/
    └── FilterModal.js               # Reused from Stage 1
```

**Key Files**:
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - Dry run endpoint
- [Stage2Preview.js](../../frontend/src/pages/ingest/Stage2Preview.js) - Stage 2 UI
- [config.py](../../backend/extractors/config.py) - TitleFilters with normalization

---

## Key Learnings

### Async vs Threading for I/O-bound Work
Python's GIL (Global Interpreter Lock) allows only one thread to execute Python bytecode at a time, but releases during I/O operations. For HTTP requests, both `ThreadPoolExecutor` and `asyncio` provide parallelism, but asyncio is more efficient with modern async libraries like httpx.

Reference: [python-fastapi.md](../learning/python-fastapi.md#pythons-gil-global-interpreter-lock)

### Dry Run Pattern
Preview operations before execution reduces errors and builds user confidence. Small upfront cost (extracting URLs) prevents large waste (full crawl with bad config).

### Partial Success Strategy
Independent processing of items (companies) with graceful degradation provides better UX than all-or-nothing failures. Users get value even when some operations fail.

### Error Transparency
Clear, actionable error messages with recovery guidance reduce support burden and empower users to self-serve fixes.

### API Boundary Normalization
When data has multiple valid representations (e.g., `[]` vs `null` for "include all"), normalize at API boundaries:
- Backend always returns consistent representation (`[]` in API responses)
- Backend handles conversion internally (`[]` → `None` for filtering logic)
- Frontend doesn't need conditional logic for different representations

---

## References

**External Documentation**:
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html) - User company settings storage
- [React State Management](https://react.dev/learn/managing-state) - Stage workflow state
- [httpx Documentation](https://www.python-httpx.org/) - Async HTTP client
