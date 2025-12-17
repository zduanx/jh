# Phase 2D: Dry Run Implementation (Stage 2)

**Status**: 📋 Planning
**Date**: TBD
**Goal**: Enable URL extraction preview to validate company configurations before full ingestion

---

## Overview

Phase 2D implements Stage 2 of the ingestion workflow, providing a dry run feature that extracts job URLs without crawling full job details. This validation step allows users to preview exactly which jobs will be ingested and verify their company configurations are correct before committing to the full crawl.

**Included in this phase**:
- Dry run backend endpoint integrating Phase 2A extractors
- Stage 2 UI with expandable URL preview
- Per-company extraction results with error handling
- Confirmation modal before starting full ingestion
- Partial success support (some companies succeed, others fail)

**Explicitly excluded** (deferred to Phase 2E):
- Job archiving (Stage 3)
- Full job crawling (Stage 4)
- Ingestion runs persistence
- Results display (Stage 5)

---

## Key Achievements

### 1. Extractor Integration
- **Reuse Phase 2A framework**: Registry pattern, title filtering, standardized metadata
- **Dry run vs full crawl**: Extract URLs + basic metadata only (not descriptions)
- **Extractor factory**: Route URLs to appropriate extractor by domain pattern
- Reference: [PHASE_2A_SUMMARY.md](./PHASE_2A_SUMMARY.md)

### 2. Backend Dry Run Endpoint
- **Route**: POST /api/ingest/dry-run
- **Process**: Iterate companies, extract URLs, apply title filters, return grouped results
- **Error handling**: Capture per-company failures without blocking others
- **Partial success**: Return results even if some companies fail

### 3. Stage 2 Preview UI
- **Summary statistics**: Total URLs, company count, status breakdown
- **Expandable company cards**: Show first 10 URLs, "... and N more" for large lists
- **Color-coded badges**: Green (success), red (error), gray (in progress)
- **Navigation**: Previous (back to Stage 1), Rerun (refresh), Start Ingestion (to Stage 3)

### 4. Validation & Error Feedback
- **Early issue detection**: Invalid URLs, no jobs found, rate limiting, timeouts
- **Clear error messages**: Per-company error display with recovery guidance
- **User-friendly recovery**: Easy return to Stage 1 to fix configuration

### 5. Confirmation Modal
- **Purpose**: Prevent accidental ingestion runs
- **Content**: Total URL count, duration warning, archiving notice, cancellation warning
- **Actions**: Cancel (stay on Stage 2) or Confirm (proceed to Stage 3)

---

## API Endpoints

**POST `/api/ingest/dry-run`**:
- Purpose: Extract job URLs for configured companies without full crawl
- Request: User's company configurations (from user_company_settings table)
- Response: Array of results per company (name, URL count, status, URLs, error_message)
- Validation: At least one company required
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
- Add 3 companies → Run dry run → Verify URLs displayed
- Invalid URL → Verify error message shown
- No title filters → Verify all jobs shown
- Overly restrictive filters → Verify "no jobs found" warning
- Company with 500+ jobs → Verify "and N more" displays correctly
- Very slow career site → Verify timeout after 30 seconds
- Mixed success (2/5 companies) → Verify partial results shown
- Confirmation modal → Verify displays correctly, cancel works

**Automated Testing**:
- Future: Unit tests for extractor factory routing
- Future: Integration tests for dry run endpoint
- Future: Frontend component tests for results display
- Future: End-to-end test for Stage 1 → Stage 2 flow

---

## Metrics

- **API Endpoints**: 1 (POST /api/ingest/dry-run)
- **Frontend Components**: 4 (Stage 2, results, loader, confirmation modal)
- **Error Types Handled**: 4 (invalid URL, no jobs, rate limiting, timeout)
- **Timeout Thresholds**: 30s per company, 5min total
- **Target Completion**: Stage 2 fully functional with preview and validation

---

## Next Steps → Phase 2E

Phase 2E will implement **Stages 3-5**:
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
│   └── ingest_routes.py     # Add POST /api/ingest/dry-run
└── tests/
    └── test_dry_run.py      # Dry run endpoint tests

frontend/src/pages/Ingest/
├── Stage2_Preview.js        # Main Stage 2 component
├── DryRunResults.js         # Results display component
├── DryRunLoader.js          # Loading state component
└── ConfirmIngestionModal.js # Confirmation dialog
```

**Key Files**:
- [ingest_routes.py](../../backend/api/ingest_routes.py) - Dry run endpoint
- [Stage2_Preview.js](../../frontend/src/pages/Ingest/Stage2_Preview.js) - Stage 2 UI

---

## Key Learnings

### Dry Run Pattern
Preview operations before execution reduces errors and builds user confidence. Small upfront cost (extracting URLs) prevents large waste (full crawl with bad config).

### Partial Success Strategy
Independent processing of items (companies) with graceful degradation provides better UX than all-or-nothing failures. Users get value even when some operations fail.

### Error Transparency
Clear, actionable error messages with recovery guidance reduce support burden and empower users to self-serve fixes.

---

## References

**External Documentation**:
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html) - User company settings storage
- [React State Management](https://react.dev/learn/managing-state) - Stage workflow state

---

**Status**: Ready for Phase 2E
