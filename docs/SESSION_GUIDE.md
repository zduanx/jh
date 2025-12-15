# Session Entry Point

**Purpose**: This file is the entry point for resuming AI assistant sessions. Read this first when starting a new session.

**Last Updated:** 2024-12-14

---

## Quick Start: Resuming a Session

When starting a new AI session, follow these steps:

1. **Read this file first** (you're here!)
2. **Check current status**: [Phase 1 Summary](./logs/PHASE_1_SUMMARY.md)
3. **Review architecture**: [System Design](./architecture/SYSTEM_DESIGN.md)
4. **Check recent changes**: `git log --oneline -10`

---

## Project Status

**Current Phase**: Phase 2A Complete ✅, Phase 2B In Progress 🚧
**Last Session**: 2024-12-15
**Next Steps**: Phase 2B Implementation (see detailed plan below)

### What's Working (Phase 1)
- ✅ Google OAuth authentication
- ✅ JWT token generation and validation
- ✅ Email whitelist access control
- ✅ AWS Lambda + API Gateway deployment (auth endpoints)
- ✅ Vercel frontend deployment
- ✅ CORS configured (localhost + production)
- ✅ HTTPS on both frontend and backend

### What's Working (Phase 2A)
- ✅ 6 company extractors (Google, Amazon, Anthropic, TikTok, Roblox, Netflix)
- ✅ Base extractor architecture with title filtering
- ✅ Company enum + registry system
- ✅ POST /api/sourcing endpoint added to Lambda (dry_run mode)
- ✅ Async parallel extraction orchestrator
- ✅ Location field standardization

**Note:** The same Lambda now handles both auth (Phase 1) and sourcing (Phase 2A) endpoints. We call it "SourceURLLambda" to reflect its expanded role.

### Quick Links
- **Live Frontend**: https://your-app.vercel.app - Read local .env for more info
- **Live Backend**: https://your-api-id.execute-api.us-east-1.amazonaws.com/prod - Read local .env for more info
- **Phase 1 Summary**: [PHASE_1_SUMMARY.md](./logs/PHASE_1_SUMMARY.md)
- **Phase 2-4 Roadmap**: [SYSTEM_DESIGN.md](./architecture/SYSTEM_DESIGN.md#future-architecture-phase-2-4)

---

## Key Documentation Files

### Start Here
- **[PHASE_1_SUMMARY.md](./logs/PHASE_1_SUMMARY.md)** - Comprehensive Phase 1 recap, current state, next steps

### Architecture
- **[SYSTEM_DESIGN.md](./architecture/SYSTEM_DESIGN.md)** - Overall system design, tech stack, Phase 2-4 roadmap
- **[API_DESIGN.md](./architecture/API_DESIGN.md)** - API endpoints, request/response formats
- **[DECISIONS.md](./architecture/DECISIONS.md)** - Technical decision log

### Deployment
- **[AWS_LAMBDA_DEPLOYMENT.md](./deployment/AWS_LAMBDA_DEPLOYMENT.md)** - Backend deployment guide
- **[VERCEL_DEPLOYMENT.md](./deployment/VERCEL_DEPLOYMENT.md)** - Frontend deployment guide
- **[ENVIRONMENT_SETUP.md](./deployment/ENVIRONMENT_SETUP.md)** - Environment variables reference
- **[SECRETS_LOCATION.md](./deployment/SECRETS_LOCATION.md)** - Where secrets are stored

### Learning Resources
- **[aws-deployment.md](./learning/aws-deployment.md)** - AWS SAM, Lambda, API Gateway concepts
- **[authentication.md](./learning/authentication.md)** - OAuth, JWT, security patterns
- **[backend.md](./learning/backend.md)** - FastAPI, Pydantic, Python
- **[frontend.md](./learning/frontend.md)** - React, routing, state management
- **[security.md](./learning/security.md)** - HTTPS, CORS, token storage

### Logs
- **[aws-lambda-deployment.md](./logs/aws-lambda-deployment.md)** - Detailed deployment chronicle with errors and fixes

---

## Codebase Structure

```
jh/
├── backend/                 # FastAPI backend (AWS Lambda)
│   ├── main.py             # FastAPI app + Lambda handler
│   ├── template.yaml       # CloudFormation infrastructure
│   ├── samconfig.toml      # SAM deployment config
│   ├── requirements.txt    # Python dependencies
│   ├── .env                # Local env vars (git-ignored)
│   ├── config/
│   │   └── settings.py     # Pydantic settings (ALLOWED_EMAILS hardcoded)
│   ├── auth/               # Authentication routes + utils
│   └── api/                # Protected API routes
│
├── frontend/               # React frontend (Vercel)
│   ├── src/
│   │   ├── App.js         # Main app + routing
│   │   ├── pages/
│   │   │   ├── LoginPage.js    # Google OAuth login
│   │   │   └── InfoPage.js     # Protected user page
│   │   └── index.js       # GoogleOAuthProvider setup
│   ├── .env               # Local env vars (git-ignored)
│   └── package.json
│
└── docs/                   # All documentation (this folder)
    ├── AI_ASSISTANT_PREFERENCES.md  # This file (session entry point)
    ├── architecture/       # System design, API design, decisions
    ├── deployment/         # Deployment guides, environment setup
    ├── learning/          # Educational content (AWS, auth, etc.)
    └── logs/              # Deployment logs, phase summaries
```

---

## Current Environment Variables

### Backend (.env)
```bash
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
SECRET_KEY=your-secret-key-32-chars-minimum-use-openssl-rand-hex-32
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
ALLOWED_EMAILS=your-email@gmail.com  # Hardcoded in settings.py
```

### Frontend (.env)
```bash
REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
REACT_APP_API_URL=https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
```

---

## AI Assistant Behavior Preferences

Below are the user's preferences for AI assistant behavior during development.

---

## Tool Usage Permissions

### ✅ Always Proceed (No Permission Needed)

#### 1. Directory Creation
- **Command:** `mkdir` (any directory)
- **Reason:** Safe operation, easy to undo
- **Example:** `mkdir -p backend/api/routes`

#### 2. Documentation Files
- **Scope:** Any files in `docs/` folder and all subfolders
- **Operations:** Create, edit, update, delete
- **Reason:** Documentation is low-risk and meant to be iterative
- **Includes:**
  - `docs/architecture/*.md`
  - `docs/learning/*.md`
  - Any new subdirectories under `docs/`

---

## Workflow Guidelines

### Updating backend/extractors Logic

**IMPORTANT: Always check trials folder first**

Before making ANY changes to `backend/extractors/` logic:

1. **Check for API response snapshots:**
   - Look in `trials/{company_name}/` for response examples
   - Review snapshot files (e.g., `trials/tiktok/trial_3/tiktok_api_response_snapshot.json`)
   - Understand the actual API structure before making assumptions

2. **Why this matters:**
   - API docs may be outdated or incomplete
   - Real response structures often differ from expectations
   - Prevents bugs like wrong ID fields, missing location data, etc.

3. **If no snapshot exists:**
   - Create one first by dumping actual API responses
   - Save in `trials/{company_name}/` with descriptive filename
   - Document any quirks in comments

**Example issues caught by checking trials:**
- Amazon has TWO id fields (`id` = UUID, `id_icims` = job number)
- TikTok has nested `city_info` structure, not flat `location`
- Anthropic uses `office` field instead of `location`

### Adding to Learning Documentation

**When discussing new concepts:**

1. **If content is valuable for learning:**
   - AI should proactively suggest: "This would be good to add to learning docs. Should I add it to [specific file]?"
   - Wait for user approval before adding

2. **If updating existing learning content:**
   - Go ahead and update directly (covered by permission #2 above)
   - No need to ask

3. **If creating NEW learning files:**
   - Ask first: "Should I create a new file `docs/learning/new-topic.md` for this?"
   - Wait for approval

**Example Good Behavior:**
```
User: "What's the difference between WebSocket and Server-Sent Events?"
AI: [Explains concept]
AI: "This SSE vs WebSocket comparison would be useful in learning docs.
     Should I add it to docs/learning/backend.md under a new section?"
User: "Yes"
AI: [Adds content immediately]
```

**Example Bad Behavior:**
```
User: "What's SSE?"
AI: [Explains and immediately adds to docs without asking]
❌ Should have asked first for NEW content
```

---

## Code Files (Outside docs/)

### ❌ Always Ask Permission

For any files outside `docs/` folder:
- **Backend code:** `backend/**/*.py`
- **Frontend code:** `frontend/**/*`
- **Config files:** `.env`, `requirements.txt`, `package.json`, etc.
- **Root files:** `README.md` (wait, this one needs clarification...)

**Exception:** `README.md` in project root
- If it's documentation updates (architecture, setup instructions): ✅ Go ahead
- If it's substantial changes: Ask first

---

## Summary Table

| Action | Permission Needed? | Notes |
|--------|-------------------|-------|
| `mkdir` any directory | ✅ No | Always proceed |
| Create/edit `docs/**/*.md` | ✅ No | Always proceed |
| Add NEW concepts to learning | ⚠️ Ask first | Suggest, then wait for approval |
| Update existing learning docs | ✅ No | Already approved content |
| Edit code files (backend/frontend) | ❌ Yes | Always ask |
| Edit config files (.env, etc.) | ❌ Yes | Always ask |
| Project root README.md | ⚠️ Depends | Docs updates OK, major changes ask |

---

## Rationale

**Why `mkdir` is always OK:**
- Low-risk operation
- Easy to undo (just delete directory)
- Doesn't modify existing files

**Why `docs/` is always OK:**
- Documentation is meant to evolve
- Low risk of breaking anything
- User can review git diff if needed
- Enables faster iteration

**Why ask for new learning content:**
- Ensures user finds it valuable
- Prevents doc bloat
- User controls what's worth documenting

---

## Future Preferences

Add new preferences here as they come up:

- [ ] TBD

---

## Next Session Implementation Plan

**Phase 2B Tasks (In Priority Order):**

### 1. User Settings System
**Goal:** Allow users to configure which companies to crawl and set title filters

**Tasks:**
- [ ] Design database schema for user_settings table
- [ ] Design frontend settings page UI
- [ ] Implement backend settings API:
  - POST /api/settings (save user settings)
  - GET /api/settings/:user_id (retrieve user settings)
- [ ] Connect frontend to backend settings API
- [ ] Test settings save/load flow

**Decision needed:** Database choice (see PDR-001 below)

---

### 2. Deploy SourceURLLambda + Frontend Integration
**Goal:** Deploy current Phase 2A work and connect with frontend

**Tasks:**
- [ ] Deploy updated SourceURLLambda (with /api/sourcing endpoint)
- [ ] Create frontend page to trigger sourcing
- [ ] Display dry_run results on frontend (company results, job counts, included/excluded jobs)
- [ ] Test end-to-end flow: Frontend → SourceURLLambda → Display results

---

### 3. Implement Crawling & Parsing Logic
**Goal:** Add crawl_job() and parse_job() methods to extractors

**Tasks:**
- [ ] Implement `crawl_job(url: str) -> str` method in base extractor
- [ ] Implement crawl_job() for each company (6 companies)
- [ ] Implement `parse_job(html: str) -> Dict` method in base extractor
- [ ] Implement parse_job() for each company (6 companies)
- [ ] Test crawling and parsing locally

**Decision needed:** Rate limits per company (see PDR-003 below)

---

### 4. Database Setup
**Goal:** Set up database for storing job data and user settings

**Tasks:**
- [ ] Choose database (Neon vs RDS PostgreSQL vs DynamoDB)
- [ ] Create database schema:
  - users table (if not exists)
  - user_settings table
  - jobs table
- [ ] Set up database connection in backend
- [ ] Test CRUD operations

**Decision needed:** Database choice (see PDR-001 below)

---

### 5. SQS Queues + Lambda Functions
**Goal:** Set up async crawling and parsing pipeline

**Tasks:**
- [ ] Create SQS Queue A (job URLs to crawl)
- [ ] Create SQS Queue B (job IDs to parse)
- [ ] Create JobCrawlerLambda function
- [ ] Create JobParserLambda function
- [ ] Set up Lambda triggers from SQS queues
- [ ] Update SourceURLLambda to send to SQS when dry_run=false
- [ ] Set up S3 bucket for raw HTML storage
- [ ] Test full pipeline: SourceURLLambda → Queue A → JobCrawlerLambda → S3 + DB → Queue B → JobParserLambda → DB

**Decisions needed:**
- Error handling strategy (see PDR-004 below)
- S3 cleanup policy (see PDR-005 below)
- Batching strategy (see PDR-006 below)

---

### 6. Fuzzy Search Discussion
**Goal:** Plan how to store and search parsed job data

**Discussion points:**
- How should we structure parsed data for fuzzy search?
- Should we use PostgreSQL full-text search, Elasticsearch, or other?
- What fields should be searchable (title, description, requirements, etc.)?
- Should we store normalized/tokenized versions?

---

## Pending Architecture Decisions (PDRs)

**IMPORTANT:** Review these before starting Phase 2B implementation. See [DECISIONS.md](./architecture/DECISIONS.md#phase-2-pending-decisions) for full details.

### PDR-001: Database Choice
**Question:** PostgreSQL (RDS vs Neon) or DynamoDB?

**Options:**
- PostgreSQL on AWS RDS (~$15-20/month, full SQL)
- Neon (serverless Postgres, generous free tier)
- DynamoDB (serverless NoSQL, unlimited scale)

**Status:** ⏳ To be decided before Task #4
**Impact:** Affects settings storage strategy (PDR-002)

---

### PDR-002: Settings Storage Strategy
**Question:** How to store user settings (companies, filters)?

**Options:**
- Dedicated settings table
- JSON field in users table
- Separate DynamoDB table

**Status:** ⏳ To be decided (depends on PDR-001)
**Impact:** Affects Task #1 implementation

---

### PDR-003: Crawling Rate Limits
**Question:** How to avoid getting blocked by company career pages?

**Options:**
- Fixed delay per company (e.g., 2 seconds)
- Configurable delay in extractor class
- SQS delay/visibility timeout

**Status:** ⏳ To be decided before Task #3
**Impact:** Affects crawl_job() implementation

---

### PDR-004: Error Handling Strategy
**Question:** How to handle crawling/parsing failures?

**Options:**
- SQS Dead Letter Queue (DLQ)
- Custom retry logic with exponential backoff
- Hybrid approach

**Status:** ⏳ To be decided before Task #5
**Impact:** Affects Lambda and SQS configuration

---

### PDR-005: S3 Cleanup Policy
**Question:** How long to keep raw HTML in S3?

**Options:**
- Keep forever (can re-parse, costs grow)
- Delete after successful parsing (minimal cost, no re-parsing)
- S3 Lifecycle Policy (30/60/90 days)

**Recommendation:** Start with 30-day retention
**Status:** ⏳ To be decided before Task #5

---

### PDR-006: JobCrawlerLambda Batching Strategy
**Question:** Process 1 URL or multiple URLs per Lambda invocation?

**Options:**
- 1 URL per invocation (simple, auto-scales)
- Batch 10-50 URLs (fewer cold starts, risk of timeout)

**Recommendation:** Start with 1 URL, optimize later
**Status:** ⏳ To be decided before Task #5

---

### PDR-007: WebSocket Infrastructure
**Question:** How to show real-time crawl status updates?

**Options:**
- API Gateway WebSocket (AWS-native, complex)
- Polling GET /api/crawl-status (simple)
- Server-Sent Events (SSE)

**Recommendation:** Start with polling, add WebSocket later
**Status:** ⏳ Deferred to later in Phase 2B

---

## Notes for Next AI Session

When starting a new session, AI should:
1. Read this file first
2. Review the Next Session Implementation Plan above
3. Ask user which task to start with (1-6)
4. For each task, check if any PDRs need to be resolved first
5. Follow the workflow preferences without re-asking
6. If unclear, ask for clarification once, then add to this file
