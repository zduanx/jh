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

## Future Architecture (Phase 2-4)

See [Phase 1 Summary](../logs/PHASE_1_SUMMARY.md) for current state.

### Phase 2: Web Scraping & Database
**Goal**: Scrape job postings and save to database

**Components**:
- Database setup (PostgreSQL on RDS or Neon)
- Database schema (jobs, applications tables)
- Web scraping logic (LinkedIn, Indeed, etc.)
- Scraping API endpoints
- Data storage pipeline

**Status**: To be designed

### Phase 3: Search & Add to List
**Goal**: Search scraped jobs and add to personal application tracker

**Components**:
- Search API with filtering (company, title, location)
- Frontend search UI
- "Add to my list" functionality
- Personal application tracker (status, notes, dates)
- Application CRUD endpoints

**Status**: To be designed

### Phase 4: Application Tracking
**Goal**: Track application status through hiring process

**Components**:
- Application status workflow (applied → phone screen → onsite → offer/rejected)
- Notes and follow-up reminders
- Timeline visualization
- Email integration (optional)
- Analytics dashboard

**Status**: To be designed

---

**Current Phase**: Phase 1 Complete ✅
**Next**: Begin Phase 2 planning
