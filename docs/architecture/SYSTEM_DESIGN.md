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

## Phase 1 Architecture (Current - POC - Serverless)

```
┌──────────────────────────────────────┐
│   React Frontend (Vercel)            │
│   - Static files via CDN             │
│   - yourapp.vercel.app               │
└─────────────┬────────────────────────┘
              │ HTTPS API calls
              ↓
┌──────────────────────────────────────┐
│   AWS API Gateway                    │
│   - HTTPS endpoint                   │
│   - CORS enabled                     │
└─────────────┬────────────────────────┘
              │
              ↓
┌──────────────────────────────────────┐
│   AWS Lambda (Python + FastAPI)     │
│   - OAuth validation                 │
│   - JWT creation                     │
│   - API endpoints                    │
└─────────────┬────────────────────────┘
              │
              ↓
┌──────────────────────────────────────┐
│   Google OAuth API                   │
└──────────────────────────────────────┘
```

### Detailed Request Flow

**Initial Page Load:**
```
1. User visits: https://yourapp.vercel.app
2. Vercel CDN serves: index.html + bundle.js (React code)
3. Browser downloads and runs React
4. React renders Login page
```

**Authentication Flow:**
```
1. User clicks "Login with Google"
2. Google OAuth popup → user logs in
3. Google returns ID token to React (in browser)
4. React → POST https://api-gateway-url.aws.com/api/auth/google
       Body: {token: "google_id_token"}
5. API Gateway → Lambda
6. Lambda (FastAPI) validates token with Google
7. Lambda creates our JWT
8. Lambda → {access_token: "our_jwt"}
9. React stores JWT in localStorage
10. React redirects to /info page
```

**Protected Page Access:**
```
1. React → GET https://api-gateway-url.aws.com/api/user
       Headers: Authorization: Bearer our_jwt
2. API Gateway → Lambda
3. Lambda validates JWT signature
4. Lambda → {email, name, picture}
5. React displays user info
```

---

## Technology Stack

### Frontend
- **Framework:** React 18+
- **OAuth:** @react-oauth/google
- **Routing:** React Router v6
- **HTTP:** fetch API
- **Build:** Create React App or Vite
- **Hosting:** Vercel (auto-deploy from GitHub)

### Backend
- **Framework:** FastAPI
- **Language:** Python 3.11+
- **OAuth:** google-auth
- **JWT:** python-jose
- **Lambda Adapter:** Mangum (FastAPI → Lambda)
- **Hosting:** AWS Lambda
- **CORS:** fastapi.middleware.cors

### Infrastructure
- **Frontend CDN:** Vercel (global edge network)
- **Backend:** AWS Lambda (serverless compute)
- **API Gateway:** AWS API Gateway (HTTP API)
- **HTTPS:** Auto (Vercel + API Gateway)
- **Deployment Tools:**
  - Frontend: Vercel CLI or GitHub integration
  - Backend: AWS SAM, Serverless Framework, or AWS Console

### Future (Phase 2+)
- **Database:** PostgreSQL
- **Cache:** Redis
- **Queue:** AWS SQS
- **Real-time:** WebSocket

---

## API Endpoints (Phase 1)

### POST /auth/google
Validate Google OAuth token, return our JWT

**Request:**
```json
{
  "token": "google_id_token_here"
}
```

**Response:**
```json
{
  "access_token": "our_jwt_here",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### GET /api/user
Get current user info (requires JWT)

**Headers:**
```
Authorization: Bearer <our_jwt>
```

**Response:**
```json
{
  "email": "user@gmail.com",
  "name": "John Doe",
  "picture": "https://..."
}
```

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Frontend Routes

- `/login` - Public login page
- `/info` - Protected page showing user info (requires auth)

**Route Protection:**
- Check if JWT exists in localStorage
- If not → redirect to /login
- If yes → verify with backend
- If invalid → clear storage, redirect to /login

---

## Security

### Phase 1 Measures
1. **HTTPS everywhere** (Vercel auto, Lambda + API Gateway auto)
2. **JWT signed** with HS256 algorithm
3. **Short expiration** (1 day for POC)
4. **CORS** configured properly
5. **Input validation** with Pydantic
6. **Email whitelist** (only authorized emails can authenticate)

### Future Enhancements
- Refresh tokens (15-min access tokens)
- httpOnly cookies (instead of localStorage)
- Rate limiting
- CSRF protection

---

## Deployment

### Backend (AWS Lambda)
1. Configure AWS credentials locally
2. Update `backend/samconfig.toml` with parameters
3. Run: `sam build && sam deploy`
4. CloudFormation creates:
   - Lambda function (Python 3.13)
   - API Gateway (HTTP API with CORS)
   - IAM roles
   - CloudWatch logs
5. HTTPS automatic via API Gateway
6. Get API URL from CloudFormation outputs

See [AWS Lambda Deployment Guide](../deployment/AWS_LAMBDA_DEPLOYMENT.md) for details.

### Frontend (Vercel)
1. Push code to GitHub
2. Connect Vercel to repo
3. Set environment variables via Vercel CLI/dashboard
4. Auto-deploy on push
5. HTTPS automatic via Vercel CDN

See [Vercel Deployment Guide](../deployment/VERCEL_DEPLOYMENT.md) for details.

---

## Environment Variables

### Backend (.env)
```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SECRET_KEY=... (for JWT signing)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app
ALLOWED_EMAILS=your-email@gmail.com
```

### Frontend (.env)
```bash
REACT_APP_GOOGLE_CLIENT_ID=...
REACT_APP_API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/prod
```

See [Environment Setup Guide](../deployment/ENVIRONMENT_SETUP.md) for complete details.

---

## Phase 2 Architecture: Job Ingestion Pipeline

**Status**: In Progress 🚧
**Goals**:
1. Generate job URLs from company career pages
2. Crawl job pages to get raw HTML
3. Extract structured job data from HTML
4. Track ingestion progress with real-time updates
5. Deduplicate content to avoid redundant extraction

### Architecture Overview

**Phase 2J - Crawler Queue (Current)**
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
                 │
                 │ Async (Lambda invoke)
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     IngestionWorker Lambda                          │
│  1. Status: INITIALIZING                                           │
│  2. For each enabled company:                                      │
│     - Run extractor → get job URLs                                 │
│     - UPSERT to DB (all non-expired → PENDING)                     │
│  3. Mark expired jobs                                              │
│  4. Status: INGESTING                                              │
│  5. Query all PENDING jobs                                         │
│  6. SendMessageBatch to CrawlerQueue.fifo:                         │
│     - MessageGroupId: company                                      │
│     - MessageDeduplicationId: {run_id}-{company}-{external_id}     │
│  7. Return immediately (workers process async)                     │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  CrawlerQueue.fifo (SQS FIFO)                       │
│  MessageGroupId = company → only 1 msg/company in-flight           │
│  Message: {run_id, user_id, company, external_id, url}             │
└────────────────┬────────────────────────────────────────────────────┘
                 │ Triggers (BatchSize: 1)
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     CrawlerWorker Lambda                            │
│  1. Parse message                                                  │
│  2. Query run (status + metadata) - single DB call                 │
│     ├─ ABORTED → return                                            │
│     └─ failures >= 5 → mark job ERROR, return (circuit breaker)    │
│  3. try:                                                           │
│       Crawl URL (3 retries, 1s backoff)                            │
│       SimHash check (skip if Hamming distance ≤ 3)                 │
│       S3 save → raw/{company}/{external_id}.html                   │
│     except: increment failures, mark job ERROR, return             │
│  4. Update job (READY or SKIPPED, simhash, raw_s3_url)             │
│  5. TODO Phase 2K: Send to ExtractorQueue                          │
│  6. sleep(1) → rate limiting                                       │
│  7. Return                                                         │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ├─→ S3 Bucket: raw/{company}/{external_id}.html
                 │
                 └─→ Database: jobs.status = READY/SKIPPED/ERROR
                               ingestion_runs.run_metadata[{company}_failures]
```

**Phase 2K - Extractor Queue (Future)**
```
┌─────────────────────────────────────────────────────────────────────┐
│                     CrawlerWorker Lambda                            │
│  ... (after S3 save)                                               │
│  5. Send to ExtractorQueue.fifo                                    │
│  6. Update job status: CRAWLED                                     │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                 ExtractorQueue.fifo (SQS FIFO)                      │
│  Message: {run_id, user_id, company, external_id}                  │
└────────────────┬────────────────────────────────────────────────────┘
                 │ Triggers (BatchSize: 1)
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    ExtractorWorker Lambda                           │
│  1. Download raw HTML from S3                                      │
│  2. Extract structured data (description, requirements)            │
│  3. Update DB: status = READY, description, requirements           │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          Database                                   │
│  ingestion_runs: Track overall progress + metadata                 │
│  jobs: Individual job status, simhash, raw_s3_url                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Status Flows

**Ingestion Run Status**
```
pending → initializing → ingesting → finished
                    ↘            ↘
                     → error      → error
```

| Status | Description |
|--------|-------------|
| `pending` | Run created, waiting to start |
| `initializing` | Fetching URLs from company APIs, creating job records |
| `ingesting` | Workers processing jobs (crawl + extract) |
| `finished` | All jobs processed successfully |
| `error` | Catastrophic failure (can't proceed) |

**Job Status**
```
Phase 2J (Crawler):
pending → ready (crawled, SimHash changed)
    ↘
     → skipped (SimHash similar - no change)
     → error (crawl/S3 failed)
     → expired (URL 404)

Phase 2K (Extractor - adds extraction step):
pending → crawled → ready
    ↘        ↘
     → skipped  → error
     → error
     → expired
```

| Status | Description |
|--------|-------------|
| `pending` | Job created, waiting for crawler |
| `crawled` | HTML fetched, waiting for extraction (Phase 2K) |
| `ready` | Processing complete |
| `skipped` | SimHash similar to previous run - no re-extraction needed |
| `error` | Processing failed (see error_message) |
| `expired` | Job URL returned 404 |

### SimHash Deduplication

To avoid expensive extraction when job content hasn't changed:

1. **Crawler** computes SimHash (64-bit fuzzy hash) of HTML content
2. **Compare** with stored SimHash in DB (if job existed before)
3. **If similar** (Hamming distance ≤ 3): Skip extraction, mark as 'ready'
4. **If different**: Proceed to extraction queue

See [ADR-017: SimHash for Raw Content Deduplication](./DECISIONS.md#adr-017-simhash-for-raw-content-deduplication)

### Real-Time Progress (SSE)

Frontend receives progress updates via Server-Sent Events:

```
GET /api/ingestion/progress/{run_id}?token=<jwt>
Accept: text/event-stream
```

**Authentication**: JWT passed as query parameter (EventSource API cannot send headers)

**Event Types**:

| Event | When | Data |
|-------|------|------|
| `status` | pending/initializing/terminal | Run status string |
| `all_jobs` | First poll when ingesting | Full job map by company |
| `update` | Subsequent polls when ingesting | Only changed jobs (diff) |

**Example Stream**:
```
event: status
data: pending

event: status
data: initializing

event: all_jobs
data: {"google": [{"external_id": "123", "title": "Software Engineer", "status": "pending"}, ...], "amazon": [...]}

event: update
data: {"google": {"123": "crawling"}, "amazon": {"456": "ready"}}

event: update
data: {"google": {"123": "ready"}}

event: status
data: finished
```

**Data Structures**:
- **Unique key**: `company` + `external_id` (e.g., google + 123)
- **all_jobs**: `{company: [{external_id, title, status}, ...]}`
- **update**: `{company: {external_id: status, ...}}` (status changes only)

**Polling Strategy by Phase**:

| Run Status | What SSE Polls | Why |
|------------|----------------|-----|
| `pending` | `ingestion_run` only | No jobs exist yet |
| `initializing` | `ingestion_run` only | Jobs being created |
| `ingesting` | `jobs` table | Need job-level status |
| terminal | Nothing | Emit final status, close |

**Implementation Details**:
- Polls DB every 3 seconds
- Auto-reconnects every 29s (API Gateway limit)
- On reconnect: always sends `all_jobs` (full state)
- During session: sends `update` (diff only)
- Bandwidth: ~25KB on connect, ~0.5KB per update

See [ADR-016: SSE for Real-Time Progress Updates](./DECISIONS.md#adr-016-sse-for-real-time-progress-updates)
See [ADR-018: SSE Update Strategy](./DECISIONS.md#adr-018-sse-update-strategy---full-state-on-connect-diffs-during-session)

### Database Schema

**ingestion_runs table**
```sql
CREATE TABLE ingestion_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',
    -- pending, initializing, ingesting, finished, error
    error_message TEXT,              -- Only for catastrophic failures
    created_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP
);
```

**jobs table**
```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES ingestion_runs(id),
    user_id INTEGER REFERENCES users(id),
    company VARCHAR(100),
    external_id VARCHAR(255),        -- Company's job ID
    url TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    -- pending, crawled, ready, error, expired
    simhash BIGINT,                  -- For content deduplication
    s3_key TEXT,                     -- Path to raw HTML
    title TEXT,
    location TEXT,
    description TEXT,
    error_message TEXT,              -- Job-specific errors
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, company, external_id)
);
```

### API Endpoints

#### Implemented (Stage 1 & 2)

**GET /api/ingestion/companies** - List available companies
```json
Response:
[
  {"name": "google", "display_name": "Google", "logo_url": "https://..."},
  {"name": "amazon", "display_name": "Amazon", "logo_url": "https://..."},
  ...
]
```

**GET /api/ingestion/settings** - Get user's company settings (Auth: JWT)
```json
Response:
[
  {
    "id": 1,
    "company_name": "anthropic",
    "title_filters": {"include": ["engineer"], "exclude": ["intern"]},
    "is_enabled": true,
    "updated_at": "2024-12-18T..."
  },
  ...
]
```

**POST /api/ingestion/settings** - Batch update settings (Auth: JWT)
```json
Request:
[
  {"op": "upsert", "company_name": "google", "title_filters": {"include": ["engineer"]}, "is_enabled": true},
  {"op": "upsert", "company_name": "amazon", "title_filters": {}, "is_enabled": false},
  {"op": "delete", "company_name": "netflix"}
]

Response:
[
  {"op": "upsert", "success": true, "company_name": "google", "id": 1, "updated_at": "2025-12-18T..."},
  {"op": "upsert", "success": true, "company_name": "amazon", "id": 2, "updated_at": "2025-12-18T..."},
  {"op": "delete", "success": true, "company_name": "netflix"}
]
```

**POST /api/ingestion/dry-run** - Preview jobs for enabled companies (Auth: JWT)
```json
Response:
{
  "google": {
    "status": "success",
    "total_count": 128,
    "filtered_count": 3,
    "urls_count": 125,
    "included_jobs": [
      {"id": "123", "title": "Software Engineer", "location": "NYC", "url": "https://..."},
      ...
    ],
    "excluded_jobs": [...],
    "error_message": null
  },
  "amazon": {
    "status": "error",
    "total_count": 0,
    "filtered_count": 0,
    "urls_count": 0,
    "included_jobs": [],
    "excluded_jobs": [],
    "error_message": "Request timed out - career site may be slow"
  }
}
```

#### Planned (Stage 3: Sync & Ingest)

**POST /api/ingestion/start** - Start ingestion run (Auth: JWT)
```json
Request: {}

Response:
{
  "run_id": 123
}
```
Note: Only `run_id` returned. Status/progress comes from SSE endpoint.

**GET /api/ingestion/progress/{run_id}?token=\<jwt\>** - SSE stream
```
Accept: text/event-stream
Auth: JWT as query param (EventSource can't send headers)

Response: Server-Sent Events stream
- event: status (pending/initializing/terminal states)
- event: all_jobs (full job map on connect/reconnect)
- event: update (diff of changed jobs during session)

See Real-Time Progress section for details.
```

**GET /api/ingestion/status/{run_id}** - One-time status check (Auth: JWT)
```json
Response:
{
  "run_id": 123,
  "status": "ingesting",
  "counts": {
    "pending": 45,
    "crawled": 30,
    "ready": 25,
    "error": 0
  },
  "created_at": "2024-12-31T10:00:00Z"
}
```

### Run Completion Detection

Each worker checks if the run is complete after processing a job:

```python
def check_run_complete(run_id: int):
    """Called by worker after updating job status"""
    pending = db.query(
        "SELECT COUNT(*) FROM jobs WHERE run_id = ? AND status IN ('pending', 'crawled')",
        run_id
    )
    if pending == 0:
        db.execute(
            "UPDATE ingestion_runs SET status = 'finished', finished_at = NOW() WHERE id = ?",
            run_id
        )
```

### Error Handling

| Level | Condition | Action |
|-------|-----------|--------|
| **Run-level** | Can't fetch any company APIs | `ingestion_runs.status = 'error'` |
| **Run-level** | DB connection failed | `ingestion_runs.status = 'error'` |
| **Job-level** | Single URL fetch failed | `jobs.status = 'error'`, continue others |
| **Job-level** | Extraction failed | `jobs.status = 'error'`, continue others |
| **Job-level** | URL returned 404 | `jobs.status = 'expired'` |

- **Run errors**: Catastrophic, entire run fails
- **Job errors**: Isolated, logged in `jobs.error_message`, other jobs continue
- **Developer visibility**: CloudWatch logs for debugging
- **User visibility**: Error counts in progress stream, details in job records

### Extractor Class Structure

Each company has a single extractor class with all phases:

```python
from extractors.base_extractor import BaseJobExtractor
from extractors.enums import Company

class GoogleExtractor(BaseJobExtractor):
    COMPANY_NAME = Company.GOOGLE
    API_URL = "https://careers.google.com/api/v3/search"

    # Phase 1: URL Generation
    def _fetch_all_jobs(self) -> List[Dict]:
        """Fetch jobs from API, return standardized metadata"""
        pass

    # Phase 2: Crawling
    def crawl_job(self, url: str) -> str:
        """Fetch raw HTML from job URL"""
        pass

    # Phase 3: Extraction
    def extract_job(self, raw_html: str) -> Dict:
        """Extract structured data from HTML"""
        pass
```

### Phase 2 Implementation Status

**Completed:**
- ✅ Phase 2A-2F: Extractor base class and 6 company extractors
- ✅ Phase 2G: SSE progress endpoint with real-time updates
- ✅ Phase 2H: Frontend progress display with diff-based updates
- ✅ Phase 2I: Raw info crawling and extraction methods in extractors
- ✅ Database: users, user_settings, company_settings, ingestion_runs, jobs tables
- ✅ API endpoints: GET /companies, GET/POST /settings, POST /dry-run, POST /start, GET /progress SSE
- ✅ IngestionWorker Lambda (async invoke, mock SQS publishing)

**Phase 2J (Planning):** Crawler Queue Infrastructure
- 📋 SQS FIFO queue (CrawlerQueue.fifo) with MessageGroupId per company
- 📋 S3 bucket for raw HTML storage
- 📋 CrawlerWorker Lambda (SQS-triggered)
- 📋 DB migration: add `metadata` to ingestion_runs, `raw_s3_url` to jobs
- 📋 SimHash integration for content deduplication
- 📋 Update IngestionWorker to publish real messages to SQS

**Phase 2K (Future):** Extractor Queue Infrastructure
- 📋 SQS FIFO queue (ExtractorQueue.fifo)
- 📋 ExtractorWorker Lambda
- 📋 Add CRAWLED job status
- 📋 CrawlerWorker sends to ExtractorQueue after S3 save

**Design Decisions Made:**
- ✅ [ADR-020](./DECISIONS.md#adr-020-sqs-fifo-with-messagegroupid-for-crawler-rate-limiting): FIFO + MessageGroupId for rate limiting (1s sleep)
- ✅ [ADR-017](./DECISIONS.md#adr-017-use-simhash-for-raw-content-deduplication): SimHash with Hamming distance ≤ 3
- ✅ No DLQ (simplicity)
- ✅ Circuit breaker: 5 failures per company per run

---

## Phase 3 Architecture: Search Page

**Status**: Planning 📋
**Goals**:
1. Display all jobs with company-grouped layout
2. Fuzzy search across titles, descriptions, requirements
3. Sync All: Update job metadata without re-crawling
4. Re-Extract: Re-run extraction from S3 for individual jobs

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Search Page (React)                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔍 [search query__________________] [Search] [Clear]    [Sync All]   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────┬─────────────────────────────────────────────────────┐  │
│  │  COMPANIES      │  JOB DETAILS                                        │  │
│  │  ┌───────────┐  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Google ▼  │  │  │  Senior K8s Engineer ↗                     │    │  │
│  │  │ Ready: 45 │  │  │  Mountain View, CA                         │    │  │
│  │  │ Match: 8  │  │  ├─────────────────────────────────────────────┤    │  │
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
│  GET  /api/jobs                → List all jobs grouped by company           │
│  GET  /api/jobs/{id}           → Get full job details                       │
│  GET  /api/jobs/search?q=...   → Fuzzy search jobs                          │
│  POST /api/jobs/sync           → Sync All: update metadata, mark expired    │
│  POST /api/jobs/{id}/re-extract → Re-extract single job from S3             │
└────────────────┬────────────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PostgreSQL (Neon)                                   │
│  jobs table:                                                                 │
│  - Trigram index on title (pg_trgm) for fuzzy search                        │
│  - Phase 3C: tsvector for full-text search                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### UI Layout (1:3 Column Design)

**Left Column (1/4)**: Company cards with expandable job lists
- Company logo, name, ready count
- After search: matched count
- Expand/collapse to show jobs
- Radio buttons for job selection
- "⌄ N more" / "⌃ show less" for long lists

**Right Column (3/4)**: Selected job details
- Clickable title → opens job URL in new tab
- Location
- Description (full text)
- Requirements (full text)
- [Re-Extract] button

### API Endpoints (Phase 3)

#### GET /api/jobs (Phase 3A)
List all jobs grouped by company.

```json
Response:
{
  "companies": [
    {
      "name": "google",
      "display_name": "Google",
      "logo_url": "https://...",
      "ready_count": 45,
      "jobs": [
        {
          "id": 123,
          "title": "Kubernetes Platform Engineer",
          "location": "Seattle, WA"
        }
      ]
    }
  ],
  "total_ready": 126
}
```

#### GET /api/jobs/{job_id} (Phase 3A)
Get full job details.

```json
Response:
{
  "id": 123,
  "company": "google",
  "external_id": "abc123",
  "title": "Kubernetes Platform Engineer",
  "location": "Seattle, WA",
  "url": "https://careers.google.com/...",
  "status": "ready",
  "description": "Build and maintain our Kubernetes platform...",
  "requirements": "• 3+ years Kubernetes experience\n• Go or Python...",
  "raw_s3_url": "s3://bucket/raw/google/abc123.html",
  "updated_at": "2026-01-12T10:30:00Z"
}
```

#### POST /api/jobs/sync (Phase 3B)
Sync All: Update metadata, mark expired. Does NOT crawl or extract.

```json
Request: {}

Response:
{
  "updated": 130,
  "expired": 5,
  "duration_ms": 8500
}
```

**Process:**
1. Get enabled companies from settings
2. Run extractors to get current job URLs (like dry-run)
3. UPSERT jobs with metadata only (title, location, url, updated_at)
4. Mark jobs not in results as EXPIRED
5. Does NOT change status to PENDING (preserves READY/SKIPPED)
6. Does NOT clear description/requirements

#### POST /api/jobs/{job_id}/re-extract (Phase 3B)
Re-extract single job from S3 HTML.

```json
Request: {}

Response (Success):
{
  "success": true,
  "job_id": 123,
  "description_length": 1250,
  "requirements_length": 450
}

Response (Error):
{
  "success": false,
  "error": "No raw HTML found for this job. Run full ingestion first."
}
```

**Process:**
1. Get job by ID, verify user ownership
2. Check raw_s3_url exists
3. Download raw HTML from S3
4. Run company's extract_raw_info() method
5. Update job: description, requirements
6. Return success with content lengths

#### GET /api/jobs/search?q={query} (Phase 3C)
Fuzzy search using pg_trgm.

```json
Request: GET /api/jobs/search?q=kubernetes

Response:
{
  "companies": [
    {
      "name": "google",
      "display_name": "Google",
      "ready_count": 45,
      "matched_count": 8,
      "jobs": [
        {
          "id": 123,
          "title": "Kubernetes Platform Engineer",
          "location": "Seattle, WA",
          "similarity": 0.85
        }
      ]
    }
  ],
  "total_ready": 126,
  "total_matched": 16,
  "query": "kubernetes"
}
```

### Search Implementation (Phase 3C)

**Fuzzy Search (pg_trgm)**
```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Trigram index for fuzzy matching
CREATE INDEX idx_jobs_title_trgm ON jobs USING GIN(title gin_trgm_ops);

-- Search query
SELECT *, similarity(title, 'kubernetes') AS sim
FROM jobs
WHERE user_id = ?
  AND status = 'ready'
  AND similarity(title, 'kubernetes') > 0.3
ORDER BY sim DESC;
```

**Full-Text Search (tsvector) - Optional Enhancement**
```sql
-- Add tsvector column
ALTER TABLE jobs ADD COLUMN search_vector TSVECTOR;

-- GIN index for full-text
CREATE INDEX idx_jobs_search_vector ON jobs USING GIN(search_vector);

-- Trigger for auto-update
CREATE TRIGGER jobs_search_vector_trigger
  BEFORE INSERT OR UPDATE ON jobs
  FOR EACH ROW EXECUTE FUNCTION jobs_search_vector_update();

-- Hybrid search: full-text OR fuzzy
SELECT *
FROM jobs
WHERE user_id = ?
  AND (search_vector @@ plainto_tsquery('english', 'kubernetes')
       OR similarity(title, 'kubernetes') > 0.3)
ORDER BY ts_rank(search_vector, query) + similarity(title, 'kubernetes') DESC;
```

### Phase 3 Implementation Status

**Phase 3A: Basic Job Display (UI Only)**
- 📋 GET /api/jobs endpoint
- 📋 GET /api/jobs/{id} endpoint
- 📋 Frontend: 1:3 column layout
- 📋 Frontend: Company cards with expand/collapse
- 📋 Frontend: Job details panel
- 📋 Search bar placeholder (disabled)

**Phase 3B: Sync All & Re-Extract**
- 📋 POST /api/jobs/sync endpoint
- 📋 POST /api/jobs/{id}/re-extract endpoint
- 📋 Frontend: Sync All button with loading state
- 📋 Frontend: Re-Extract button per job
- 📋 Success/error banners and toasts

**Phase 3C: Fuzzy Search**
- 📋 GET /api/jobs/search endpoint
- 📋 Database: pg_trgm index
- 📋 Frontend: Enable search bar
- 📋 Optional: tsvector for full-text search
- 📋 Optional: Search result snippets with highlights

---

## Phase 4 (Future)

### Phase 4: Job Tracking & Cart
- Add jobs to tracked list
- Track page with saved jobs
- Application status tracking
- Timeline visualization
- Analytics dashboard

---

**Current Phase**: Phase 2 Complete ✅
**Next**: Phase 3A - Basic Job Display
