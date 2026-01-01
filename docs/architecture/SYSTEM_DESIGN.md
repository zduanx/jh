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
│  POST /api/ingest/start    → Create run, async initialize         │
│  GET  /api/ingest/progress → SSE stream for real-time updates     │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 │ Async (Lambda invoke)
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Initializer Lambda (Async)                       │
│  1. Fetch job URLs from all company APIs                           │
│  2. Create job records in DB (status: pending)                     │
│  3. Send messages to SQS1 (crawl queue)                            │
│  4. Update run status: initializing → ingesting                    │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         SQS1 (Crawl Queue)                          │
│  Message: {job_id (DB), run_id, company, url}                      │
└────────────────┬────────────────────────────────────────────────────┘
                 │ Triggers (batch size: 1)
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    CrawlerLambda (Worker 1)                         │
│  1. Fetch raw HTML from job URL                                    │
│  2. Compute SimHash of content                                     │
│  3. Compare with existing SimHash in DB                            │
│  4. If changed: Save to S3, update DB, send to SQS2               │
│  5. If unchanged: Update status to 'ready' (skip extraction)       │
│  6. Check if run complete → update run status                      │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ├─→ S3 Bucket: raw/{company}/{job_id}.html
                 │
                 └─→ Database: jobs.status = 'crawled' or 'ready'
                     │
                     ↓ (only if content changed)
┌─────────────────────────────────────────────────────────────────────┐
│                       SQS2 (Extract Queue)                          │
│  Message: {job_id (DB), run_id}                                    │
└────────────────┬────────────────────────────────────────────────────┘
                 │ Triggers (batch size: 1)
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   ExtractorLambda (Worker 2)                        │
│  1. Read job record from DB (get s3_key)                           │
│  2. Download raw HTML from S3                                      │
│  3. Extract structured data (title, description, etc.)             │
│  4. Update DB with extracted fields, status = 'ready'              │
│  5. Check if run complete → update run status                      │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          Database                                   │
│  ingestion_runs: Track overall progress                            │
│  jobs: Individual job status and data                              │
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
pending → crawled → ready
    ↘        ↘
     → error  → error
     → expired (URL 404)

With SimHash optimization:
pending → ready (if content unchanged, skip extraction)
```

| Status | Description |
|--------|-------------|
| `pending` | Job created, waiting for crawler |
| `crawled` | HTML fetched, waiting for extraction |
| `ready` | Extraction complete (or skipped via SimHash) |
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
GET /api/ingest/progress/{run_id}
Accept: text/event-stream

← event: progress
← data: {"status":"ingesting","pending":45,"crawled":30,"ready":25,"error":0}

← event: progress
← data: {"status":"ingesting","pending":20,"crawled":35,"ready":45,"error":0}

← event: complete
← data: {"status":"finished","total":100,"ready":98,"error":2}
```

**Implementation**:
- SSE endpoint queries DB for current counts
- Emits events every 2-3 seconds
- Auto-reconnects every 29s (API Gateway limit)
- Uses `Last-Event-ID` header for resume

See [ADR-016: SSE for Real-Time Progress Updates](./DECISIONS.md#adr-016-sse-for-real-time-progress-updates)

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

**GET /api/ingestion/progress/{run_id}** - SSE stream (Auth: JWT)
```
Accept: text/event-stream

Response: Server-Sent Events stream (see Real-Time Progress section)
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
- ✅ Extractor base class and 6 company extractors (Google, Amazon, Anthropic, TikTok, Roblox, Netflix)
- ✅ Async URL sourcing with httpx + asyncio.gather (parallel company fetches)
- ✅ Database schema: users, user_settings, company_settings tables
- ✅ API endpoints: GET /companies, GET/POST /settings, POST /dry-run
- ✅ Frontend Stage 1: Company selection with filters
- ✅ Frontend Stage 2: Dry-run preview with job counts

**In Progress (Stage 3: Sync & Ingest):**
- 🚧 ingestion_runs and jobs tables (schema defined, not yet migrated)
- 🚧 POST /ingestion/start endpoint
- 🚧 SQS queues setup (crawl queue, extract queue)
- 🚧 CrawlerLambda (Worker 1)
- 🚧 ExtractorLambda (Worker 2)
- 🚧 SSE progress endpoint
- 🚧 SimHash integration
- 🚧 Frontend Stage 3: Sync & Ingest with progress display

**Pending Design Decisions:**
- Crawling rate limits per company
- S3 cleanup policy (retention period)
- DLQ configuration for failed messages

---

## Phase 3-4 (Future)

### Phase 3: Search & Application Tracking
- Search API with filters
- Add jobs to personal tracker
- Application CRUD operations

### Phase 4: Status Tracking & Analytics
- Application workflow management
- Timeline visualization
- Analytics dashboard

---

**Current Phase**: Phase 2 In Progress 🚧
**Next**: Implement crawler methods + JobCrawlerLambda
