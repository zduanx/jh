# Job Hunt Tracker - Backend API

FastAPI backend for job application tracking system, designed for AWS Lambda deployment.

## Architecture

- **Framework**: FastAPI (async Python web framework)
- **Authentication**: Google OAuth 2.0 + JWT tokens
- **Deployment**: AWS Lambda + API Gateway (serverless)
- **Adapter**: Mangum (FastAPI → Lambda)

## Project Structure

```
backend/
├── main.py                 # FastAPI app + Lambda handler (SourceURLLambda)
├── requirements.txt        # Python dependencies
├── template.yaml           # AWS SAM/CloudFormation template
├── samconfig.toml         # SAM deployment configuration
├── .env                   # Environment variables (not committed)
├── .env.example           # Environment template
├── auth/
│   ├── routes.py          # Authentication endpoints
│   ├── models.py          # Pydantic models for auth
│   ├── utils.py           # JWT & Google OAuth utilities
│   └── dependencies.py    # FastAPI dependencies (get_current_user)
├── api/
│   └── routes.py          # Protected API endpoints
├── sourcing/              # Phase 2: Job URL sourcing module
│   ├── routes.py          # POST /api/sourcing endpoint
│   ├── models.py          # Pydantic models for sourcing API
│   └── orchestrator.py    # Async parallel extraction across companies
├── extractors/            # Job URL extractors (shared library)
│   ├── base_extractor.py  # Abstract base class
│   ├── config.py          # TitleFilters configuration
│   ├── enums.py           # Company enum
│   ├── registry.py        # Extractor registry
│   └── {company}.py       # Company-specific extractors
└── config/
    └── settings.py        # Configuration management
```

## Setup (Local Development)

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `GOOGLE_CLIENT_ID`: From Google Cloud Console
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `ALLOWED_ORIGINS`: Your frontend URL(s)

### 3. Run Locally

```bash
uvicorn main:app --reload --port 8000
```

API will be available at: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## API Endpoints

### Phase 1: Authentication

#### `GET /health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-13T10:30:00Z"
}
```

#### `POST /auth/google`
Exchange Google OAuth token for JWT

**Request:**
```json
{
  "token": "google_id_token_from_frontend"
}
```

**Response:**
```json
{
  "access_token": "our_jwt_token",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### `GET /api/user`
Get current user information (Protected)

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "email": "user@gmail.com",
  "name": "John Doe",
  "picture": "https://lh3.googleusercontent.com/..."
}
```

### Phase 2: Job URL Sourcing

#### `POST /api/sourcing`
Generate job URLs from company career pages (Protected)

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request:**
```json
{
  "dry_run": true  // If true: return results, if false: send to SQS queue
}
```

**Response (dry_run=true):**
```json
{
  "summary": {
    "total_jobs": 480,
    "total_filtered_jobs": 93,
    "total_included_jobs": 387,
    "total_companies": 6
  },
  "results": [
    {
      "company": "google",
      "total_count": 117,
      "filtered_count": 15,
      "urls_count": 102,
      "included_jobs": [
        {
          "id": "123",
          "title": "Software Engineer",
          "location": "Mountain View, California",
          "url": "https://..."
        }
      ],
      "excluded_jobs": [...]
    }
  ],
  "dry_run": true
}
```

**Response (dry_run=false):**
```json
{
  "message": "Crawl pipeline started",
  "job_count": 387,
  "companies": ["google", "amazon", "anthropic", "tiktok", "roblox", "netflix"],
  "dry_run": false
}
```

## AWS Lambda Deployment

### Using AWS SAM (Recommended)

1. **Install AWS SAM CLI**
   ```bash
   brew install aws-sam-cli  # macOS
   ```

2. **Create `template.yaml`** (see deployment guide in docs)

3. **Deploy**
   ```bash
   sam build
   sam deploy --guided
   ```

### Manual Deployment

1. **Package dependencies**
   ```bash
   pip install -r requirements.txt -t package/
   cp -r *.py auth/ api/ config/ package/
   cd package && zip -r ../deployment.zip . && cd ..
   ```

2. **Create Lambda function** in AWS Console
   - Runtime: Python 3.11
   - Handler: `main.handler`
   - Upload `deployment.zip`

3. **Configure API Gateway**
   - Create HTTP API
   - Add Lambda integration
   - Configure CORS

4. **Set environment variables** in Lambda configuration

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | ✅ Yes | - |
| `SECRET_KEY` | JWT signing key | ✅ Yes | - |
| `ALGORITHM` | JWT algorithm | No | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | No | 1440 (24h) |
| `ALLOWED_ORIGINS` | CORS allowed origins | No | localhost |

## Security Notes

1. **JWT Storage**: Frontend stores JWT in localStorage (Phase 1)
   - Phase 2+: Move to httpOnly cookies
2. **Token Expiration**: 24 hours (POC), will reduce to 15 min + refresh tokens
3. **HTTPS**: Required in production (API Gateway provides this)
4. **CORS**: Only allow trusted frontend domains

## Testing

```bash
# Run FastAPI with auto-reload
uvicorn main:app --reload

# Test health endpoint
curl http://localhost:8000/health

# Test auth endpoint (need valid Google token)
curl -X POST http://localhost:8000/auth/google \
  -H "Content-Type: application/json" \
  -d '{"token": "your_google_token"}'

# Test protected endpoint
curl http://localhost:8000/api/user \
  -H "Authorization: Bearer your_jwt_token"
```

## Common Issues

### "Invalid authentication token"
- Check `GOOGLE_CLIENT_ID` matches frontend
- Ensure token is fresh (Google tokens expire)

### "Could not validate credentials"
- Check `SECRET_KEY` is set
- Verify JWT hasn't expired

### CORS errors
- Add frontend URL to `ALLOWED_ORIGINS` in `.env`

## Phase 2 Architecture

**Current Status**: Phase 2A Complete ✅, Phase 2B In Progress 🚧

### Lambda Functions

**SourceURLLambda** (Current - `main.py`) ✅
- Handles authentication endpoints
- Handles sourcing endpoint: `POST /api/sourcing`
- Supports dry_run mode (return metadata) or live mode (send to SQS)
- Uses extractors from `backend/extractors/` directory
- Orchestrates parallel extraction across multiple companies

**JobCrawlerLambda** (Phase 2B - Not yet implemented) 🚧
- Triggered by SQS Queue A
- Fetches raw HTML from job URLs
- Saves to S3: `raw/{company}/{job_id}.html`
- Saves metadata to database
- Sends job DB ID to SQS Queue B

**JobParserLambda** (Phase 2B - Not yet implemented) 🚧
- Triggered by SQS Queue B
- Reads raw HTML from S3
- Parses structured data from HTML
- Updates database with parsed job details

### Data Flow

```
User → POST /api/sourcing (dry_run=false)
  ↓
SourceURLLambda: Extract URLs from all companies
  ↓
SQS Queue A: Job URLs to crawl
  ↓
JobCrawlerLambda: Fetch HTML, save to S3 + DB
  ↓
SQS Queue B: Job DB IDs to parse
  ↓
JobParserLambda: Parse HTML, update DB
  ↓
Database: Complete job data ready for search
```

### Sourcing Module

Location: [backend/sourcing/](./sourcing/)

**Files:**
- `routes.py` - POST /api/sourcing endpoint implementation
- `models.py` - Pydantic models (SourceUrlsRequest, SourceUrlsResponse, CompanyResult, JobMetadata)
- `orchestrator.py` - Async parallel extraction using extractors from `backend/extractors/`

**How it works:**
1. Reads user settings (companies + filters) - currently hardcoded, will use DB later
2. Creates tasks for each company using `backend/extractors/registry.get_extractor()`
3. Runs all extractions in parallel using asyncio
4. Aggregates results into summary statistics
5. If dry_run=false: sends jobs to SQS Queue A (Phase 2B)

## Next Steps (Phase 2B)

- [ ] Database setup (Neon/RDS/DynamoDB - TBD)
- [ ] Implement `crawl_job(url)` in extractors
- [ ] Create JobCrawlerLambda function
- [ ] Create JobParserLambda function
- [ ] Implement `parse_job(html)` in extractors
- [ ] Set up SQS queues (Queue A + Queue B)
- [ ] Set up S3 bucket for raw HTML storage
- [ ] Add settings storage (user companies + filters)
- [ ] Add monitoring (CloudWatch)
- [ ] Add error handling (DLQ, retries)
