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

## Phase 2 Architecture: Job URL Sourcing & Crawling Pipeline

**Status**: In Progress 🚧
**Goals**:
1. Generate job URLs from company career pages
2. Crawl job pages to get raw HTML
3. Parse HTML to extract structured job data
4. Store in database for application tracking

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface (React)                      │
│  - Settings Page: Configure companies & filters                    │
│  - Crawl Control: Trigger dry-run or live crawl                   │
│  - Real-time Status: WebSocket updates (future)                   │
└────────────────┬────────────────────────────────────────────────────┘
                 │ HTTPS API calls
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  API Gateway + SourceURLLambda                      │
│                    (URL Generation Service)                         │
│                                                                     │
│  POST /api/sourcing (dry_run=true)  → Return URL metadata         │
│  POST /api/sourcing (dry_run=false) → Send to SQS Queue A         │
└────────────┬────────────────────────────────────────────────────────┘
             │
             │ dry_run=false
             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         SQS Queue A                                 │
│                   (Job URLs to Crawl)                              │
│  Message: {job_id, company, title, location, url}                 │
└────────────┬────────────────────────────────────────────────────────┘
             │ Triggers
             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  JobCrawlerLambda (Crawling)                       │
│  1. Fetch raw HTML from job URL                                   │
│  2. Save metadata + S3 reference to DB                            │
│  3. Save raw HTML to S3                                           │
│  4. Send job DB ID to SQS Queue B                                 │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ├─→ S3 Bucket: raw/{company}/{job_id}.html
             │
             └─→ Database: jobs table (status: 'crawled')
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         SQS Queue B                                 │
│                   (Job IDs to Parse)                               │
│  Message: {job_db_id}                                             │
└────────────┬────────────────────────────────────────────────────────┘
             │ Triggers
             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  JobParserLambda (Parsing)                         │
│  1. Read job metadata from DB (get S3 key)                        │
│  2. Read raw HTML from S3                                         │
│  3. Parse HTML → structured data                                  │
│  4. Update DB with parsed data                                    │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          Database                                   │
│  jobs table: Complete job data (status: 'parsed')                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Detail

**1. URL Generation (SourceURLLambda)**
```
Input:  POST /api/sourcing {dry_run: boolean, user_id: string}

Process:
  1. Read user settings from DB (companies, filters)
  2. For each company:
     - Get extractor: get_extractor(company, filters)
     - Call: extractor.extract_source_urls_metadata()
  3. If dry_run=true:
     - Return: {summary, results: [CompanyResult, ...]}
  4. If dry_run=false:
     - For each job in results.included_jobs:
       - Send message to SQS Queue A
     - Return: {message: "Crawl started", job_count: N}

Output: JSON response OR SQS messages
```

**2. Crawling (JobCrawlerLambda)**
```
Input:  SQS message from Queue A
        {job_id, company, title, location, url}

Process:
  1. Get extractor for company
  2. Call: raw_html = extractor.crawl_job(url)
  3. Generate S3 key: raw/{company}/{job_id}.html
  4. Upload raw_html to S3
  5. Insert to DB:
     - job_id, company, title, location, url
     - s3_key, status='crawled', created_at
  6. Get DB record ID
  7. Send {job_db_id} to SQS Queue B

Output: DB record + S3 file + SQS message
```

**3. Parsing (JobParserLambda)**
```
Input:  SQS message from Queue B
        {job_db_id}

Process:
  1. Read job record from DB (get s3_key)
  2. Download raw_html from S3
  3. Get extractor for company
  4. Call: parsed_data = extractor.parse_job(raw_html)
     Returns: {
       description: str,
       requirements: [str],
       responsibilities: [str],
       salary_range: str,
       job_type: str,
       ...
     }
  5. Update DB record:
     - Add parsed fields
     - status='parsed'
     - updated_at

Output: Updated DB record
```

### Extractor Class Structure

Each company has a single extractor class with all 3 phases:

```python
from extractors.base_extractor import BaseJobExtractor
from extractors.enums import Company

class GoogleExtractor(BaseJobExtractor):
    COMPANY_NAME = Company.GOOGLE
    API_URL = "https://careers.google.com/api/v3/search"
    URL_PREFIX_JOB = "https://www.google.com/about/careers/..."

    # Phase 1: URL Generation (✅ Implemented)
    def _fetch_all_jobs(self) -> List[Dict]:
        """Fetch jobs from API, return standardized metadata"""
        pass

    # Phase 2: Crawling (🚧 To Implement)
    def crawl_job(self, url: str) -> str:
        """Fetch raw HTML from job URL"""
        pass

    # Phase 3: Parsing (🚧 To Implement)
    def parse_job(self, raw_html: str) -> Dict:
        """Parse HTML to extract structured data"""
        pass
```

### API Endpoints (Phase 2)

**POST /api/sourcing**
```json
Request:
{
  "dry_run": true  // or false
}

Response (dry_run=true):
{
  "summary": {
    "total_jobs": 480,
    "total_companies": 6
  },
  "results": [
    {
      "company": "google",
      "total_count": 117,
      "filtered_count": 15,
      "urls_count": 102,
      "included_jobs": [
        {"id": "...", "title": "...", "location": "...", "url": "..."},
        ...
      ]
    },
    ...
  ]
}

Response (dry_run=false):
{
  "message": "Crawl pipeline started",
  "job_count": 480,
  "companies": ["google", "amazon", "anthropic", ...]
}
```

**GET /api/companies** (New)
```json
Response:
{
  "companies": [
    {"id": "google", "name": "Google", "job_count": 117},
    {"id": "amazon", "name": "Amazon", "job_count": 63},
    ...
  ]
}
```

**POST /api/settings** (New)
```json
Request:
{
  "user_id": "user123",
  "companies": ["google", "amazon"],
  "filters": {
    "google": {"include": ["software"], "exclude": ["senior staff"]},
    "amazon": {"include": null, "exclude": ["principal"]}
  }
}

Response:
{
  "message": "Settings saved",
  "settings_id": "setting123"
}
```

**GET /api/settings/:user_id** (New)
```json
Response:
{
  "user_id": "user123",
  "companies": ["google", "amazon"],
  "filters": {...},
  "last_updated": "2024-12-15T10:00:00Z"
}
```

**GET /api/queue/status** (New - Better UX)
```json
Response:
{
  "queue_a": {
    "name": "job-urls-to-crawl",
    "status": "active",
    "messages_in_queue": 150
  },
  "queue_b": {
    "name": "job-ids-to-parse",
    "status": "active",
    "messages_in_queue": 20
  }
}
```

**WebSocket /ws/crawl-status** (Future - Real-time updates)
```json
Message:
{
  "event": "crawl_progress",
  "company": "google",
  "crawled": 45,
  "total": 102,
  "percent": 44.1
}
```

### Database Schema (Preliminary)

**users table** (from Phase 1)
- id (PK)
- email
- name
- google_id
- created_at

**user_settings table** (New)
- id (PK)
- user_id (FK)
- companies (JSON array)
- filters (JSON object)
- enabled (boolean)
- last_run_at
- created_at, updated_at

**jobs table** (New)
- id (PK)
- job_id (company's job ID)
- company (enum)
- title
- location
- url
- s3_key (S3 path to raw HTML)
- status (enum: pending, crawled, parsed, error)
- description (text) - from parsing
- requirements (JSON array) - from parsing
- salary_range - from parsing
- job_type - from parsing
- created_at, updated_at

### Phase 2 Scope

**Included:**
- ✅ Extractor crawler methods (Phase 2A)
- ✅ JobCrawlerLambda (crawling service)
- ✅ SQS Queue A + Queue B setup
- ✅ S3 bucket for raw HTML
- ✅ Database schema + tables
- ✅ SourceURLLambda updates (SQS sending)
- ✅ Settings API endpoints
- ✅ Companies API endpoint
- ✅ Queue status API endpoint
- ✅ Extractor parser methods (Phase 2B)
- ✅ JobParserLambda (parsing service)

**Deferred to ADR (Pending Decisions):**
- Settings storage choice (DynamoDB vs PostgreSQL)
- Crawling rate limits & delays per company
- Error handling strategy (retries, DLQ, logging)
- S3 cleanup policy (retention period)
- JobCrawlerLambda batching strategy (1 URL vs multiple)
- WebSocket implementation (infrastructure choice)
- Database choice (RDS vs Neon vs DynamoDB)

See [ADR: Phase 2 Pending Decisions](../architecture/DECISIONS.md#phase-2-pending-decisions)

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
