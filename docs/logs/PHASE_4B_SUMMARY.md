# Phase 4B: Track Page - Display & Manage

**Status**: ✅ Complete
**Date**: January 22, 2026
**Goal**: Build Track page for viewing and managing tracked jobs with archive/delete functionality

---

## Overview

Phase 4B creates the Track page where users view and manage their tracked jobs. The page features two tabs (Calendar placeholder for 4C, Manage active), jobs grouped by company with expandable cards, and archive/delete functionality with confirmation modals.

The backend exposes a RESTful API for listing tracked jobs with full details and updating tracking status. The frontend displays jobs in a company-grouped layout with visual distinction between active and archived jobs.

**Included in this phase**:
- Track nav tab in sidebar
- Two-tab layout (Calendar placeholder, Manage active)
- Jobs grouped by company with expandable cards
- Company logos on headers and job cards
- Archive/unarchive with confirmation modal
- Delete with confirmation modal
- Archived section with visual distinction

**Explicitly excluded** (deferred to Phase 4C):
- Calendar tab implementation
- Edit notes functionality
- Change stage dropdown
- Resume upload/download
- Sorting/filtering

---

## Key Achievements

1. **RESTful Tracking API**
   - Added GET /api/tracked for full job list with details
   - Added PATCH /api/tracked/{id} for unified updates
   - Single PATCH endpoint handles archive, stage, notes (extensible for 4C)

2. **Track Page with Company Grouping**
   - Jobs displayed in expandable cards grouped by company
   - Company logos on section headers and job cards (with letter fallback)
   - Active jobs first, archived section at bottom
   - Fold/unfold to show description and notes

3. **Archive Workflow**
   - Separate archive flag from delete (is_archived boolean)
   - Archived jobs visually distinguished (dashed border, muted colors)
   - Unarchive action to restore jobs

---

## API Endpoints

All tracking endpoints follow RESTful conventions on `/api/tracked`:

| Method | Endpoint | Purpose | Phase |
|--------|----------|---------|-------|
| GET | `/api/tracked/ids` | Lightweight IDs for Search page | 4A |
| GET | `/api/tracked` | Full list with job details | 4B |
| POST | `/api/tracked` | Add job to tracking | 4A |
| PATCH | `/api/tracked/{id}` | Update tracking (archive, stage, notes) | 4B/4C |
| DELETE | `/api/tracked/{id}` | Remove from tracking | 4A |

**Route**: `GET /api/tracked`
- Returns all tracked jobs with full job details (title, company, company_logo_url, location, description, url)
- Sorted: active first, archived last, then by tracked_at desc
- Auth: JWT required

**Route**: `PATCH /api/tracked/{id}`
- Update one or more fields: is_archived, stage, notes (all optional)
- Validates stage against enum values
- Auth: JWT required

---

## Highlights

### Unified PATCH Endpoint
Instead of separate `/archive`, `/stage`, `/notes` endpoints, a single PATCH accepts any combination of optional fields. This makes the API cleaner and extensible for Phase 4C.

### SQLAlchemy Relationship for Eager Loading
Added `job` relationship to JobTracking model to enable joinedload in the list query, avoiding N+1 queries when fetching tracked jobs with their details.

### Archive vs Delete Distinction
- **Delete**: Only allowed for "interested" stage (prevents accidental removal of jobs with progress)
- **Archive**: Available for any stage, moves job to archived section but preserves data

---

## Testing & Validation

**Manual Testing**:
- ✅ GET /api/tracked returns jobs with full details
- ✅ PATCH /api/tracked/{id} updates is_archived
- ✅ Archived jobs sorted to bottom of list
- ✅ Invalid stage value returns 422

**Automated Testing**:
- Future: Unit tests for tracking routes
- Future: Integration tests for track/untrack flow

---

## Metrics

- **API endpoints added**: 2 (GET /tracked, PATCH /tracked/{id})
- **Frontend components**: 3 (TrackPage, TrackedJobCard, TrackPage.css)
- **Model changes**: 1 (job relationship on JobTracking)

---

## Next Steps → Phase 4C & 4D

**Phase 4C - Card Edit Features**:
- Edit notes functionality (inline edit in expanded card)
- Change stage dropdown with workflow stages
- Resume upload/download per job
- Sorting and filtering options

**Phase 4D - Calendar View**:
- Calendar tab implementation with event display
- Schedule interviews and track deadlines
- Event management for job applications

**Target**: Phase 4C completes card edit workflow, Phase 4D adds calendar visualization

---

## File Structure

```
backend/
├── api/
│   └── tracking_routes.py       # Updated: GET /tracked, PATCH /{id}
└── models/
    └── job_tracking.py          # Updated: job relationship

frontend/src/
├── components/
│   └── Sidebar.js               # Updated: Add Track tab
└── pages/track/
    ├── TrackPage.js             # NEW: Main page with tabs
    ├── TrackPage.css            # NEW: Styles (trk- prefix)
    └── TrackedJobCard.js        # NEW: Expandable card
```

**Key Files**:
- [tracking_routes.py](../../backend/api/tracking_routes.py) - API endpoints with GET/PATCH
- [job_tracking.py](../../backend/models/job_tracking.py) - Model with job relationship

---

## Key Learnings

### RESTful API Design
Using a single PATCH endpoint with optional fields is cleaner than multiple specific endpoints. The frontend can send only the fields it wants to update.

### SQLAlchemy Eager Loading
The `joinedload` option with a defined relationship prevents N+1 queries when fetching related data, important for list endpoints.

---

## References

**External Documentation**:
- [SQLAlchemy Relationships](https://docs.sqlalchemy.org/en/20/orm/relationships.html) - Relationship loading strategies
- [FastAPI PATCH](https://fastapi.tiangolo.com/tutorial/body-updates/) - Partial updates pattern
