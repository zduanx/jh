# Phase 3B: Sync All & Re-Extract

**Status**: ✅ Completed
**Date**: January 13, 2026
**Goal**: Enable "Sync All" to check job status and "Re-Extract" buttons to re-run extraction per job and per company

---

## Overview

Phase 3B enables the action buttons introduced in Phase 3A's UI. The primary features are:

1. **Sync All**: Run extractors to get current job URLs, compare with DB, mark expired jobs. Does NOT insert new jobs - just identifies them. Shows per-company breakdown popup.

2. **Re-Extract** (per job): Re-run extraction on a single job's existing S3 raw HTML WITHOUT re-crawling. Useful after fixing extractors to populate previously empty description/requirements fields.

3. **Re-Extract** (per company): Batch re-extract all READY jobs for a company at once, displayed on company cards.

**Included in this phase**:
- Backend API: `POST /api/jobs/sync`, `POST /api/jobs/re-extract` (unified endpoint)
- Frontend: Enable Sync All and Re-Extract buttons
- Page overlay during sync (blocks content, not nav)
- Popup card showing per-company sync results
- Company-level re-extract with confirmation modal
- Unified API endpoint with request body for single job or company batch

**Explicitly excluded** (deferred to Phase 3C):
- Full-text search with tsvector
- Inserting new jobs (handled by full ingestion on Ingest page)

---

## Key Achievements

1. **Sync All Endpoint**
   - Runs extractors to get current job URLs from career pages
   - Compares with DB to identify existing, new, and expired jobs
   - Marks jobs not found on career pages as EXPIRED
   - Reference: [jobs_routes.py](../../backend/api/jobs_routes.py)

2. **Single Job Re-Extract**
   - Downloads raw HTML from S3 and re-runs company extractor
   - Updates job description and requirements without re-crawling
   - Toast notification shows character counts for feedback
   - Reference: [JobDetails.js](../../frontend/src/pages/search/JobDetails.js)

3. **Company Batch Re-Extract**
   - Re-extracts all READY jobs for a company in one operation
   - Confirmation modal prevents accidental bulk operations
   - Toast shows success/failure counts
   - Reference: [CompanyCard.js](../../frontend/src/pages/search/CompanyCard.js)

4. **Unified Re-Extract Endpoint**
   - Single endpoint `POST /api/jobs/re-extract` with request body
   - Supports both single job (`{job_id: 123}`) and company batch (`{company: "netflix"}`)
   - Unified response format: `{company, total_jobs, successful, failed, results: [...]}`

---

## API Endpoints

**Route**: `POST /api/jobs/sync`
- Sync all jobs: run extractors, compare with DB, mark expired
- Auth: JWT required
- Response: `{companies: [{company, found, existing, new, expired, error}], total_*}`

**Route**: `POST /api/jobs/re-extract`
- Unified endpoint for re-extracting jobs from existing S3 HTML
- Auth: JWT required
- Request body (mutually exclusive):
  - `{job_id: int}` - Re-extract a single job
  - `{company: str}` - Batch re-extract all READY jobs for a company
- Response: `{company, total_jobs, successful, failed, results: [{job_id, title, success, description_length, requirements_length, error}]}`

---

## Highlights

### Company Card Re-Extract Button

Added "Re-Extract" button directly on company cards in the Search page:
- Amber colored button matching the theme
- Confirmation modal: "Re-extract all X jobs for {company}?"
- Loading state with "Extracting..." text
- Success/error toast with job counts

### Unified Endpoint Design

Refactored from two separate endpoints to a single unified endpoint:
- `ReExtractRequest` accepts either `job_id` or `company` (mutually exclusive)
- `ReExtractResponse` provides unified response format for both cases
- `ReExtractJobResult` contains per-job extraction details
- Frontend handles single vs batch by checking `results` array length

---

## Testing & Validation

**Manual Testing**:
- ✅ Sync All shows loading overlay
- ✅ Sync All popup shows per-company breakdown
- ✅ Sync All marks expired jobs correctly
- ✅ Single Re-Extract updates job content
- ✅ Single Re-Extract shows toast with char counts
- ✅ Company Re-Extract confirmation modal works
- ✅ Company Re-Extract shows batch results toast
- ✅ Both re-extract endpoints return consistent format

**Automated Testing**:
- ✅ Netflix extractor snapshot tests
- Future: API endpoint integration tests

---

## Metrics

- **API endpoints added**: 2 (sync, re-extract)
- **UI components updated**: 4 (CompanyCard, JobDetails, SearchPage, SearchPage.css)
- **Response models**: 3 (ReExtractRequest, ReExtractResponse, ReExtractJobResult)

---

## Next Steps → Phase 3C

Phase 3C will add full-text search capabilities to the Search page.

**Key Features**:
- Full-text search with PostgreSQL tsvector
- Search result snippets with highlighted matches
- Advanced filters (company, status, location)

**Target**: Enable users to search job descriptions and requirements by keyword

---

## File Structure

```
backend/
├── api/
│   └── jobs_routes.py           # Sync and re-extract endpoints

frontend/src/pages/
└── search/
    ├── CompanyCard.js           # Company re-extract button and modal
    ├── JobDetails.js            # Single job re-extract button
    ├── SearchPage.js            # Re-extract completion handlers
    └── SearchPage.css           # Modal and toast styles
```

**Key Files**:
- [jobs_routes.py](../../backend/api/jobs_routes.py) - All re-extract and sync endpoints
- [CompanyCard.js](../../frontend/src/pages/search/CompanyCard.js) - Company-level re-extract UI
- [JobDetails.js](../../frontend/src/pages/search/JobDetails.js) - Single job re-extract UI

---

## Key Learnings

### S3 URL Parsing
Parsing S3 URLs (`s3://bucket/key`) requires stripping the protocol and splitting on first `/` to separate bucket from key.

### Batch Operations with Confirmation
For destructive or bulk operations, confirmation modals prevent accidental triggers and improve UX by showing what will happen.

### RESTful API Design
POST endpoints should use request body instead of path parameters. This allows for:
- Mutually exclusive parameters (job_id OR company)
- Easier extensibility (add new fields without changing URL)
- Cleaner URL structure

---

## References

**External Documentation**:
- [boto3 S3 get_object](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/get_object.html) - S3 download API
- [React useState](https://react.dev/reference/react/useState) - State management for modals and loading states
