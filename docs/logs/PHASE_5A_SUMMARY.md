# Phase 5A: Stories - Behavioral Interview Prep

**Status**: ✅ Completed
**Date**: February 2, 2026
**Goal**: Build database, API, and UI for storing behavioral interview stories using STAR format

---

## Overview

Phase 5A introduces a new "Stories" feature for behavioral interview preparation. Users can create, organize, and review personal stories structured using the STAR format (Situation, Task, Action, Result). Stories are tagged and categorized to help users quickly find relevant examples during interview prep.

The UI follows a 1:3 column layout: left sidebar for question navigation, right panel for viewing/editing story content. Each story card shows the question, type, tags, a read-only Overview (concatenated STAR fields), and editable STAR textareas with Cancel/Save buttons that appear when changes are detected.

**Included in this phase**:
- Database schema: `stories` table with STAR format fields
- API endpoints: CRUD operations for stories
- Stories nav tab in sidebar
- Question list navigation (click scrolls to card)
- Story card with Overview + STAR fields
- Tag input with Enter/Space to create tokens
- Delete confirmation modal

**Explicitly excluded** (future phases):
- AI-assisted story generation
- Story sharing/export
- Practice mode with mock interviews
- Audio/video recording of answers

---

## Key Achievements

### 1. Database Schema
- Created `stories` table with STAR format fields
- PostgreSQL ARRAY type for tags with GIN index
- Migration: [951da046d96d_create_stories_table.py](../../backend/alembic/versions/951da046d96d_create_stories_table.py)

### 2. Backend API
- Full CRUD endpoints at `/api/stories`
- Filter by type or tag query params
- Routes: [story_routes.py](../../backend/api/story_routes.py)

### 3. Frontend Components
- 1:3 column layout with question list and story cards
- Read-only Overview section concatenating STAR fields
- Tag input creates tokens on Enter or Space
- Cancel/Save buttons appear when form is dirty
- Delete button with confirmation modal

### 4. Navigation Integration
- Added Stories tab to sidebar with MdMenuBook icon
- Added /stories route to App.js

---

## Database Schema

**stories**:
| Field | Type | Description |
|-------|------|-------------|
| `id` | SERIAL | Primary key |
| `user_id` | BIGINT | FK to users, cascades on delete |
| `question` | TEXT | The behavioral question |
| `type` | VARCHAR(50) | Question category (leadership, conflict, teamwork, etc.) |
| `tags` | TEXT[] | PostgreSQL array of tags |
| `situation` | TEXT | STAR: Context and background |
| `task` | TEXT | STAR: What was your responsibility |
| `action` | TEXT | STAR: What steps did you take |
| `result` | TEXT | STAR: What was the outcome |
| `created_at` | TIMESTAMP | When story was created |
| `updated_at` | TIMESTAMP | Auto-updated on changes |

**Indexes**:
- `idx_stories_user_id` - Filter by user
- `idx_stories_type` - Filter by question type
- `idx_stories_tags` (GIN) - Efficient tag searching

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/stories` | List all stories (optional: `?type=`, `?tag=`) |
| GET | `/api/stories/{id}` | Get single story |
| POST | `/api/stories` | Create new story |
| PATCH | `/api/stories/{id}` | Update story fields |
| DELETE | `/api/stories/{id}` | Delete story |

---

## Highlights

### UI Layout
- **Left panel (280px)**: Question list with full text wrapping, click to scroll to card
- **Right panel (flex 1)**: Scrollable story cards with smooth scroll-to behavior
- **Question field**: Single-line input with "Question:" label
- **Tags**: Token-based input, Enter or Space creates tag, click × to remove

### Technical Details
- `scrollIntoView({ behavior: 'smooth', block: 'start' })` for card navigation
- 50ms delay before scroll to ensure DOM is ready after state update
- `box-sizing: border-box` on textareas to prevent overflow
- Fetch only on mount (removed `activeStoryId` dependency to prevent re-fetching)

### Question Types
- leadership, conflict, teamwork, problem-solving
- failure, success, communication, time-management

---

## Testing & Validation

### Manual Testing
- [x] Create new story → appears in list
- [x] Edit story fields → Cancel reverts, Save persists
- [x] Delete story → confirmation modal → removed from list
- [x] Click question in left nav → scrolls to card
- [x] Tags: Enter/Space creates token, × removes
- [x] Overview updates as STAR fields change

---

## File Structure

```
backend/
├── models/
│   └── story.py                              # Story SQLAlchemy model
├── api/
│   └── story_routes.py                       # CRUD API routes
├── main.py                                   # Added story_router
└── alembic/versions/
    └── 951da046d96d_create_stories_table.py  # Migration

frontend/src/
├── App.js                                    # Added /stories route
├── components/
│   └── Sidebar.js                            # Added Stories nav item
└── pages/stories/
    ├── StoriesPage.js                        # Main page with 1:3 layout
    ├── StoriesPage.css                       # Page styles
    ├── StoryCard.js                          # Individual story card
    └── StoryCard.css                         # Card styles
```

**Key Files**:
- [story.py](../../backend/models/story.py) - Story model with STAR fields
- [story_routes.py](../../backend/api/story_routes.py) - API endpoints
- [StoriesPage.js](../../frontend/src/pages/stories/StoriesPage.js) - Main page component
- [StoryCard.js](../../frontend/src/pages/stories/StoryCard.js) - Story card with form

---

## Next Steps → Phase 5B

Potential enhancements for future iterations:

- Search/filter stories by keyword
- Practice mode with timed responses
- AI-assisted story suggestions
- Export stories to PDF/markdown
- Story templates for common question types

---

## References

**External Documentation**:
- [STAR Interview Method](https://www.themuse.com/advice/star-interview-method) - STAR format explanation
- [PostgreSQL Arrays](https://www.postgresql.org/docs/current/arrays.html) - Tags storage
