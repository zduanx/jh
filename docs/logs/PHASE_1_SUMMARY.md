# Phase 1 Summary: Full-Stack Authentication

**Completion Date**: December 14, 2025
**Status**: ✅ **COMPLETE**

---

## What We Built

A **full-stack job hunt tracker** with Google OAuth authentication, deployed to production.

**Stack**:
- **Frontend**: React + Google OAuth → Vercel
- **Backend**: FastAPI + JWT → AWS Lambda + API Gateway
- **Auth**: Google OAuth → JWT tokens → Email whitelist

---

## Live URLs

| Component | URL | Status |
|-----------|-----|--------|
| Frontend | https://your-app.vercel.app | ✅ Live |
| Backend API | https://your-api-id.execute-api.us-east-1.amazonaws.com/prod | ✅ Live |
| Health Check | https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/health | ✅ Working |

---

## Key Achievements

### 1. Authentication Flow (End-to-End Working)
```
User clicks "Login with Google"
  ↓
Google OAuth popup
  ↓
Frontend receives Google ID token
  ↓
Frontend sends token to backend (/auth/google)
  ↓
Backend validates with Google
  ↓
Backend checks email whitelist
  ↓
Backend issues JWT token
  ↓
Frontend stores JWT in localStorage
  ↓
User accesses protected routes
```

**Implementation**: [auth/routes.py](../../backend/auth/routes.py), [LoginPage.js](../../frontend/src/pages/LoginPage.js)

### 2. AWS Lambda Deployment (Serverless)
- **Runtime**: Python 3.13
- **Trigger**: API Gateway HTTP API
- **CORS**: Configured for Vercel + localhost
- **Environment Variables**: Set via CloudFormation (template.yaml + samconfig.toml)
- **HTTPS**: Automatic via API Gateway

**Deployment Guide**: [AWS Lambda Deployment](../deployment/AWS_LAMBDA_DEPLOYMENT.md)
**Deployment Log**: [aws-lambda-deployment.md](./aws-lambda-deployment.md)

### 3. Vercel Deployment (Frontend)
- **Auto-deploy**: On git push
- **Environment Variables**: Set via Vercel CLI
- **HTTPS**: Automatic via Vercel CDN
- **OAuth**: Authorized JavaScript Origins configured

**Deployment Guide**: [Vercel Deployment](../deployment/VERCEL_DEPLOYMENT.md)

### 4. Email Whitelist Access Control
- Only authorized emails can authenticate
- Hardcoded in `backend/config/settings.py` for quick iteration
- Can edit directly in Lambda console → Deploy

**Current Allowed**: `zduanx@gmail.com`

### 5. Infrastructure as Code
- **CloudFormation**: All AWS resources defined in template.yaml
- **SAM**: Simplified deployment with `sam build && sam deploy`
- **Version Control**: All config in git (except secrets)

**Key Files**:
- [template.yaml](../../backend/template.yaml) - AWS resources definition
- [samconfig.toml](../../backend/samconfig.toml) - Deployment configuration

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Backend Hosting** | AWS Lambda | Free tier, auto-scaling, no server management |
| **API Gateway** | HTTP API | Simpler than REST API, auto CORS, cheaper |
| **Frontend Hosting** | Vercel | Auto HTTPS, CDN, git integration |
| **Auth Strategy** | Google OAuth → JWT | Social login UX + stateless backend |
| **Access Control** | Email whitelist | Simple, effective for single-user POC |
| **Python Version** | 3.13 | Latest stable, Lambda support added |
| **JWT Storage** | localStorage | Simple for POC (will move to httpOnly cookies later) |

**Decision Log**: [DECISIONS.md](../architecture/DECISIONS.md)

---

## Challenges Overcome

### 1. Lambda Deployment Issues (9 iterations)
- **Issue**: Python version mismatch (3.11 vs 3.13)
- **Issue**: Pydantic dependency build failures
- **Issue**: IAM permissions (user needed CloudFormation access)
- **Issue**: CORS wildcards not allowed with credentials
- **Issue**: Missing dependencies (requests, email-validator)
- **Issue**: Pydantic settings parsing error
- **Issue**: FastAPI routing (needed root_path="/prod")
- **Solution**: Iterative debugging with CloudWatch logs

**Full Log**: [aws-lambda-deployment.md](./aws-lambda-deployment.md)

### 2. Vercel Environment Variables
- **Issue**: Deployed bundle still using localhost:8000
- **Root Cause**: Vercel doesn't read local .env file
- **Solution**: Set env vars via Vercel CLI, redeploy

### 3. Google OAuth Configuration
- **Issue**: Understanding Authorized JavaScript Origins
- **Clarification**: Only frontend URL needed (not backend)
- **Reason**: OAuth button loads from frontend, backend validation is server-to-server

---

## Documentation Created

### Architecture
- [System Design](../architecture/SYSTEM_DESIGN.md) - Overall system architecture
- [API Design](../architecture/API_DESIGN.md) - API endpoints and contracts
- [Decisions](../architecture/DECISIONS.md) - Technical decision log

### Learning Guides
- [AWS Deployment](../learning/aws-deployment.md) - EC2 vs Lambda, SAM, API Gateway
- [Authentication](../learning/authentication.md) - OAuth, JWT, security
- [Backend](../learning/backend.md) - FastAPI, Pydantic, Python
- [Frontend](../learning/frontend.md) - React, routing, state
- [Security](../learning/security.md) - HTTPS, CORS, token storage

### Deployment Guides
- [AWS Lambda Deployment](../deployment/AWS_LAMBDA_DEPLOYMENT.md) - Step-by-step SAM deployment
- [Vercel Deployment](../deployment/VERCEL_DEPLOYMENT.md) - Frontend deployment
- [Environment Setup](../deployment/ENVIRONMENT_SETUP.md) - Environment variables reference
- [Local Testing](../deployment/LOCAL_TESTING.md) - Local development setup

### Logs
- [AWS Lambda Deployment Log](./aws-lambda-deployment.md) - Detailed deployment chronicle
- **This File** - Phase 1 summary

---

## Current System State

### Backend Structure
```
backend/
├── main.py                 # FastAPI app + Lambda handler
├── template.yaml           # CloudFormation infrastructure
├── samconfig.toml          # SAM deployment config
├── requirements.txt        # Python dependencies
├── .env                    # Local environment variables
├── config/
│   └── settings.py         # Pydantic settings (ALLOWED_EMAILS hardcoded)
├── auth/
│   ├── routes.py           # /auth/google endpoint
│   ├── utils.py            # JWT creation, Google token verification
│   └── models.py           # Pydantic request/response models
└── api/
    ├── routes.py           # /api/user endpoint (protected)
    └── dependencies.py     # JWT authentication dependency
```

### Frontend Structure
```
frontend/
├── src/
│   ├── App.js              # Main app + routing
│   ├── pages/
│   │   ├── LoginPage.js    # Google OAuth login
│   │   └── InfoPage.js     # Protected user info page
│   └── index.js            # GoogleOAuthProvider setup
├── .env                    # Environment variables (git-ignored)
├── .env.example            # Template for new developers
└── package.json            # Dependencies
```

### Environment Variables

**Backend** (.env):
```bash
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
SECRET_KEY=your-secret-key-use-openssl-rand-hex-32
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
ALLOWED_EMAILS=your-email@gmail.com
```

**Frontend** (.env):
```bash
REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
REACT_APP_API_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod
```

**Secrets Location**: [SECRETS_LOCATION.md](../deployment/SECRETS_LOCATION.md)

---

## What's Next: Phase 2-4 Roadmap

### Phase 2: Web Scraping & Database
**Goal**: Scrape job postings and save to database

**Components**:
- [ ] Set up PostgreSQL database (RDS or Neon)
- [ ] Create database schema (jobs, applications tables)
- [ ] Build web scraping logic (LinkedIn, Indeed, etc.)
- [ ] API endpoints to trigger scraping
- [ ] Store scraped data in database

**To be designed**: Scraping strategy, database schema, scheduling

---

### Phase 3: Search & Add to List
**Goal**: Search scraped jobs and add to personal application tracker

**Components**:
- [ ] Search API (filter by company, title, location, etc.)
- [ ] Frontend search UI
- [ ] "Add to my list" functionality
- [ ] Personal application tracker (status, notes, dates)
- [ ] CRUD endpoints for applications

**To be designed**: Search algorithm, filtering logic, UI/UX

---

### Phase 4: Application Tracking
**Goal**: Track application status through the hiring process

**Components**:
- [ ] Application status workflow (applied, phone screen, onsite, offer, rejected)
- [ ] Notes and follow-up reminders
- [ ] Timeline visualization
- [ ] Email integration (optional)
- [ ] Analytics dashboard

**To be designed**: Status workflow, notification system, analytics

---

## Testing Checklist

- [x] Local development (uvicorn)
- [x] AWS Lambda deployment
- [x] Vercel deployment
- [x] Google OAuth login flow
- [x] JWT authentication
- [x] Email whitelist enforcement
- [x] CORS configuration (localhost + Vercel)
- [x] HTTPS (automatic on both Vercel and API Gateway)
- [ ] End-to-end user flow (pending UI for job tracking)
- [ ] Error handling (partially done)
- [ ] Rate limiting (not implemented yet)

---

## Key Learnings

### AWS SAM
- **template.yaml**: WHAT to deploy (infrastructure blueprint)
- **samconfig.toml**: HOW to deploy (region, parameters, stack name)
- **Events section**: Automatically creates API Gateway when specified
- **CloudFormation**: Tracks all resources in a stack

**Learning Doc**: [AWS SAM Guide](../learning/aws-deployment.md#aws-sam-templateyaml-vs-samconfigtoml)

### Environment Variables in Lambda
- `.env` file: Local development only (not uploaded to Lambda)
- Lambda: Reads from environment variables set via CloudFormation
- Flow: samconfig.toml → template.yaml → Lambda env vars → Pydantic
- **No virtual .env file** - Pydantic reads directly from Lambda runtime

**Learning Doc**: [Environment Variables in AWS Lambda](../learning/aws-deployment.md#environment-variables-in-aws-lambda)

### Vercel Environment Variables
- Must be set via Vercel CLI or dashboard
- Local .env file **not used** in deployed bundle
- Need to redeploy after changing env vars

### Google OAuth
- **Authorized JavaScript Origins**: Frontend URL only (not backend)
- Backend validation is server-to-server (Google doesn't check origins)
- ID token contains: email, name, picture

---

## Performance & Costs

### AWS Lambda (Current Usage)
- **Requests**: ~50-100 test requests
- **Duration**: ~50-200ms per request
- **Memory**: 512 MB configured, ~100 MB used
- **Cost**: $0.00 (within free tier: 1M requests/month)

### Vercel (Current Usage)
- **Bandwidth**: ~10 MB
- **Build time**: ~30 seconds
- **Cost**: $0.00 (within free tier)

### Google Cloud (OAuth)
- **Cost**: $0.00 (free tier: unlimited OAuth requests)

**Total Cost**: $0.00 / month

---

## Quick Commands Reference

### Local Development
```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm start
```

### Deployment
```bash
# Backend to Lambda
cd backend
sam build && sam deploy

# Frontend to Vercel
cd frontend
vercel --prod
```

### Logs
```bash
# Lambda logs (live tail)
sam logs --tail --stack-name jh-backend-stack

# Or via AWS CLI
aws logs tail /aws/lambda/JobHuntTrackerAPI --follow
```

---

## Team
- **Developer**: zduanx@gmail.com
- **AI Assistant**: Claude (Anthropic)

---

**Phase 1 Duration**: ~8 hours (with learning and troubleshooting)
**Phase 1 Lines of Code**: ~500 lines backend + ~200 lines frontend
**Phase 1 Documentation**: ~3,000 lines across 15 files

---

## Resume Session

To resume this project in a new session:

1. **Read**: [AI_ASSISTANT_PREFERENCES.md](../AI_ASSISTANT_PREFERENCES.md) - Session entry point
2. **Review**: This file (PHASE_1_SUMMARY.md) - Current state
3. **Check**: [SYSTEM_DESIGN.md](../architecture/SYSTEM_DESIGN.md) - Architecture overview
4. **Refer**: Phase 2-4 roadmap above for next steps

---

**Status**: Ready for Phase 2 🚀
