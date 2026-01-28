# Phase 4C: Track Page - Stepper, Stage Cards & Resume

**Status**: ✅ Completed
**Date**: January 28, 2026
**Goal**: Add progress tracking with stage cards, events, and resume upload for tracked jobs

---

## Overview

Phase 4C enhances the Track page with a visual progress stepper, per-stage cards with structured data, and resume upload functionality. Users can track their application journey through stages (applied → screening → interview → reference → offer), with each stage storing specific data. The design supports marking jobs as rejected at any point (locks further modifications) and uploading a resume per tracked job.

**Included in this phase**:
- Horizontal progress stepper with 5 stages + terminal branches (accepted/declined)
- Per-stage mini cards with stage-specific fields
- Event endpoints (POST, PATCH, DELETE) with auto-rollback
- Mark rejected functionality (locks card, undo available)
- Job metadata inputs (salary, location, general note)
- Resume upload/download via presigned URLs (direct-to-S3)

**Explicitly excluded** (deferred to Phase 4D):
- Calendar tab with month view
- Upcoming events aggregated view

---

## Key Achievements

1. **Database Migration**
   - Converted `job_tracking.notes` column from TEXT to JSONB for job metadata
   - Added new stage enum values: `interview`, `reference`, `declined`
   - Created `tracking_events` table with `event_type` enum
   - Converted `tracking_events.note` from TEXT to JSONB for stage-specific data
   - Migrations: `f5c246f90db1_phase4c_notes_jsonb_stage_enum.py`, `465f573218c3_convert_tracking_events_note_to_jsonb.py`

2. **Event-Based Stage Progression**
   - Separate `tracking_events` table for calendar-friendly queries
   - Stage auto-updates when events are created
   - Auto-rollback when latest event is deleted
   - Reference: [ADR-023](../architecture/DECISIONS.md#adr-023-separate-events-table-for-calendar-tracking)

3. **Resume Upload with Presigned URLs**
   - Direct-to-S3 upload bypasses Lambda memory/timeout constraints
   - Three endpoints: GET upload-url, POST confirm, GET download-url
   - No delete needed - re-upload overwrites
   - Reference: [ADR-024](../architecture/DECISIONS.md#adr-024-presigned-urls-for-resume-upload-direct-to-s3)

4. **Schema Codegen**
   - Backend Pydantic schemas → frontend JavaScript for form rendering
   - Script: `backend/scripts/generate_tracking_schema.py`
   - Integrated into dev workflow: `jcodegen`, `jready`, `jpushapi`

5. **Frontend Components**
   - ProgressStepper, StageCard, StageCardForm, JobMetadataInputs
   - RejectModal with undo capability
   - ResumeSection with upload/preview/download/replace

---

## Database Schema

**tracking_events table**:
- Stores discrete events (applied, screening, interview, etc.)
- `event_date`, `event_time`, `location` per event
- `note` (JSONB) - stage-specific data: {type, with_person, round, interviewers, amount, note, ...}
- Latest event determines current stage
- Only latest event is deletable (enables undo/rollback)

**job_tracking.notes JSONB structure**:
- Job metadata only: `salary`, `location`, `general_note`, `resume_filename`
- Stage-specific data is stored on event.note, not here

---

## API Endpoints

**Event Endpoints**:
- `POST /api/tracked/{id}/events` - Create event (updates stage)
- `PATCH /api/tracked/{id}/events/{event_id}` - Update event details
- `DELETE /api/tracked/{id}/events/{event_id}` - Delete latest event (auto-rollback)

**Resume Endpoints**:
- `GET /api/tracked/{id}/resume/upload-url` - Get presigned PUT URL
- `POST /api/tracked/{id}/resume/confirm` - Save S3 key to database
- `GET /api/tracked/{id}/resume/url` - Get presigned GET URL (preview/download)

---

## Highlights

### Permissive Schema Validation

Backend implements permissive parsing for JSONB notes - if data doesn't match schema, returns defaults rather than failing. This allows:
- Reading old/malformed data gracefully
- Updates to fix invalid data by overwriting

### Stage Card State Machine

| State | Appearance | Actions |
|-------|------------|---------|
| Completed | Date + summary | Edit, Delete (if latest) |
| Next | [+ Add] button | Add new event |
| Locked | Greyed out | None |
| Rejected | Read-only | Only Undo available |

### Resume Upload Flow

1. Frontend validates file (PDF only, max 5MB)
2. GET presigned URL from backend (5 min expiry)
3. PUT file directly to S3
4. POST confirm to save S3 key in database

---

## Testing & Validation

**Manual Testing**:
- ✅ Create/edit/delete events with stage auto-update
- ✅ Reject job locks all stage cards
- ✅ Undo rejection restores previous state
- ✅ Resume upload/preview/download/replace
- ✅ Metadata inputs save on blur

**Automated Testing**:
- Future: Unit tests for event endpoints
- Future: Integration tests for stage rollback

---

## Metrics

- **New database table**: 1 (tracking_events)
- **New API endpoints**: 6 (3 event, 3 resume)
- **New frontend components**: 6 (stepper, card, form, modal, inputs, resume)
- **Migration files**: 1

---

## Next Steps → Phase 4D

Phase 4D will implement the Calendar view:
- Calendar tab with month view (react-day-picker)
- Events from tracking_events table
- Visual indicators for upcoming interviews/deadlines

---

## File Structure

```
backend/
├── api/
│   └── tracking_routes.py        # Event + resume endpoints
├── models/
│   ├── job_tracking.py           # TrackingStage enum, resume_s3_url
│   └── tracking_event.py         # TrackingEvent model, EventType enum, note JSONB
├── scripts/
│   └── generate_tracking_schema.py  # Pydantic → JS codegen
└── alembic/versions/
    ├── f5c246f90db1_phase4c_notes_jsonb_stage_enum.py
    └── 465f573218c3_convert_tracking_events_note_to_jsonb.py

frontend/src/pages/track/
├── TrackPage.js                  # Event + resume handlers
├── TrackedJobCard.js             # Expanded layout
├── ProgressStepper.js            # Horizontal stepper
├── StageCard.js                  # Per-stage mini card
├── StageCardForm.js              # Edit form modal
├── JobMetadataInputs.js          # Salary/location/note
├── RejectModal.js                # Rejection confirmation
└── ResumeSection.js              # Upload/preview/download
```

**Key Files**:
- [tracking_routes.py](../../backend/api/tracking_routes.py) - All tracking API endpoints
- [TrackedJobCard.js](../../frontend/src/pages/track/TrackedJobCard.js) - Main card component

---

## Key Learnings

### Presigned URL Pattern

Direct-to-S3 uploads via presigned URLs bypass Lambda constraints (memory, timeout, API Gateway 10MB limit). Trade-off: 3 endpoints instead of 1, but enables unlimited file sizes.

**Reference**: [ADR-024](../architecture/DECISIONS.md#adr-024-presigned-urls-for-resume-upload-direct-to-s3)

### Event-Based vs JSONB-Only Tracking

Using a separate events table (instead of just JSONB) enables efficient calendar queries by date range. JSONB still used for metadata that doesn't need date-based queries.

**Reference**: [ADR-023](../architecture/DECISIONS.md#adr-023-separate-events-table-for-calendar-tracking)

---

## References

**External Documentation**:
- [AWS S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html) - Direct upload pattern
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html) - Structured notes storage
