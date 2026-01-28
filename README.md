# Job Hunt Tracker

A full-stack job application tracking system built with React and FastAPI, deployed on AWS Lambda and Vercel.

**Status**: All Phases Complete

---

## Features

- **Google OAuth Authentication** - Secure login with JWT tokens and email whitelist
- **Job Ingestion Pipeline** - Automated crawling of company career pages with SimHash deduplication
- **Hybrid Search** - Full-text and fuzzy search across job titles and descriptions
- **Application Tracking** - Track jobs through stages (interested, applied, screening, interview, offer)
- **Calendar View** - Visual overview of upcoming interviews and application events
- **Resume Management** - Direct-to-S3 upload with presigned URLs
- **Real-time Progress** - Server-Sent Events (SSE) for ingestion status updates

---

## Tech Stack

### Frontend
- React 19 with React Router
- Google OAuth (@react-oauth/google)
- Hosted on Vercel (global CDN)

### Backend
- FastAPI (Python 3.13)
- SQLAlchemy + Alembic (ORM + migrations)
- Mangum (Lambda adapter)
- Hosted on AWS Lambda + API Gateway

### Infrastructure
- **Database**: PostgreSQL (Neon - serverless)
- **Queue**: AWS SQS FIFO (rate-limited crawling)
- **Storage**: AWS S3 (raw HTML, resumes)
- **Real-time**: Server-Sent Events (SSE)

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React App     │────▶│  API Gateway    │────▶│  AWS Lambda     │
│   (Vercel)      │     │  + Lambda       │     │  Workers        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   PostgreSQL    │     │   AWS SQS       │
                        │   (Neon)        │     │   + S3          │
                        └─────────────────┘     └─────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+
- AWS CLI configured
- Google OAuth credentials

### Local Development

1. **Clone and setup environment files**
   ```bash
   # Backend
   cp backend/.env.example backend/.env.local

   # Frontend
   cp frontend/.env.example frontend/.env.local
   ```

2. **Load development shortcuts**
   ```bash
   source dev.sh
   jh-help  # See all available commands
   ```

3. **Start backend (Terminal 1)**
   ```bash
   source dev.sh
   jh-start-be
   ```

4. **Start frontend (Terminal 2)**
   ```bash
   source dev.sh
   jh-start-fe
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Dev Shortcuts Reference

| Command | Description |
|---------|-------------|
| `jh-start-be` | Start backend server |
| `jh-start-fe` | Start frontend server |
| `jh-start-be-bg` | Start backend in background |
| `jh-start-fe-bg` | Start frontend in background |
| `jh-kill-all` | Stop all services |
| `jh-status` | Check what's running |
| `jh-be` | Navigate to backend directory |
| `jh-fe` | Navigate to frontend directory |

---

## Project Structure

```
jh/
├── backend/
│   ├── main.py              # FastAPI app + Lambda handler
│   ├── template.yaml        # AWS SAM infrastructure
│   ├── requirements.txt     # Python dependencies
│   ├── api/                 # API routes
│   ├── auth/                # Authentication logic
│   ├── config/              # Settings (Pydantic)
│   ├── models/              # SQLAlchemy models
│   ├── extractors/          # Company career page extractors
│   └── alembic/             # Database migrations
├── frontend/
│   ├── src/
│   │   ├── App.js           # Main app + routing
│   │   ├── pages/           # Page components
│   │   └── components/      # Shared components
│   └── package.json
├── docs/
│   ├── architecture/        # System design, API specs, ADRs
│   ├── deployment/          # Deployment guides
│   ├── learning/            # Tech learning notes
│   └── logs/                # Phase summaries
└── dev.sh                   # Development shortcuts
```

---

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/google` | POST | Google OAuth login |
| `/api/user` | GET | Get current user |
| `/api/ingestion/dry-run` | POST | Preview job extraction |
| `/api/ingestion/start` | POST | Start ingestion run |
| `/api/ingestion/progress/{id}` | GET | SSE progress stream |
| `/api/jobs` | GET | List/search jobs |
| `/api/tracked` | GET/POST | Tracked jobs management |
| `/api/tracked/{id}` | PATCH/DELETE | Update/remove tracking |
| `/api/tracked/calendar/events` | GET | Calendar events |

See [API_DESIGN.md](docs/architecture/API_DESIGN.md) for complete documentation.

---

## Deployment

### Backend (AWS Lambda)

```bash
cd backend
sam build && sam deploy
```

See [AWS_LAMBDA_DEPLOYMENT.md](docs/deployment/AWS_LAMBDA_DEPLOYMENT.md) for detailed guide.

### Frontend (Vercel)

Push to GitHub for automatic deployment, or:

```bash
cd frontend
vercel --prod
```

See [VERCEL_DEPLOYMENT.md](docs/deployment/VERCEL_DEPLOYMENT.md) for detailed guide.

---

## Documentation

| Document | Description |
|----------|-------------|
| [SYSTEM_DESIGN.md](docs/architecture/SYSTEM_DESIGN.md) | High-level architecture |
| [API_DESIGN.md](docs/architecture/API_DESIGN.md) | API endpoint specifications |
| [DECISIONS.md](docs/architecture/DECISIONS.md) | Architecture Decision Records (ADRs) |
| [LOCAL_DEVELOPMENT.md](docs/deployment/LOCAL_DEVELOPMENT.md) | Local setup guide |
| [ENV_VARIABLES.md](docs/deployment/ENV_VARIABLES.md) | Environment configuration |

---

## Key Design Decisions

| ADR | Decision | Why |
|-----|----------|-----|
| ADR-004 | AWS Lambda over EC2 | Serverless, permanent free tier |
| ADR-012 | Neon over RDS | Serverless PostgreSQL, instant setup |
| ADR-014 | Hybrid text search | Full-text + pg_trgm fuzzy matching |
| ADR-016 | SSE over WebSocket | Simpler, built-in auto-reconnect |
| ADR-017 | SimHash deduplication | Fuzzy content matching for unchanged pages |
| ADR-020 | SQS FIFO + MessageGroupId | Per-company rate limiting |
| ADR-024 | Presigned URLs for uploads | Bypass Lambda memory/timeout limits |

See [DECISIONS.md](docs/architecture/DECISIONS.md) for all 24 ADRs.

---

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Authentication & AWS/Vercel deployment | Complete |
| 2 | Job ingestion pipeline (crawling, extraction, SSE) | Complete |
| 3 | Search page with fuzzy search | Complete |
| 4 | Job tracking, events, resume upload, calendar | Complete |

Phase summaries: [docs/logs/](docs/logs/)

---

## Cost

Running entirely on free tier:

| Service | Free Tier |
|---------|-----------|
| AWS Lambda | 1M requests/month |
| Neon PostgreSQL | 0.5 GB storage |
| Vercel | Unlimited static hosting |
| **Total** | **$0/month** |

---

## License

Private project for learning purposes.

---

## Acknowledgments

Built with AI assistance (Claude Code) as a learning project for system design and full-stack development.
