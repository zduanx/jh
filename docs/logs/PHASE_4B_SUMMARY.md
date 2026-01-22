# Phase 4B: Track Page - Display & Remove

**Status**: 📋 Planning
**Date**: January 15, 2026
**Goal**: Build Track page skeleton with job display and removal functionality

---

## Overview

Phase 4B creates the Track page where users view and manage their tracked jobs. This is a skeleton implementation focusing on basic display and removal - advanced features come in Phase 4C.

**Included in this phase**:
- Track nav tab in sidebar
- Track page with tracked jobs list
- Basic job card display (title, company, stage, tracked date)
- Remove from tracked (with confirmation)
- Empty state when no tracked jobs

**Explicitly excluded** (deferred to Phase 4C):
- Edit notes
- Change stage (dropdown/workflow)
- Resume upload/download
- Detailed job view
- Sorting/filtering

---

## UI Design

### Sidebar Navigation

Add "Track" tab:
- Icon: Bookmark or star
- Position: After "Search" tab
- Badge: Count of tracked jobs (optional)

### Track Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Track                                                          │
│  Manage your tracked job applications                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [Google Logo] Senior Software Engineer                  │   │
│  │  Google • Seattle, WA                                    │   │
│  │  Stage: Interested         Tracked: Jan 15, 2026         │   │
│  │                                            [Remove]      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [Amazon Logo] Cloud Architect                          │   │
│  │  Amazon • New York, NY                                   │   │
│  │  Stage: Applied            Tracked: Jan 14, 2026         │   │
│  │                                            [Remove]      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Total: 2 tracked jobs                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Empty State

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                          📭                                     │
│                   No Tracked Jobs                               │
│                                                                 │
│     Track jobs from the Search page to manage your              │
│     applications here.                                          │
│                                                                 │
│                    [Go to Search]                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Remove Confirmation

Simple confirmation modal:
- "Remove from tracked?"
- "This will remove {job title} from your tracked list. The job will still be available in Search."
- [Cancel] [Remove]

---

## API Endpoints

### GET /api/tracked
List all tracked jobs for user.

**Response**:
```json
{
  "tracked_jobs": [
    {
      "id": 1,
      "job_id": 123,
      "stage": "interested",
      "notes": null,
      "tracked_at": "2026-01-15T10:00:00Z",
      "job": {
        "id": 123,
        "title": "Senior Software Engineer",
        "company": "google",
        "location": "Seattle, WA",
        "url": "https://..."
      }
    }
  ],
  "total": 1
}
```

### DELETE /api/tracked/{id}
Remove job from tracked list.

**Response**:
```json
{
  "success": true
}
```

---

## Frontend Components

### New Files

```
frontend/src/pages/track/
├── TrackPage.js          # Main page component
├── TrackPage.css         # Styles
└── TrackedJobCard.js     # Individual job card
```

### Component Structure

**TrackPage.js**:
- Fetch tracked jobs on mount
- Loading/error/empty states
- List of TrackedJobCard components

**TrackedJobCard.js**:
- Company logo
- Job title (clickable → opens URL)
- Company name, location
- Stage badge
- Tracked date
- Remove button

---

## Implementation Plan

1. **Backend**: GET /api/tracked endpoint
2. **Backend**: DELETE /api/tracked/{id} endpoint
3. **Frontend**: Add Track tab to Sidebar
4. **Frontend**: Create TrackPage component
5. **Frontend**: Create TrackedJobCard component
6. **Frontend**: Add remove confirmation modal
7. **Frontend**: Wire up navigation routing

---

## Next Steps → Phase 4C

Phase 4C will complete the tracking feature set with notes, stages, and resume management.

**Key Features**:
- Edit notes (inline or modal)
- Change stage (dropdown with workflow stages)
- Resume upload per job
- Resume download
- Stage timeline/visualization
- Sorting and filtering options

**Target**: Full job application tracking workflow
