# Job Hunt Tracker

A full-stack job application tracking system built with React and FastAPI.

**Status**: Phase 1 Complete ✅

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
- **Future:** PostgreSQL, Redis, Web Scraping

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
├── docs/
│   ├── architecture/      # Architecture decisions and system design
│   │   ├── DECISIONS.md
│   │   ├── SYSTEM_DESIGN.md
│   │   └── API_DESIGN.md
│   └── learning/          # Learning notes and references
│       ├── README.md      # Quick topic index
│       ├── authentication.md
│       ├── aws-deployment.md
│       ├── backend.md
│       ├── frontend.md
│       └── security.md
├── backend/               # FastAPI backend
├── frontend/              # React frontend
└── README.md             # This file
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

**Phase 1 - COMPLETE ✅**
- [x] Project structure and documentation
- [x] FastAPI backend with Google OAuth
- [x] React frontend with Google login
- [x] Email whitelist access control
- [x] Local testing
- [x] Deploy to AWS Lambda + API Gateway
- [x] Deploy to Vercel
- [x] HTTPS on both frontend and backend

**Phase 2 (Planned) - Web Scraping & Database:**
- Database setup (PostgreSQL on RDS or Neon)
- Web scraping logic (LinkedIn, Indeed, etc.)
- Scraping API endpoints
- Data storage pipeline

**Phase 3 (Planned) - Search & Add to List:**
- Search API with filtering
- Frontend search UI
- Personal application tracker
- Application CRUD endpoints

**Phase 4 (Planned) - Application Tracking:**
- Status workflow (applied → interview → offer)
- Notes and reminders
- Timeline visualization
- Analytics dashboard

See [docs/logs/PHASE_1_SUMMARY.md](docs/logs/PHASE_1_SUMMARY.md) for detailed Phase 1 recap.

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
