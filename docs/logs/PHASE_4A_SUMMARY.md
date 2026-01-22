# Phase 4A: Tracked Jobs - Database & Add to Track

**Status**: ✅ Completed
**Date**: January 22, 2026
**Goal**: Design database schema for job tracking and enable adding/removing jobs from Search page

---

## Overview

Phase 4A establishes the foundation for job tracking functionality. Users can track jobs they're interested in, moving them from the Search page into a personal tracking list. This phase focuses on database design and the Track/Untrack action on the Search page.

The implementation uses a two-table design: `job_tracking` for tracking metadata and `tracking_events` for calendar-queryable events. This enables efficient date-range queries for the calendar feature planned in Phase 4C.

**Included in this phase**:
- Database schema: `job_tracking` and `tracking_events` tables
- API endpoints: get tracked IDs, add to tracking, remove from tracking
- Frontend: Track/Untrack button on job details panel
- Visual indicators for tracked jobs (text color in list, border on details card)

**Explicitly excluded** (deferred to Phase 4B/4C):
- Track page UI (4B)
- Stage management, notes, events, resume upload, calendar (4C)

---

## Key Achievements

1. **Two-Table Database Design**
   - Created `job_tracking` for tracking metadata (stage, notes, resume)
   - Created `tracking_events` for calendar-queryable events
   - Reference: [ADR-023](../architecture/DECISIONS.md#adr-023-separate-events-table-vs-jsonb-for-job-tracking)

2. **PostgreSQL Enum for Stage**
   - Used native PostgreSQL ENUM type for `tracking_stage`
   - Values: interested, applied, screening, interviewing, offer, accepted, rejected
   - Required `values_callable` in SQLAlchemy to map Python enum to lowercase DB values

3. **Frontend State Caching**
   - Single API call on page load fetches all tracked job IDs
   - Local cache updates on track/untrack (no refetch needed)
   - Optimizes performance by avoiding per-job queries

---

## Database Schema

**job_tracking**:
- Stores user's tracked jobs with stage and notes
- Unique constraint on (user_id, job_id) prevents duplicate tracking
- `is_archived` is separate from stage - job can be archived at any stage
- Reference: [ADR-023](../architecture/DECISIONS.md#adr-023-separate-events-table-vs-jsonb-for-job-tracking)

| Field | Type | Description |
|-------|------|-------------|
| `id` | SERIAL | Primary key |
| `user_id` | BIGINT | FK to users, cascades on delete |
| `job_id` | INTEGER | FK to jobs, cascades on delete |
| `stage` | ENUM | tracking_stage enum (default: interested) |
| `is_archived` | BOOLEAN | Whether job is archived (default: false) |
| `notes` | TEXT | General notes about the job |
| `resume_s3_url` | TEXT | S3 path to customized resume |
| `tracked_at` | TIMESTAMP | When user added to tracking |
| `updated_at` | TIMESTAMP | Auto-updated on changes |

**tracking_events**:
- Stores individual events (interviews, calls, etc.)
- Date index enables efficient calendar queries
- Cascades delete when parent tracking is removed

| Field | Type | Description |
|-------|------|-------------|
| `id` | SERIAL | Primary key |
| `tracking_id` | INTEGER | FK to job_tracking |
| `event_type` | VARCHAR(50) | phone_screen, technical, onsite, etc. |
| `event_date` | DATE | Date of event (required) |
| `event_time` | TIME | Time of event (optional) |
| `location` | TEXT | Location/meeting link |
| `note` | TEXT | Notes about the event |
| `created_at` | TIMESTAMP | When event was created |

---

## API Endpoints

**Route**: `GET /api/tracked/ids`
- Get all tracked job IDs with their tracking info for current user
- Response: `{ "tracked": { "123": { "tracking_id": 5, "stage": "interested" } } }`
- Used to populate frontend cache on Search page load

**Route**: `POST /api/tracked`
- Add a job to user's tracked list (stage defaults to "interested")
- Request: `{ "job_id": 123 }`
- Response: `{ "tracking_id": 5, "job_id": 123, "stage": "interested", "tracked_at": "..." }`
- Errors: 404 (job not found), 409 (already tracked)

**Route**: `DELETE /api/tracked/{tracking_id}`
- Remove job from tracking by tracking_id
- Only allowed when stage is "interested" (prevents accidental deletion)
- Response: `{ "success": true }`
- Errors: 404 (not found), 400 (stage is not "interested")

---

## Highlights

### Track Button UX
Button states in JobDetails component:
- **Not tracked** → "Interested" button (blue) → click to add to tracking
- **Interested stage** → "Untrack" button (green, red on hover) → click to remove
- **Other stages** → Stage text (gray, read-only, e.g., "Applied")

### PostgreSQL Enum Mapping
SQLAlchemy's `PgEnum` uses enum member names by default (uppercase), but PostgreSQL expects the values (lowercase). Fixed with:
```python
values_callable=lambda e: [member.value for member in e]
```

### Visual Indicators
- Job list (left panel): Green text color for tracked jobs
- Job details (right panel): Green border when tracked

---

## Testing & Validation

**Manual Testing**:
- ✅ Track a job from Search page
- ✅ Untrack a job (only when stage is "interested")
- ✅ Visual indicator appears in job list
- ✅ Green border appears on job details card
- ✅ State persists across page refresh
- ✅ Duplicate tracking prevented (409 error)

**Automated Testing**:
- Future: Unit tests for tracking routes
- Future: Integration tests for track/untrack flow

---

## Metrics

- **Tables added**: 2 (job_tracking, tracking_events)
- **API endpoints**: 3 (GET /ids, POST, DELETE)
- **Frontend components modified**: 3 (SearchPage, JobDetails, CompanyCard)
- **PostgreSQL enum values**: 7 (tracking stages)

---

## Next Steps → Phase 4B

Phase 4B will build the Track page to display and manage tracked jobs.

**Key Features**:
- Track nav tab in sidebar
- List of tracked jobs with stage indicators
- Archive functionality

**Target**: Enable users to view their tracked jobs in dedicated page

---

## File Structure

```
backend/
├── models/
│   ├── __init__.py              # Updated exports
│   ├── job_tracking.py          # NEW: JobTracking model with TrackingStage enum
│   └── tracking_event.py        # NEW: TrackingEvent model
├── api/
│   └── tracking_routes.py       # NEW: Tracking API routes
└── alembic/versions/
    └── 48935213746f_...py       # NEW: Migration with enum

frontend/src/pages/search/
├── SearchPage.js                # Updated: trackedJobs state, fetch, handlers
├── JobDetails.js                # Updated: Track/Untrack button
├── CompanyCard.js               # Updated: tracked indicator in job list
└── SearchPage.css               # Updated: tracked styles
```

**Key Files**:
- [job_tracking.py](../../backend/models/job_tracking.py) - JobTracking model with TrackingStage enum
- [tracking_routes.py](../../backend/api/tracking_routes.py) - GET/POST/DELETE endpoints
- [Migration](../../backend/alembic/versions/48935213746f_create_job_tracking_and_tracking_events.py) - Creates tables with PostgreSQL enum

---

## Key Learnings

### PostgreSQL Enum with SQLAlchemy
When using Python enums with PostgreSQL, the enum member names vs values distinction matters. Use `values_callable` to control what gets sent to the database.

### Frontend State Caching
Fetching all tracked IDs in one call and caching locally is more efficient than querying per-job. Cache updates optimistically on mutations.

---

## References

**Architecture Decision**:
- [ADR-023: Separate Events Table vs JSONB](../architecture/DECISIONS.md#adr-023-separate-events-table-vs-jsonb-for-job-tracking)

**External Documentation**:
- [SQLAlchemy PostgreSQL ENUM](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#enum-types) - Enum type handling
