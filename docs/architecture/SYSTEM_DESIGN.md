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

## Phase 4: Job Tracking (Future)

- Add jobs to tracked list ("cart")
- Track page with saved jobs
- Application status tracking (applied, interviewing, etc.)
- Timeline visualization
- Analytics dashboard

---

## Key Design Decisions

All architectural decisions documented in [DECISIONS.md](./DECISIONS.md):

- **ADR-014**: Hybrid text search (PostgreSQL full-text + fuzzy)
- **ADR-016**: SSE for real-time progress updates
- **ADR-017**: SimHash for raw content deduplication
- **ADR-018**: SSE update strategy (full state on connect, diffs during session)
- **ADR-020**: SQS FIFO with MessageGroupId for crawler rate limiting
