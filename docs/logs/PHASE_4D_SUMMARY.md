# Phase 4D: Track Page - Calendar View

**Status**: ✅ Completed
**Date**: January 28, 2026
**Goal**: Implement calendar tab with visual event display and date navigation

---

## Overview

Phase 4D adds the Calendar tab to the Track page, providing a visual overview of application events across all tracked jobs. Users can see interviews, screenings, and other application milestones on a monthly calendar grid with hover cards showing event details.

**Included in this phase**:
- Calendar tab with month grid view (custom implementation)
- Event indicators on calendar days with stage-based colors
- Hover cards showing event details (company, job title, stage data)
- Click-to-expand day cells showing all events
- Month navigation with caching strategy
- Upcoming and Past events sections below calendar
- Stage data displayed from event.note JSONB field

**Explicitly excluded** (future phases):
- External calendar integration (Google Calendar, Outlook)
- Push notifications/reminders
- Interview scheduling automation
- Week/day view modes

---

## Key Achievements

1. **Calendar Grid Component**
   - Custom month grid with Apple Calendar-inspired design
   - Events displayed inline in day cells (time + company logo + truncated title)
   - Click day to expand and see all events
   - Hover card with full event details (position: fixed for proper z-index)

2. **Date Range Caching**
   - Initial load fetches ±3 months (6 month window)
   - Frontend tracks fetched months to avoid duplicate requests
   - Smart refetching when navigating outside cached range
   - Events merged by ID to prevent duplicates

3. **Stage Details Display**
   - Stage-specific data rendered in both hover cards and event cards
   - Field labels from STAGE_FIELD_LABELS mapping
   - Data read directly from event.note JSONB (not tracking.notes.stages)

4. **Event Data Architecture**
   - Stage data stored directly on tracking_events.note as JSONB
   - Simplified API: single event endpoint handles all stage data
   - No need for separate notes.stages merging logic
   - Migration: `465f573218c3_convert_tracking_events_note_to_jsonb.py`

---

## API Endpoints

**Calendar Events Query**:
- `GET /api/tracked/calendar/events` - Fetch all events across tracked jobs
  - Optional params: `start`, `end` (YYYY-MM-DD)
  - Default: ±3 months from today
  - Returns: events array with job info, range metadata, months list

**Response Structure**:
```json
{
  "events": [{
    "id": 1,
    "tracking_id": 5,
    "event_type": "screening",
    "event_date": "2026-01-22",
    "event_time": "14:00",
    "location": "Zoom",
    "note": {"type": "phone", "with_person": "John", "note": "Initial screen"},
    "job": {"title": "Senior Engineer", "company": "Google", "company_logo_url": "..."}
  }],
  "range": {"start": "2025-10-28", "end": "2026-04-28"},
  "months": ["2025-10", "2025-11", ...]
}
```

---

## Highlights

### Month Grid Implementation

Custom calendar grid without external dependencies (no react-day-picker needed):
- CSS Grid for consistent day cell sizing
- `getCalendarDays()` generates 6-week grid with outside month days
- Stage-based border colors for event pills
- Responsive design with overflow handling

### Hover Card Positioning

Fixed position hover cards with smart placement:
- Positioned relative to mouse cursor
- Boundary detection to prevent off-screen rendering
- Pointer-events: none to prevent flickering
- Visible class toggle for smooth transitions

### Event Data Flow

```
Frontend Form → API Request → Backend
     ↓               ↓           ↓
{event_date,    POST/PATCH    event.note = JSONB
 event_time,    /events       containing all
 location,                    stage data
 note: {...}}
```

Stage data flows directly through event.note, eliminating the two-request pattern and notes.stages complexity.

---

## Testing & Validation

**Manual Testing**:
- ✅ Calendar displays current month on load
- ✅ Events appear on correct dates with stage colors
- ✅ Hover cards show full event details
- ✅ Click to expand day cells with multiple events
- ✅ Month navigation preserves cached events
- ✅ Stage data displays correctly (type, with_person, round, etc.)
- ✅ Location field saves and displays on events

**Automated Testing**:
- Future: Unit tests for calendar event endpoints
- Future: Component tests for CalendarView

---

## Metrics

- **New API endpoints**: 1 (calendar/events)
- **New frontend components**: 1 (CalendarView.js + CalendarView.css)
- **Database migrations**: 1 (note TEXT → JSONB)
- **Lines of CSS**: ~400 (calendar-specific styles)

---

## Project Complete

Phase 4D completes the Job Hunt Tracker application. All core features are implemented:

- **Phase 1**: Authentication & AWS/Vercel deployment
- **Phase 2**: Job ingestion pipeline (crawling, extraction, SSE progress)
- **Phase 3**: Search page with fuzzy search and company grouping
- **Phase 4**: Job tracking with stages, events, resume upload, and calendar

**Potential future enhancements** (not planned):
- Google Calendar sync (OAuth integration)
- iCal export/import
- Push notifications for upcoming events
- Mobile app version
- Multi-user collaboration

---

## File Structure

```
backend/
├── api/
│   └── tracking_routes.py        # Calendar events endpoint
├── models/
│   └── tracking_event.py         # note field as JSONB
└── alembic/versions/
    └── 465f573218c3_convert_tracking_events_note_to_jsonb.py

frontend/src/pages/track/
├── CalendarView.js               # Calendar tab component
├── CalendarView.css              # Calendar-specific styles
├── StageCardForm.js              # Updated for note JSONB
├── StageCard.js                  # Reads stage data from event.note
└── TrackedJobCard.js             # Simplified stage data handling
```

**Key Files**:
- [CalendarView.js](../../frontend/src/pages/track/CalendarView.js) - Calendar tab implementation
- [tracking_routes.py](../../backend/api/tracking_routes.py) - Calendar events endpoint

---

## Key Learnings

### Event-Scoped Stage Data

Storing stage-specific data (type, with_person, round, etc.) directly on the event's `note` JSONB field rather than in job_tracking.notes.stages:
- Simplifies data model: one source of truth per event
- Enables efficient calendar queries without joins to notes
- Single API request for event CRUD operations
- Frontend reads directly from event.note, no mapping needed

### Custom Calendar vs Library

Built custom calendar grid instead of using react-day-picker:
- Full control over layout and styling
- No external dependency
- Simpler integration with hover cards and event rendering
- CSS Grid provides responsive, consistent sizing

---

## References

**External Documentation**:
- [CSS Grid Layout](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout) - Calendar grid implementation
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html) - Event note storage
