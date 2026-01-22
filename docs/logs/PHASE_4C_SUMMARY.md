# Phase 4C: Track Page - Full Features

**Status**: 📋 Planning
**Date**: January 21, 2026
**Goal**: Complete job tracking with notes, stages, events, resume management, and calendar view

---

## Overview

Phase 4C completes the job tracking experience with all planned features. Users can manage their entire job application workflow: track stages, add notes, log events, upload customized resumes, and view upcoming events in a calendar.

**Included in this phase**:
- Edit notes (per job)
- Stage management with dropdown
- Events management (add, edit, delete events)
- Calendar view showing upcoming events across all jobs
- Resume upload/download per job
- Sorting and filtering

**Explicitly excluded** (future considerations):
- Analytics dashboard
- Email/calendar integration
- Interview scheduling
- Reminders/notifications

---

## Database Schema

Uses the two-table design from Phase 4A (see [ADR-023](../architecture/DECISIONS.md#adr-023-separate-events-table-vs-jsonb-for-job-tracking)):

- `job_tracking`: Stores tracking metadata (stage, notes, resume)
- `tracking_events`: Stores individual events (interviews, calls, etc.)

The separate events table enables efficient calendar queries:
```sql
SELECT te.*, jt.job_id, j.title, j.company
FROM tracking_events te
JOIN job_tracking jt ON te.tracking_id = jt.id
JOIN jobs j ON jt.job_id = j.id
WHERE jt.user_id = :user_id
  AND te.event_date BETWEEN :start AND :end
ORDER BY te.event_date, te.event_time;
```

---

## Features

### 1. Stage Dropdown

**UI**:
- Dropdown showing current stage with color indicator
- On change: API call to update, optimistic UI update

**Stage Colors**:
| Stage | Color |
|-------|-------|
| interested | Gray |
| applied | Blue |
| screening | Yellow |
| interviewing | Orange |
| offer | Green |
| accepted | Dark Green |
| rejected | Red |
| archived | Muted Gray |

### 2. Notes Management

**UI Options**:
- Inline edit: Click notes area to edit in place
- Modal edit: Click edit icon to open modal with textarea

**Behavior**:
- Auto-save with debounce (500ms) or explicit save button
- Show "Saving..." indicator

### 3. Events Management

**Add Event Modal**:
- Event type dropdown (phone_screen, technical, onsite, etc.)
- Date picker (native `<input type="date">`)
- Time picker (native `<input type="time">`, optional)
- Location text field
- Notes textarea

**Events List**:
- Chronological list within each tracked job card
- Edit/delete buttons per event
- Visual indicator for past vs upcoming events

### 4. Calendar View

**Design Decision**: Start with native date inputs, add `react-day-picker` if calendar UI needed.

**Simple Upcoming Events List** (Phase 4C MVP):
```
┌─────────────────────────────────────────────────────────────────┐
│  Upcoming Events                                                │
├─────────────────────────────────────────────────────────────────┤
│  Jan 22, 2026 • 2:00 PM                                        │
│  Technical Interview - Google Senior Engineer                   │
│  Location: Zoom                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Jan 25, 2026 • 9:00 AM                                        │
│  Onsite - Amazon Cloud Architect                               │
│  Location: Seattle HQ                                           │
└─────────────────────────────────────────────────────────────────┘
```

**Future Enhancement**: Month calendar view with `react-day-picker`

### 5. Resume Upload/Download

**Upload Flow**:
1. Click "Upload Resume" button on job card
2. File picker opens (accept: .pdf, .docx)
3. File uploads to S3: `resumes/{user_id}/{job_id}/{filename}`
4. `job_tracking.resume_s3_url` updated
5. UI shows filename with download/replace/remove options

**Download Flow**:
1. Click resume filename or download icon
2. Backend generates presigned S3 URL (1 hour expiry)
3. Browser downloads file

**UI States**:
- No resume: [Upload Resume] button
- Has resume: "resume.pdf" link + [Download] + [Replace] + [Remove]

### 6. Sorting & Filtering

**Sort Options**:
- Tracked date (newest/oldest)
- Company name (A-Z)
- Stage (workflow order)
- Next event date

**Filter Options**:
- By stage (multi-select chips)
- By company (dropdown)

---

## API Endpoints

### Events CRUD

**POST /api/tracked/{tracking_id}/events**
Create new event.

```json
Request:
{
  "event_type": "technical",
  "event_date": "2026-01-22",
  "event_time": "14:00",
  "location": "Zoom",
  "note": "System design round"
}

Response:
{
  "id": 1,
  "tracking_id": 5,
  "event_type": "technical",
  "event_date": "2026-01-22",
  "event_time": "14:00",
  "location": "Zoom",
  "note": "System design round",
  "created_at": "2026-01-21T10:00:00Z"
}
```

**GET /api/tracked/events?start=2026-01-01&end=2026-01-31**
Get all events in date range (for calendar).

```json
Response:
{
  "events": [
    {
      "id": 1,
      "event_type": "technical",
      "event_date": "2026-01-22",
      "event_time": "14:00",
      "location": "Zoom",
      "note": "System design round",
      "job": {
        "id": 123,
        "title": "Senior Engineer",
        "company": "google"
      }
    }
  ]
}
```

**PATCH /api/tracked/events/{event_id}**
Update event.

**DELETE /api/tracked/events/{event_id}**
Delete event.

### Tracking Updates

**PATCH /api/tracked/{id}**
Update tracked job (stage, notes).

```json
Request:
{
  "stage": "applied",
  "notes": "Applied via website on Jan 21"
}

Response:
{
  "id": 1,
  "stage": "applied",
  "notes": "Applied via website on Jan 21",
  "updated_at": "2026-01-21T12:00:00Z"
}
```

### Resume

**POST /api/tracked/{id}/resume**
Upload resume (multipart/form-data).

```json
Response:
{
  "resume_s3_url": "s3://bucket/resumes/123/456/resume.pdf",
  "filename": "resume.pdf"
}
```

**GET /api/tracked/{id}/resume**
Get presigned download URL.

```json
Response:
{
  "download_url": "https://s3.amazonaws.com/...",
  "filename": "resume.pdf",
  "expires_in": 3600
}
```

**DELETE /api/tracked/{id}/resume**
Remove resume.

---

## Frontend Components

### New/Updated Files

```
frontend/src/pages/track/
├── TrackPage.js              # Main page with sorting/filtering
├── TrackPage.css             # Enhanced styles
├── TrackedJobCard.js         # Job card with events, notes, stage
├── StageDropdown.js          # Stage selector with colors
├── NotesEditor.js            # Inline or modal notes editing
├── EventsList.js             # List of events per job
├── AddEventModal.js          # Modal for adding/editing events
├── UpcomingEvents.js         # Calendar/list of upcoming events
└── ResumeUpload.js           # Resume upload/download component
```

---

## Implementation Order

1. **Stage dropdown**: Simple, high impact
2. **Notes editing**: Inline with auto-save
3. **Events CRUD**: Add/edit/delete events
4. **Upcoming events list**: Simple date-sorted list
5. **Sorting & filtering**: Client-side initially
6. **Resume upload**: S3 integration
7. **Resume download**: Presigned URLs
8. **Calendar view**: If time permits, add react-day-picker

---

## Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Notes editing: inline vs modal? | Start with inline, auto-save |
| Calendar library? | Start with native inputs, add react-day-picker later if needed |
| Events storage: JSONB vs table? | Separate table per [ADR-023](../architecture/DECISIONS.md#adr-023-separate-events-table-vs-jsonb-for-job-tracking) |

---

## Next Steps → Phase 5 (Future)

Potential Phase 5 features:
- Analytics dashboard (applications per week, response rates)
- Month calendar view with react-day-picker
- Export to CSV/spreadsheet
- Email tracking integration
- Reminders and notifications
