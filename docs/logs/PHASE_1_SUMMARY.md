# Phase 1: Full-Stack Authentication & Deployment

**Status**: ✅ Completed
**Date**: December 14, 2025
**Goal**: Build and deploy a production-ready full-stack application with Google OAuth authentication

---

## Overview

Phase 1 established the complete infrastructure and authentication foundation for the job hunt tracker. Built a serverless full-stack application with social login, deployed to production on AWS Lambda (backend) and Vercel (frontend).

**Stack**: React + FastAPI + Google OAuth + JWT

**Included in this phase**:
- Google OAuth → JWT authentication flow
- AWS Lambda serverless backend deployment
- Vercel frontend deployment with CDN
- Email whitelist access control
- Infrastructure as Code (CloudFormation/SAM)
- Local development environment with shortcuts

**Explicitly excluded** (deferred to Phase 2+):
- Database integration
- User data persistence
- Job tracking features

---

## Key Achievements

### 1. End-to-End Authentication Flow
- **Google OAuth**: Social login with popup flow
- **JWT tokens**: Stateless backend authentication
- **Email whitelist**: Access control for authorized users only
- **Protected routes**: Frontend guards requiring valid JWT
- Reference: [Authentication Guide](../learning/authentication.md)

### 2. AWS Lambda Serverless Backend
- **Runtime**: Python 3.13 on Lambda
- **API Gateway**: HTTP API with automatic HTTPS
- **CORS**: Configured for Vercel + localhost origins
- **Environment variables**: Managed via CloudFormation
- **Deployment**: SAM CLI with `sam build && sam deploy`
- Reference: [AWS Lambda Deployment](../deployment/AWS_LAMBDA_DEPLOYMENT.md)

### 3. Vercel Frontend Deployment
- **Auto-deploy**: Git push triggers rebuild
- **CDN**: Global edge network with automatic HTTPS
- **Environment**: Variables set via Vercel CLI
- **OAuth config**: Authorized JavaScript Origins registered
- Reference: [Vercel Deployment](../deployment/VERCEL_DEPLOYMENT.md)

### 4. Infrastructure as Code
- **CloudFormation**: All AWS resources in `template.yaml`
- **SAM**: Simplified Lambda + API Gateway deployment
- **Version control**: Config in git (secrets in .env.local)
- **Reproducible**: One command deployment to any AWS account

### 5. Local Development Environment
- **`.env.local` files**: Standardized environment variable management (git-ignored)
- **dev.sh shortcuts**: Ultra-fast commands (`jbe`, `jfe`, `jready`, `jstatus`, `jkillall`)
- **Port management**: Automatic conflict detection and process cleanup
- **Background processes**: Services survive terminal close
- Reference: [Local Development](../deployment/LOCAL_DEVELOPMENT.md), [DEV_SHORTCUTS.md](../../DEV_SHORTCUTS.md)

### 6. Documentation Infrastructure
- **Architecture docs**: System design, API design, decisions log
- **Learning guides**: AWS, FastAPI, React, OAuth, security (8 topics)
- **Deployment guides**: Step-by-step for Lambda, Vercel, testing, migrations
- **This summary**: Phase 1 chronicle

---

## API Endpoints

**POST `/auth/google`**
- Purpose: Exchange Google ID token for JWT
- Request: `{ credential: string }` (Google ID token)
- Response: `{ access_token: string, user: { email, name, picture } }`
- Auth: None (public endpoint)

**GET `/api/user`**
- Purpose: Get authenticated user info (protected route demo)
- Request: Headers with `Authorization: Bearer <jwt>`
- Response: `{ email, name, picture }`
- Auth: JWT required

**GET `/health`**
- Purpose: Health check endpoint
- Response: `{ status: "healthy" }`
- Auth: None

Reference: [API_DESIGN.md](../architecture/API_DESIGN.md)

---

## Highlights

### OAuth Flow Architecture
Google OAuth frontend button → ID token → Backend validation (server-to-server) → Email whitelist check → JWT issuance → localStorage storage → Protected route access

**Key insight**: Backend validates with Google directly (server-to-server), only frontend URL needs OAuth registration

### Lambda Deployment Iterations (9 attempts)
- Python version mismatch (3.11 vs 3.13)
- Pydantic dependency build failures
- IAM permissions (CloudFormation access required)
- CORS wildcards not allowed with credentials
- Missing dependencies (requests, email-validator)
- FastAPI routing (needed `root_path="/prod"`)
- Reference: [AWS Lambda Deployment Log](./aws-lambda-deployment.md)

### Environment Variable Strategy
- **Local**: `.env.local` files (git-ignored, test database)
- **Lambda**: CloudFormation env vars (production database)
- **Vercel**: Set via CLI/dashboard (not from local .env)
- **Pydantic**: Reads directly from Lambda runtime (no virtual .env)

### Development Shortcuts Design
Shell function wrapper that handles cd + venv activation + dependency checks + port management in single command. Background mode uses nohup with PID tracking for process management.

---

## Testing & Validation

**Manual Testing**:
- ✅ Local development (uvicorn + React dev server)
- ✅ AWS Lambda deployment and invocation
- ✅ Vercel deployment with CDN
- ✅ Google OAuth login flow (popup + token exchange)
- ✅ JWT token generation and validation
- ✅ Email whitelist enforcement
- ✅ CORS configuration (localhost + Vercel)
- ✅ HTTPS on both platforms (automatic)
- ✅ End-to-end user flow
- ✅ Error handling (unauthorized, invalid tokens)

**Automated Testing**:
- Future: pytest test suite planned (Phase 2B)

---

## Metrics

- **Backend**: ~500 lines Python (FastAPI + auth)
- **Frontend**: ~200 lines React (OAuth + routing)
- **Documentation**: ~3,000 lines across 15 files
- **Infrastructure**: 2 deployment platforms (AWS Lambda, Vercel)
- **Deployment iterations**: 9 (Lambda), 2 (Vercel)
- **Development time**: ~8 hours (including learning and troubleshooting)
- **Cost**: $0.00/month (free tier)

---

## Next Steps → Phase 2

**Target**: Complete job ingestion workflow from URL sourcing to database persistence

---

## File Structure

```
backend/
├── main.py                # FastAPI app + Lambda handler
├── template.yaml          # CloudFormation infrastructure
├── samconfig.toml         # SAM deployment config
├── requirements.txt       # Python dependencies
├── .env.local             # Local environment (git-ignored)
├── config/
│   └── settings.py        # Pydantic settings (email whitelist)
├── auth/
│   ├── routes.py          # /auth/google endpoint
│   ├── utils.py           # JWT creation, Google token verification
│   └── models.py          # Pydantic request/response models
└── api/
    ├── routes.py          # /api/user endpoint (protected)
    └── dependencies.py    # JWT authentication dependency

frontend/
├── src/
│   ├── App.js             # Main app + routing
│   ├── pages/
│   │   ├── LoginPage.js   # Google OAuth login
│   │   └── InfoPage.js    # Protected user info page
│   └── index.js           # GoogleOAuthProvider setup
├── .env.local             # Environment variables (git-ignored)
├── .env.example           # Template for new developers
└── package.json           # Dependencies

Root/
├── dev.sh                 # Development shortcuts
└── DEV_SHORTCUTS.md       # Shortcuts documentation
```

**Key Files**:
- [main.py](../../backend/main.py) - FastAPI application and Lambda handler
- [template.yaml](../../backend/template.yaml) - AWS infrastructure definition
- [LoginPage.js](../../frontend/src/pages/LoginPage.js) - OAuth implementation
- [dev.sh](../../dev.sh) - Development shortcuts script

---

## Key Learnings

### AWS SAM Deployment
**template.yaml** defines WHAT to deploy (infrastructure), **samconfig.toml** defines HOW (region, parameters). SAM automatically creates API Gateway when Events section specified in template.

**Reference**: [AWS SAM Guide](../learning/aws.md#aws-sam-templateyaml-vs-samconfigtoml)

### Lambda Environment Variables
Lambda reads env vars directly from CloudFormation (no .env file uploaded). Pydantic loads from Lambda runtime environment, not from file.

**Reference**: [AWS Environment Variables](../learning/aws.md#environment-variables-in-aws-lambda)

### Vercel Deployment
Local `.env` file not used in deployed bundle. Must set env vars via Vercel CLI or dashboard. Requires redeploy after changing variables.

### Google OAuth Origins
Authorized JavaScript Origins require only frontend URL (not backend). Backend validation is server-to-server with Google, which doesn't check origins.

---

## References

**External Documentation**:
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2) - OAuth protocol
- [AWS Lambda Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html) - Lambda runtime
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Web framework
- [Vercel Platform](https://vercel.com/docs) - Deployment platform
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - Configuration management
