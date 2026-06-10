# Job Hunt Tracker

A full-stack job application tracking system with AI-native features — semantic search, a RAG chat agent, and an **autonomous code-discovery agent** — built with React and FastAPI, deployed on AWS Lambda and Vercel. **Every component is hand-rolled and explainable cold (no agent/RAG frameworks).**

**Status**: Phases 1–8 Complete

---

## Features

**Core**
- **Google OAuth Authentication** - Secure login with JWT tokens and email whitelist
- **Job Ingestion Pipeline** - Automated crawling of company career pages with SimHash deduplication
- **Hybrid Search** - Full-text and fuzzy search across job titles and descriptions
- **Application Tracking** - Stages (interested → applied → screening → interview → offer)
- **Calendar View** · **Resume Management** (direct-to-S3 presigned uploads) · **STAR Interview Stories**
- **Real-time Progress** - Server-Sent Events (SSE) for ingestion status

**AI / Agents (the hard, hand-built parts)**
- **Semantic Search & RAG** - Voyage embeddings + pgvector (HNSW) for resume↔job matching; hand-rolled retrieve→augment→generate
- **Chat Agent** - A hand-written ReAct loop over a standalone **MCP server** (job/resume tools), with conversation summarization and an offline **LLM-as-judge eval** harness (faithfulness/relevancy)
- **Autonomous Extractor-Discovery Agent (Phase 8)** - Given a company + careers URL, it **plans → runs untrusted LLM-generated code in a Docker sandbox → reverse-engineers the company's job-listing API → writes a verified, runnable extractor (multi-file)** for human review (git diff). Cracked 4 different ATS systems + a custom WordPress endpoint across 5 companies. A **dedicated sub-agent** isolates heavy site exploration; prompt caching + the sub-agent gave a **measured 77% reduction in billed tokens** on the hard case.

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
- **Database**: PostgreSQL (Neon - serverless) + **pgvector** (HNSW) for embeddings
- **Queue**: AWS SQS FIFO (rate-limited crawling)
- **Storage**: AWS S3 (raw HTML, resumes)
- **Real-time**: Server-Sent Events (SSE)

### AI / Agents
- **LLMs**: Anthropic Claude (chat agent, discovery agent, eval judge) — with prompt caching
- **Embeddings**: Voyage AI (1024-dim) over pgvector
- **MCP**: a standalone Model Context Protocol server (FastMCP) exposing job/resume tools
- **Sandbox**: Docker (isolated, no-secrets, resource-limited) for running untrusted LLM-generated code
- **No frameworks**: the ReAct loop, RAG, MCP client, plan-and-execute, sub-agents, and eval are all hand-rolled (ADR-029) — explainable without framework magic

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
│   ├── template.yaml        # AWS SAM infrastructure (API, worker, MCP server Lambdas)
│   ├── api/                 # API routes
│   ├── auth/                # Authentication logic
│   ├── config/              # Settings (Pydantic)
│   ├── models/              # SQLAlchemy models
│   ├── extractors/          # v1 company career-page extractors
│   ├── mcp_server/          # standalone MCP server (FastMCP) — job/resume tools (Phase 7)
│   ├── extractor_agent/     # Phase 8: the autonomous discovery agent
│   │   ├── discover.py      #   plan-and-execute + ReAct loop, sub-agent, caching, instrumentation
│   │   ├── prompts.py       #   Pydantic-validated structured output + per-stage prompts
│   │   ├── tools.py         #   scoped read/write file tools (read-before-write)
│   │   └── sandbox/         #   Docker harness (run untrusted trial code safely)
│   ├── extractors_v2_base/  #   the agent's contract (baked into the sandbox image)
│   ├── extractors_v2/       #   the agent's GENERATED extractors + registry
│   └── alembic/             # Database migrations
├── chat/                    # chat agent (Node): hand-rolled ReAct loop + MCP client (Phase 7)
├── eval/                    # offline LLM-as-judge eval harness (Phase 7E)
├── frontend/
│   └── src/ { App.js, pages/, components/ }
├── docs/
│   ├── architecture/        # System design, API specs, ADRs (34)
│   ├── deployment/          # Deployment guides
│   ├── learning/            # Tech learning notes (RAG/eval, agent engineering)
│   └── logs/                # Phase summaries (1–8)
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
| `/api/stories` | GET/POST | List/create stories |
| `/api/stories/{id}` | GET/PATCH/DELETE | Story CRUD |

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
| ADR-029 | Hand-roll the agent loop (no LangChain/Vercel AI SDK) | Explainable cold; own the mechanics |
| ADR-030 | Standalone MCP server (multi-client) | Tools across a process boundary |
| ADR-034 | Local Docker sandbox (dev) → Lambda the prod path | The sub-step that runs untrusted code |

See [DECISIONS.md](docs/architecture/DECISIONS.md) for all 33 ADRs (001–034; 007 unused).

---

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Authentication & AWS/Vercel deployment | Complete |
| 2 | Job ingestion pipeline (crawling, extraction, SSE) | Complete |
| 3 | Search page with fuzzy search | Complete |
| 4 | Job tracking, events, resume upload, calendar | Complete |
| 5 | Behavioral interview stories (STAR format) | Complete |
| 6 | Vector embeddings + semantic search (pgvector/HNSW) | Complete |
| 7 | RAG chat agent — hand-rolled ReAct loop, MCP server, summarization, eval | Complete |
| 8 | **Autonomous extractor-discovery agent** — sandboxed code gen, sub-agent, 77% token reduction | Complete |

Phase summaries: [docs/logs/](docs/logs/). Agent-engineering lessons: [agent-discovery-prompts.md](docs/learning/agent-discovery-prompts.md), [vectors-rag-eval.md](docs/learning/vectors-rag-eval.md).

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
