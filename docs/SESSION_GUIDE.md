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

**Current Phase**: Phase 1 Complete ✅
**Last Session**: 2024-12-14
**Next Steps**: Begin Phase 2 (Web Scraping & Database)

### What's Working
- ✅ Google OAuth authentication
- ✅ JWT token generation and validation
- ✅ Email whitelist access control
- ✅ AWS Lambda + API Gateway deployment
- ✅ Vercel frontend deployment
- ✅ CORS configured (localhost + production)
- ✅ HTTPS on both frontend and backend

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

## Notes for Next AI Session

When starting a new session, AI should:
1. Read this file first
2. Follow these preferences without re-asking
3. If unclear, ask for clarification once, then add to this file
