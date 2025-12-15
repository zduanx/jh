# Job Hunt Tracker

A full-stack job application tracking system built with React and FastAPI.

**Status**: Phase 2 In Progress 🚧

---

## 🚀 For AI Assistants: Resume Session

**Start here**: [docs/SESSION_GUIDE.md](docs/SESSION_GUIDE.md)

This guide contains:
- Project current status
- Quick links to all documentation
- Codebase structure
- Environment variables
- AI assistant behavior preferences

---

## Project Overview

**Purpose:** Track job applications across multiple companies with automated web scraping.

**Tech Stack:**
- **Frontend:** React (Vercel) ✅ Deployed
- **Backend:** FastAPI (AWS Lambda + API Gateway) ✅ Deployed
- **Auth:** Google OAuth + JWT ✅ Working
- **URL Sourcing:** 6 company extractors ✅ Working
- **Phase 2:** SQS Queues, S3 Storage, Web Crawling, Parsing 🚧 In Progress
- **Future:** PostgreSQL/Neon, WebSocket, Application Tracking

**Goals:**
1. Build practical job hunting tool
2. Practice system design skills
3. Learn AI-assisted development
4. Deploy to production

---

## Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.13
- Google OAuth credentials
- AWS account (for deployment)

### Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Add your secrets
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env  # Add your config
npm start
```

---

## Project Structure

```
jh/
├── docs/                  # All project documentation
│   ├── SESSION_GUIDE.md   # 👈 START HERE (AI assistant entry point)
│   ├── architecture/      # Architecture decisions and system design
│   ├── deployment/        # Deployment guides
│   ├── learning/          # Learning notes
│   └── logs/              # Development logs and summaries
│
├── src/                   # Production source code (Phase 1-2)
│   └── extractors/        # Job URL extractors (6 companies)
│       ├── enums.py       # Company enum
│       ├── registry.py    # Extractor registry
│       ├── base_extractor.py  # Abstract base class
│       ├── config.py      # Configuration models
│       └── {company}.py   # Google, Amazon, Anthropic, TikTok, Roblox, Netflix
│
├── backend/               # FastAPI backend (AWS Lambda)
│   ├── main.py            # Lambda handler
│   ├── template.yaml      # CloudFormation/SAM
│   └── sourcing/          # URL sourcing API
│
├── frontend/              # React frontend (Vercel)
│   └── src/               # React components
│
└── trials/                # Experimental code + API snapshots
```

---

## Documentation

### Architecture Docs
- **[Architecture Decisions](docs/architecture/DECISIONS.md)** - All major tech decisions with reasoning
- **[System Design](docs/architecture/SYSTEM_DESIGN.md)** - Overall architecture and future plans
- **[API Design](docs/architecture/API_DESIGN.md)** - API endpoints and contracts

### Learning Notes
Start with **[docs/learning/README.md](docs/learning/README.md)** for quick topic lookup.

**Topics covered:**
- OAuth, JWT, authentication strategies
- AWS services (EC2, Lambda, API Gateway)
- FastAPI vs Django, REST vs GraphQL
- React, routing, protected routes
- Security best practices (HTTPS, token storage, vulnerabilities)

---

## Current Status

**Phase 1 - Authentication & Deployment** ✅ COMPLETE
- [x] FastAPI backend with Google OAuth + JWT
- [x] React frontend with protected routes
- [x] Email whitelist access control
- [x] Deploy to AWS Lambda + API Gateway (HTTPS)
- [x] Deploy to Vercel (HTTPS)
- [x] Full Phase 1 Summary: [docs/logs/PHASE_1_SUMMARY.md](docs/logs/PHASE_1_SUMMARY.md)

**Phase 2 - Job URL Sourcing & Crawling Pipeline** 🚧 IN PROGRESS

*Phase 2A: URL Generation (Completed)*
- [x] Base extractor architecture (single class per company)
- [x] 6 company extractors (Google, Amazon, Anthropic, TikTok, Roblox, Netflix)
- [x] Title filtering with include/exclude patterns
- [x] FastAPI endpoint: POST /api/sourcing (dry_run mode)
- [x] Location field standardization (city, state)
- [x] Company enum + registry with no lazy loading

*Phase 2B: Crawling & Parsing (Next)*
- [ ] Add `crawl_job(url)` methods to extractors
- [ ] JobCrawlerLambda (crawling service)
- [ ] SQS Queue A (URLs to crawl) + Queue B (IDs to parse)
- [ ] S3 bucket for raw HTML storage
- [ ] Database setup (Neon/RDS/DynamoDB - TBD)
- [ ] Database schema (jobs, user_settings tables)
- [ ] SourceURLLambda updates (SQS sending when dry_run=false)
- [ ] Settings API (POST/GET /api/settings)
- [ ] Companies API (GET /api/companies)
- [ ] Queue status API (GET /api/queue/status)
- [ ] Add `parse_job(html)` methods to extractors
- [ ] JobParserLambda (parsing service)

*Pending Decisions (See [DECISIONS.md](docs/architecture/DECISIONS.md#phase-2-pending-decisions))*
- Database choice (PostgreSQL vs Neon vs DynamoDB)
- Settings storage strategy
- Crawling rate limits per company
- Error handling (SQS DLQ, retry logic)
- S3 cleanup policy
- WebSocket vs polling for real-time updates

**Phase 3 - Search & Application Tracking** (Planned)
- Search API with filtering
- Personal job tracker (add to list, CRUD operations)
- Application status workflow

**Phase 4 - Analytics & Enhancements** (Planned)
- Timeline visualization
- Analytics dashboard
- Email notifications

See [SYSTEM_DESIGN.md](docs/architecture/SYSTEM_DESIGN.md) for detailed Phase 2 architecture.

---

## Commands

### Backend
```bash
# Run development server
uvicorn main:app --reload

# Run tests (coming soon)
pytest

# Format code
black .
```

### Frontend
```bash
# Run development server
npm start

# Build for production
npm run build

# Run tests (coming soon)
npm test
```

---

## Environment Variables

### Backend (.env)
```bash
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
SECRET_KEY=your-jwt-secret-key-32-chars-minimum
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app
ALLOWED_EMAILS=your-email@gmail.com
```

### Frontend (.env)
```bash
REACT_APP_GOOGLE_CLIENT_ID=your-client-id
REACT_APP_API_URL=http://localhost:8000  # Development
# REACT_APP_API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/prod  # Production
```

See [docs/deployment/ENVIRONMENT_SETUP.md](docs/deployment/ENVIRONMENT_SETUP.md) for complete details.

---

## Deployment

### Backend (AWS Lambda + API Gateway)
See [docs/deployment/AWS_LAMBDA_DEPLOYMENT.md](docs/deployment/AWS_LAMBDA_DEPLOYMENT.md)

**Quick Deploy:**
```bash
cd backend
sam build && sam deploy
```

### Frontend (Vercel)
See [docs/deployment/VERCEL_DEPLOYMENT.md](docs/deployment/VERCEL_DEPLOYMENT.md)

**Quick Deploy:**
```bash
cd frontend
vercel --prod
```

---

## Learning Resources

All concepts discussed during development are documented in `docs/learning/`:

- **"What is OAuth?"** → [authentication.md](docs/learning/authentication.md#what-is-oauth)
- **"EC2 or Lambda?"** → [aws-deployment.md](docs/learning/aws-deployment.md#ec2-vs-lambda)
- **"JWT vs Sessions?"** → [authentication.md](docs/learning/authentication.md#jwt-vs-sessions)
- **"FastAPI vs Django?"** → [backend.md](docs/learning/backend.md#fastapi-vs-django)
- **"Is JWT secure?"** → [security.md](docs/learning/security.md#jwt-security)

---

## License

MIT

---

## Acknowledgments

Built with AI assistance (Claude Code) as a learning project for system design and full-stack development.
