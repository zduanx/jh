# Session Guide - AI Assistant Rules

**Purpose**: Quick reference for AI behavior rules. Read FIRST after context compaction or new session.

---

## Session Startup Checklist

### Every Session Start
1. ✅ Read this file
2. ✅ Load secrets: `backend/.env.local` + `frontend/.env.local` (into memory only)
3. ✅ Check status: [PHASE_1_SUMMARY.md](./logs/PHASE_1_SUMMARY.md)

### Context Needed
- **Architecture**: [SYSTEM_DESIGN.md](./architecture/SYSTEM_DESIGN.md)
- **API Routes**: [API_DESIGN.md](./architecture/API_DESIGN.md)
- **Recent work**: `git log --oneline -10`

---

## 🔒 Security Rules

### Never Write Secrets To
- Any `docs/**/*.md` file
- Any git-tracked file (except `.env.local` which is gitignored)

### Secrets Live In
- `backend/.env.local` (local dev - TEST database)
- `frontend/.env.local` (local dev)
- Vercel Dashboard (production frontend)
- AWS Lambda env vars (production backend)

### Database URLs
- `.env.local` → Neon **test branch** (for local development)
- Lambda → Neon **production branch** (for deployed backend)

---

## Permission Rules

### ✅ Always Proceed (No Ask)

| Action | Scope |
|--------|-------|
| `mkdir` | Any directory |
| Create/edit files | `docs/**/*.md` (all docs) |
| Update API docs | `docs/architecture/API_DESIGN.md` when adding endpoints |
| Update existing learning | `docs/learning/*.md` (if content exists) |

### ⚠️ Ask First

| Action | When |
|--------|------|
| New learning content | Creating new `docs/learning/*.md` or adding new concepts |
| Code changes | Any `backend/**/*.py` or `frontend/**/*` |
| Config changes | `.env`, `requirements.txt`, `package.json`, etc. |
| ADR creation | Offer when trade-offs discussed, wait for approval |

---

## Automatic Actions

### When Adding API Endpoints
1. Implement endpoint code (with permission)
2. **Automatically update** [API_DESIGN.md](./architecture/API_DESIGN.md)
3. Include: route, method, purpose, request/response, auth

### When Trade-offs Discussed
**Offer ADR**: "This involves trade-offs. Should I create an ADR?"
- Offer when: multiple approaches, architectural decisions, future-questioning choices
- Don't offer when: obvious details, established patterns, quick tactical changes

---

## Workflow-Specific Rules

### Before Editing `backend/extractors/`
1. **Check `trials/{company}/`** for API response snapshots
2. Understand actual API structure (avoid assumptions)
3. Common quirks: Amazon dual IDs, TikTok nested locations, Anthropic office field

### Learning Content
- **Updating existing**: Proceed
- **New content**: Suggest first, wait for approval
- **New file**: Ask "Should I create `docs/learning/topic.md`?"

---

## Phase Summary Standard

**File**: `docs/logs/PHASE_X_SUMMARY.md`

**Template**: [PHASE_SUMMARY_TEMPLATE.md](./PHASE_SUMMARY_TEMPLATE.md)

**Structure** (13 sections):
1. Header (Status, Date, Goal)
2. Overview (scope: included/excluded)
3. Key Achievements (inline refs to ADRs/learning/deployment)
4. Database Schema (if applicable)
5. API Endpoints (if applicable)
6. Highlights (technical details)
7. Testing & Validation (manual vs automated, ✅ for completed)
8. Metrics
9. Next Steps
10. File Structure
11. Key Learnings (brief, link to `docs/learning/*`)
12. References (external URLs only)
13. Status footer

**Principles**:
- No item limits, keep each item 1-3 bullets
- Inline refs for internal docs, end section for external URLs
- Sequential phases (no Dependencies section)

---

## Quick Reference Table

| If User Says... | AI Should... |
|----------------|--------------|
| "Add POST /api/users endpoint" | 1) Ask to implement code, 2) Auto-update API_DESIGN.md |
| "Should we use X or Y?" | Discuss, then offer ADR if trade-offs exist |
| "What's the difference between X and Y?" | Explain, then suggest adding to learning docs |
| "Update extractor for Company Z" | Check `trials/company-z/` for API snapshots first |
| "Write phase summary" | Use template, follow 13-section structure |

---

## Project References

- **Phase status**: [logs/PHASE_1_SUMMARY.md](./logs/PHASE_1_SUMMARY.md)
- **Architecture**: [architecture/SYSTEM_DESIGN.md](./architecture/SYSTEM_DESIGN.md)
- **API routes**: [architecture/API_DESIGN.md](./architecture/API_DESIGN.md)
- **Decisions**: [architecture/DECISIONS.md](./architecture/DECISIONS.md)
- **Deployment**: [deployment/](./deployment/) folder
- **Learning**: [learning/](./learning/) folder
