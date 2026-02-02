# System Design Document

## Project Overview

**Name:** Job Hunt Tracker
**Purpose:** Full-stack job application tracking system
**Goals:**
1. Build practical job hunting tool
2. Practice system design
3. Learn AI-assisted development
4. Deploy to AWS

---

## Technology Stack

### Frontend
- **Framework:** React 18+
- **OAuth:** @react-oauth/google
- **Routing:** React Router v6
- **HTTP:** fetch API
- **Build:** Create React App
- **Hosting:** Vercel (auto-deploy from GitHub)

### Backend
- **Framework:** FastAPI
- **Language:** Python 3.11+
- **OAuth:** google-auth
- **JWT:** python-jose
- **Lambda Adapter:** Mangum (FastAPI → Lambda)
- **Hosting:** AWS Lambda

### Infrastructure
- **Frontend CDN:** Vercel (global edge network)
- **Backend:** AWS Lambda (serverless compute)
- **API Gateway:** AWS API Gateway (HTTP API)
- **Database:** PostgreSQL (Neon)
- **Queue:** AWS SQS FIFO
- **Storage:** AWS S3 (raw HTML)
- **Real-time:** Server-Sent Events (SSE)

---

## Phase 1: Authentication (POC)

```
┌──────────────────────────────────────┐
│   React Frontend (Vercel)            │
│   - Static files via CDN             │
└─────────────┬────────────────────────┘
              │ HTTPS API calls
              ↓
┌──────────────────────────────────────┐
│   AWS API Gateway + Lambda           │
│   - OAuth validation                 │
│   - JWT creation                     │
└─────────────┬────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│   Google OAuth API                   │
└──────────────────────────────────────┘
```

### Authentication Flow
1. User clicks "Login with Google"
2. Google OAuth popup → user logs in
3. Google returns ID token to React
4. React → POST /auth/google with token
5. Lambda validates token with Google
6. Lambda creates JWT, returns to React
7. React stores JWT in localStorage

### Security
- HTTPS everywhere (Vercel + API Gateway auto)
- JWT signed with HS256
- Short expiration (1 day for POC)
- CORS configured properly
- Email whitelist (only authorized emails)

---

## Phase 2: Job Ingestion Pipeline

**Goals:**
1. Generate job URLs from company career pages
2. Crawl job pages to get raw HTML
3. Extract structured job data from HTML
4. Track ingestion progress with real-time updates
5. Deduplicate content to avoid redundant extraction

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface (React)                      │
│  - Settings Page: Configure companies & filters                    │
│  - Ingest Control: Dry-run preview → Confirm → Start              │
│  - Real-time Status: SSE updates during ingestion                  │
└────────────────┬────────────────────────────────────────────────────┘
                 │ HTTPS API calls + SSE stream
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      API Gateway + Lambda                           │
│                                                                     │
│  POST /api/ingest/preview  → Dry-run, return job counts           │
│  POST /api/ingest/start    → Create run, async invoke worker      │
│  GET  /api/ingest/progress → SSE stream for real-time updates     │
└────────────────┬────────────────────────────────────────────────────┘
                 │ Async (Lambda invoke)
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     IngestionWorker Lambda                          │
│  1. Run extractors → get job URLs per company                      │
│  2. UPSERT to DB (all non-expired → PENDING)                       │
│  3. Mark expired jobs                                              │
│  4. SendMessageBatch to CrawlerQueue.fifo                          │
│     - MessageGroupId: company (rate limiting)                      │
│     - MessageDeduplicationId: {run_id}-{company}-{external_id}     │
└────────────────┬────────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  CrawlerQueue.fifo (SQS FIFO)                       │
│  MessageGroupId = company → only 1 msg/company in-flight           │
└────────────────┬────────────────────────────────────────────────────┘
                 │ Triggers (BatchSize: 1)
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     CrawlerWorker Lambda                            │
│  1. Crawl URL (3 retries, 1s backoff)                             │
│  2. SimHash check (skip if Hamming distance ≤ 3)                   │
│  3. S3 save → raw/{company}/{external_id}.html                    │
│  4. Update job (READY or SKIPPED)                                  │
│  5. Circuit breaker: 5 failures per company → stop                 │
│  6. sleep(1) → rate limiting                                       │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ├─→ S3 Bucket: raw/{company}/{external_id}.html
                 └─→ Database: jobs.status = READY/SKIPPED/ERROR
```

### Status Flows

**Ingestion Run:**
```
pending → initializing → ingesting → finished
                    ↘            ↘
                     → error      → error
```

**Job:**
```
pending → ready (crawled, SimHash changed)
    ↘
     → skipped (SimHash similar - no change)
     → error (crawl/S3 failed)
     → expired (URL 404)
```

### SimHash Deduplication

To avoid expensive extraction when job content hasn't changed:
1. Crawler computes SimHash (64-bit fuzzy hash) of HTML
2. Compare with stored SimHash in DB
3. If similar (Hamming distance ≤ 3): Skip extraction, mark as 'skipped'
4. If different: Save to S3, mark as 'ready'

See [ADR-017](./DECISIONS.md#adr-017-simhash-for-raw-content-deduplication)

### Real-Time Progress (SSE)

```
GET /api/ingestion/progress/{run_id}?token=<jwt>
Accept: text/event-stream
```

| Event | When | Data |
|-------|------|------|
| `status` | pending/initializing/terminal | Run status string |
| `all_jobs` | First poll when ingesting | Full job map by company |
| `update` | Subsequent polls | Only changed jobs (diff) |

- Polls DB every 3 seconds
- Auto-reconnects every 29s (API Gateway limit)
- On reconnect: sends `all_jobs` (full state)
- During session: sends `update` (diff only)

See [ADR-016](./DECISIONS.md#adr-016-sse-for-real-time-progress-updates), [ADR-018](./DECISIONS.md#adr-018-sse-update-strategy---full-state-on-connect-diffs-during-session)

### Database Schema

**ingestion_runs:**
- id, user_id, status, error_message, created_at, finished_at
- run_metadata (JSONB): per-company failure counts for circuit breaker

**jobs:**
- id, run_id, user_id, company, external_id, url, status
- simhash (BIGINT), raw_s3_url, title, location, description, requirements
- error_message, created_at, updated_at
- UNIQUE(user_id, company, external_id)

---

## Phase 3: Search Page

**Goals:**
1. Display all jobs with company-grouped layout
2. Fuzzy search across titles and descriptions
3. Sync All: Update job metadata without re-crawling
4. Re-Extract: Re-run extraction from S3 for individual jobs

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Search Page (React)                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  [search query__________________] [Search] [Clear]        [Sync All]   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────┬─────────────────────────────────────────────────────┐  │
│  │  COMPANIES      │  JOB DETAILS                                        │  │
│  │  ┌───────────┐  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Google    │  │  │  Senior K8s Engineer ↗                     │    │  │
│  │  │ 8/45      │  │  │  Mountain View, CA                         │    │  │
│  │  │ ● Job 1   │  │  │  Description: ...                          │    │  │
│  │  │ ○ Job 2   │  │  │  Requirements: ...                         │    │  │
│  │  │ ⌄ 5 more  │  │  │                          [Re-Extract]      │    │  │
│  │  └───────────┘  │  └─────────────────────────────────────────────┘    │  │
│  └─────────────────┴─────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────────────────────┘
                 │ HTTPS API calls
                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      API Gateway + Lambda                                    │
│                                                                              │
│  GET  /api/jobs              → List all jobs grouped by company             │
│  GET  /api/jobs?q=...        → Fuzzy search jobs                            │
│  GET  /api/jobs/{id}         → Get full job details                         │
│  POST /api/jobs/sync         → Sync All: update metadata, mark expired      │
│  POST /api/jobs/re-extract   → Re-extract from S3 (job_id or company)       │
└────────────────┬────────────────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PostgreSQL (Neon)                                   │
│  - tsvector for full-text search (title + description)                      │
│  - pg_trgm for fuzzy/typo tolerance on title                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### UI Layout

**Left Column (1/4):** Company cards
- Company logo, name, job counts (matched/total during search)
- Expand/collapse to show jobs
- Radio buttons for job selection
- Re-Extract button per company

**Right Column (3/4):** Job details
- Clickable title → opens job URL
- Location, Description, Requirements
- Re-Extract button per job

### Hybrid Search

Uses PostgreSQL native search (no external services):

1. **tsvector**: Full-text search with stemming on title (weight A) + description (weight B)
2. **pg_trgm**: Fuzzy search on title for typo tolerance (similarity > 0.2)

Single optimized query returns all jobs with computed `matched` flag:
```sql
SELECT *,
    (search_vector @@ plainto_tsquery('english', :query)
     OR similarity(title, :query) > 0.2) AS matched
FROM jobs
WHERE user_id = :user_id AND status = 'ready'
```

See [ADR-014](./DECISIONS.md#adr-014-use-hybrid-text-search-postgresql-full-text--fuzzy)

### Sync All vs Re-Extract

| Operation | Sync All | Re-Extract |
|-----------|----------|------------|
| Purpose | Update metadata from company APIs | Re-run extraction from S3 |
| Network | Calls company career APIs | Downloads from S3 |
| Updates | title, location, url, updated_at | description, requirements |
| Marks expired | Yes (URLs not in results) | No |
| Changes status | No (preserves READY/SKIPPED) | No |

---

## Phase 4: Job Tracking

**Goals:**
1. Track interesting jobs from Search page
2. Manage tracked jobs with archive/delete functionality
3. Progress through application stages
4. Calendar view for interview scheduling (Phase 4C)

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Track Page (React)                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  [Calendar]  [Manage]                                                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  GOOGLE (3 jobs)                                                        ││
│  │  ┌─────────────────────────────────────────────────────────────────┐   ││
│  │  │  Senior Engineer        Seattle    interested    [▼] [📦] [🗑]  │   ││
│  │  └─────────────────────────────────────────────────────────────────┘   ││
│  │  ┌─────────────────────────────────────────────────────────────────┐   ││
│  │  │  Staff Engineer         NYC        applied       [▼] [📦] [🗑]  │   ││
│  │  └─────────────────────────────────────────────────────────────────┘   ││
│  │                                                                         ││
│  │  ARCHIVED (1 job)                                                       ││
│  │  ┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐   ││
│  │  ┆  Data Scientist         Remote     rejected           [↩]      ┆   ││
│  │  └╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└────────────────┬────────────────────────────────────────────────────────────┘
                 │ HTTPS API calls
                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      API Gateway + Lambda                                    │
│                                                                              │
│  GET    /api/tracked/ids       → Lightweight IDs for Search page cache      │
│  GET    /api/tracked           → Full list with job details for Track page  │
│  POST   /api/tracked           → Add job to tracking                        │
│  PATCH  /api/tracked/{id}      → Update (archive, stage, notes)             │
│  DELETE /api/tracked/{id}      → Remove from tracking                       │
└────────────────┬────────────────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PostgreSQL (Neon)                                   │
│  job_tracking: user_id, job_id, stage, is_archived, notes, timestamps       │
│  UNIQUE(user_id, job_id) - each user tracks a job once                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tracking Stages

```
interested → applied → screening → interviewing → offer → accepted
                                                      ↘
                                                       → rejected
```

### RESTful API Design

Single resource `/api/tracked` with unified PATCH for updates:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/tracked/ids` | Lightweight IDs for Search page |
| GET | `/api/tracked` | Full list with job details |
| POST | `/api/tracked` | Add job to tracking |
| PATCH | `/api/tracked/{id}` | Update any field (archive, stage, notes) |
| DELETE | `/api/tracked/{id}` | Remove from tracking |

### Archive vs Delete

| Action | Behavior | When Available |
|--------|----------|----------------|
| Archive | Sets `is_archived=true`, preserves data | Any stage |
| Delete | Removes tracking record | Only "interested" stage |

Delete is restricted to prevent accidental removal of jobs with application progress.

### Database Schema

**job_tracking:**
- id, user_id, job_id (FK to jobs)
- stage (ENUM: interested, applied, screening, interview, reference, offer, accepted, declined, rejected)
- is_archived (BOOLEAN)
- notes (JSONB) - job metadata only: salary, location, general_note, resume_filename
- resume_s3_url (TEXT)
- tracked_at, updated_at

**tracking_events:**
- id, tracking_id (FK to job_tracking)
- event_type (ENUM: applied, screening, interview, reference, offer, accepted, declined, rejected)
- event_date, event_time, location
- note (JSONB) - stage-specific data: {type, with_person, round, interviewers, amount, note, ...}
- created_at

Stage data (e.g., screening type=phone, with_person="John") is stored directly on the event's `note` JSONB field, not in job_tracking.notes. This keeps event-specific data with the event and enables efficient calendar queries.

See [ADR-023](./DECISIONS.md#adr-023-separate-events-table-for-calendar-tracking) for calendar events design.

### Expanded Card Layout

```
+------------------------------------------------------------------------------+
| [Logo] Senior Software Engineer        San Francisco         [▼][📦][🗑]    |
+------------------------------------------------------------------------------+
|                                                                              |
|  DESCRIPTION (scrollable)                                                    |
|  +------------------------------------------------------------------------+  |
|  | We are looking for a Senior Software Engineer...                       |  |
|  +------------------------------------------------------------------------+  |
|                                                                              |
|  RESUME                                                                      |
|  [resume.pdf]  [👁 Preview] [⬇ Download] [⬆ Replace]                        |
|                                                                              |
|  Salary: [__$150k-180k__]   Location: [__Remote__]   Note: [__fits well__]  |
|                                                                              |
|  PROGRESS                                              [Mark Rejected]       |
|                                                                              |
|      ●──────────●──────────○──────────○──────────○                           |
|    applied    screening  interview  reference   offer                        |
|                                                   +──○ accepted              |
|   +--------+ +--------+ +--------+ +--------+    +──○ declined               |
|   |Jan 21  | |Jan 23  | |  [+]   | | locked |                                |
|   |Referral| |Phone   | |  Add   | |        |  +--------+                    |
|   |John D. | |w/Sarah | |        | |        |  | locked |                    |
|   |[Edit]  | |[Edit]  | |        | |        |  |        |                    |
|   +--------+ +--------+ +--------+ +--------+  +--------+                    |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Stage Workflow

```
interested → applied → screening → interview → reference → offer → accepted
                                                                ↘→ declined
(rejected can occur at any stage - locks the card)
```

### Stage Card States

| State | Appearance | Actions |
|-------|------------|---------|
| Completed | Date + summary + [Edit] | Can edit, latest can delete |
| Next | [+ Add] button | Can add |
| Locked | Greyed out | None |
| Rejected | Read-only, greyed | Only "Undo" on rejected event |

### Resume Upload (Direct-to-S3)

```
Frontend  →  Backend     Frontend  →  S3
   │            │           │          │
   │ GET URL    │           │          │
   │───────────→│           │          │
   │ presigned  │           │          │
   │←───────────│           │          │
   │            │  PUT file directly   │
   │────────────────────────────────→  │
   │ POST confirm           │          │
   │───────────→│           │          │
```

S3 key: `resumes/{user_id}/{tracking_id}.pdf` (re-upload overwrites)

See [ADR-024](./DECISIONS.md#adr-024-presigned-urls-for-resume-upload-direct-to-s3)

---

## Phase 5: Stories (Behavioral Interview Prep)

**Goals:**
1. Store behavioral interview stories using STAR format
2. Tag and categorize stories by question type
3. Quick navigation between questions

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Stories Page (React)                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stories                                                               │  │
│  │  Behavioral interview preparation with STAR format                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────┬─────────────────────────────────────────────────────┐  │
│  │  QUESTIONS      │  STORY CARDS                                        │  │
│  │  (280px)        │  (flex 1)                                           │  │
│  │  ┌───────────┐  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Tell me   │  │  │ Question: [Tell me about a time...     ] [×]│    │  │
│  │  │ about a   │  │  │ Type: [Leadership ▼]  Tags: [team] [+]      │    │  │
│  │  │ time when │  │  │                                              │    │  │
│  │  │ you led   │  │  │ ┌────────────────────────────────────────┐  │    │  │
│  │  │ a project │  │  │ │ Overview (read-only)                   │  │    │  │
│  │  │ [leader.] │  │  │ │ I was leading a team of 5...           │  │    │  │
│  │  ├───────────┤  │  │ │ My responsibility was to ensure...     │  │    │  │
│  │  │ Describe  │◀─┼──┼─│ I started by analyzing...              │  │    │  │
│  │  │ a time    │  │  │ │ We delivered on time and under...      │  │    │  │
│  │  │ you had   │  │  │ └────────────────────────────────────────┘  │    │  │
│  │  │ conflict  │  │  │                                              │    │  │
│  │  │ [conflict]│  │  │ Situation: [editable textarea]               │    │  │
│  │  ├───────────┤  │  │ Task: [editable textarea]                    │    │  │
│  │  │ What is   │  │  │ Action: [editable textarea]                  │    │  │
│  │  │ your      │  │  │ Result: [editable textarea]                  │    │  │
│  │  │ greatest  │  │  │                                              │    │  │
│  │  │ weakness? │  │  │                         [Cancel] [Save]      │    │  │
│  │  └───────────┘  │  └─────────────────────────────────────────────┘    │  │
│  │                 │                                                      │  │
│  │  [+ New Story]  │  ┌─────────────────────────────────────────────┐    │  │
│  │                 │  │ STORY CARD #2 ...                           │    │  │
│  │  [5 stories]    │  └─────────────────────────────────────────────┘    │  │
│  └─────────────────┴─────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────────────────────┘
                 │ HTTPS API calls
                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      API Gateway + Lambda                                    │
│                                                                              │
│  GET    /api/stories           → List all stories (optional: ?type, ?tag)   │
│  GET    /api/stories/{id}      → Get single story                           │
│  POST   /api/stories           → Create new story                           │
│  PATCH  /api/stories/{id}      → Update story fields                        │
│  DELETE /api/stories/{id}      → Delete story                               │
└────────────────┬────────────────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PostgreSQL (Neon)                                   │
│  stories: user_id, question, type, tags[], STAR fields, timestamps          │
│  Indexes: user_id, type, GIN on tags[]                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Schema

**stories:**
- id, user_id (FK to users)
- question (TEXT) - the behavioral question
- type (TEXT) - category (leadership, conflict, teamwork, etc.)
- tags (TEXT[]) - PostgreSQL array for flexible tagging
- situation, task, action, result (TEXT) - STAR format fields
- created_at, updated_at

### UI Behavior

- **Left panel**: Question list with full text wrapping, click scrolls to card
- **Right panel**: Scrollable story cards with smooth scroll behavior
- **Overview**: Read-only, concatenates STAR fields with newlines
- **Tags**: Enter or Space creates token, × removes
- **Dirty state**: Cancel/Save buttons appear when changes detected
- **Delete**: Confirmation modal required

### Question Types

- leadership, conflict, teamwork, problem-solving
- failure, success, communication, time-management

---

## Key Design Decisions

All architectural decisions documented in [DECISIONS.md](./DECISIONS.md):

- **ADR-014**: Hybrid text search (PostgreSQL full-text + fuzzy)
- **ADR-016**: SSE for real-time progress updates
- **ADR-017**: SimHash for raw content deduplication
- **ADR-018**: SSE update strategy (full state on connect, diffs during session)
- **ADR-020**: SQS FIFO with MessageGroupId for crawler rate limiting
