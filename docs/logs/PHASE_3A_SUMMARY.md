# Phase 3A: Basic Job Display

**Status**: Completed
**Date**: January 12, 2026
**Goal**: Build basic infrastructure to display all jobs in the Search nav tab

---

## Overview

Phase 3A creates the foundation for the Search page with a fixed-width left column (320px) and flexible right column. The left column shows company cards with jobs grouped by location (foldable). The right column displays detailed job information with clearly separated sections.

**Included in this phase**:
- Backend API: `GET /api/jobs` (list jobs grouped by company), `GET /api/jobs/{id}` (job details)
- Frontend: Two-column layout with company cards and job details panel
- Company cards with expand/collapse, jobs grouped by location
- Job details with Location, Description, Requirements sections
- Disabled placeholder buttons (Search, Sync All, Re-Extract)

**Explicitly excluded** (deferred to later phases):
- Search functionality (Phase 3C)
- Sync All functionality (Phase 3B)
- Re-Extract functionality (Phase 3B)

---

## Key Achievements

1. **Backend API Endpoints**
   - `GET /api/jobs` returns jobs grouped by company with metadata (logo, display name, count)
   - `GET /api/jobs/{id}` returns full job details including description/requirements
   - JWT authentication required for both endpoints

2. **Company Cards with Location Grouping**
   - Expandable company cards showing ready job count
   - Jobs grouped by location within each company (foldable subsections)
   - Radio button selection for jobs
   - Job titles wrap naturally (no truncation)

3. **Job Details Panel**
   - Clickable job title opens external URL in new tab
   - Three clearly separated sections: Location, Description, Requirements
   - Bold section headers with underline styling
   - Empty state when no job selected

4. **Placeholder UI Elements**
   - Search bar and Search button (disabled)
   - Sync All button (disabled)
   - Re-Extract button (disabled)

---

## API Endpoints

**GET /api/jobs**
- Returns jobs grouped by company for authenticated user
- Response: `{ companies: [...], total_ready: number }`
- Each company includes: name, display_name, logo_url, ready_count, jobs[]

**GET /api/jobs/{job_id}**
- Returns full job details
- Response includes: id, company, title, location, url, status, description, requirements, updated_at
- 404 if job not found or not owned by user

---

## Testing & Validation

**Manual Testing**:
- Page loads with all companies collapsed
- Clicking company header expands/collapses location groups
- Clicking location expands/collapses job list
- Selecting job shows details on right panel
- Job title link opens external URL in new tab
- Disabled buttons visible (Search, Sync All, Re-Extract)

---

## Metrics

- **API Endpoints**: 2 (GET /api/jobs, GET /api/jobs/{id})
- **Frontend Components**: 3 (SearchPage, CompanyCard, JobDetails)
- **CSS**: ~400 lines

---

## Next Steps -> Phase 3B

Phase 3B will enable:
- [Sync All] button functionality (trigger full ingestion)
- [Re-Extract] button functionality (re-process single job)

---

## File Structure

```
backend/
├── api/
│   └── jobs_routes.py           # Job listing endpoints
├── db/
│   └── jobs_service.py          # get_jobs_grouped_by_company, get_job_by_id

frontend/src/pages/
├── SearchPage.js                # Re-export from search/
└── search/
    ├── SearchPage.js            # Main page component
    ├── CompanyCard.js           # Expandable card with location groups
    ├── JobDetails.js            # Right panel with sections
    └── SearchPage.css           # All styling
```

---

## References

**Related Phases**:
- [Phase 2K: Extractor Queue](./PHASE_2K_SUMMARY.md) - Jobs table populated by extraction
- [Phase 3B: Sync & Re-Extract](./PHASE_3B_SUMMARY.md) - Adds Sync All and Re-Extract
- [Phase 3C: Search & Filter](./PHASE_3C_SUMMARY.md) - Adds fuzzy search functionality
