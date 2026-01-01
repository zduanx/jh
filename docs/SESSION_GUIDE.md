# Session Guide - AI Assistant Rules

**Purpose**: Quick reference for AI behavior rules. Read FIRST after context compaction or new session.

---

## About This File

This file is the **single source of truth** for AI assistant rules. When adding new rules:

1. **Find the right section** - Rules are grouped by category (see Table of Contents)
2. **Use consistent format** - Each section uses tables or bullet lists
3. **Keep it scannable** - Brief entries, no long paragraphs
4. **Add to Codebase Conventions** for file structure/naming rules

**Sections**:
- Session Startup → What to do first
- Security Rules → What NOT to do
- Permission Rules → When to ask vs proceed
- Codebase Conventions → File structure, naming, patterns
- Workflow Rules → How to do specific tasks
- Documentation Standards → How to write docs

---

## Session Startup Checklist

### Every Session Start
1. Read this file
2. Load secrets: `backend/.env.local` + `frontend/.env.local` (into memory only)
3. Check status: [PHASE_1_SUMMARY.md](./logs/PHASE_1_SUMMARY.md)

### After Context Compaction
**MANDATORY**: After every context compaction, immediately:
1. Re-read this file (`docs/SESSION_GUIDE.md`)
2. Print confirmation: "Re-read SESSION_GUIDE.md. Rules: [list all ## section headers from this file]"

This prevents context loss and ensures continuity of coding standards (CSS prefixes, test locations, dev.sh commands, etc.).

### Context Needed
- **Architecture**: [SYSTEM_DESIGN.md](./architecture/SYSTEM_DESIGN.md)
- **API Routes**: [API_DESIGN.md](./architecture/API_DESIGN.md)
- **Recent work**: `git log --oneline -10`

---

## Security Rules

### Never Write Secrets To
- Any `docs/**/*.md` file
- Any git-tracked file (except `.env.local` which is gitignored)

### Secrets Live In
| Environment | Location |
|-------------|----------|
| Local dev (test DB) | `backend/.env.local`, `frontend/.env.local` |
| Production frontend | Vercel Dashboard |
| Production backend | AWS Lambda env vars |

### Database URLs
| Source | Target |
|--------|--------|
| `.env.local` | Neon **test branch** |
| Lambda | Neon **production branch** |

---

## Permission Rules

### Always Proceed (No Ask)

| Action | Scope |
|--------|-------|
| `mkdir` | Any directory |
| Create/edit files | `docs/**/*.md` (all docs) |
| Update API docs | `docs/architecture/API_DESIGN.md` when adding endpoints |
| Update existing learning | `docs/learning/*.md` (if content exists) |

### Ask First

| Action | When |
|--------|------|
| New learning content | Creating new `docs/learning/*.md` or adding new concepts |
| Code changes | Any `backend/**/*.py` or `frontend/**/*` |
| Config changes | `.env`, `requirements.txt`, `package.json`, etc. |
| ADR creation | Offer when trade-offs discussed, wait for approval |

---

## Codebase Conventions

### Test Files
| Rule | Pattern |
|------|---------|
| Location | Colocate with code: `<module>/__tests__/test_*.py` |
| Shared fixtures | Root `backend/conftest.py` |
| Discovery | `pytest` finds `__tests__/` automatically |
| Header | Every test file must start with docstring showing how to run it |

**Test file header format**:
```python
"""
Tests for <module_name>.

Run: python3 -m pytest <path/to/test_file.py> -v
"""
```

**Example structure**:
```
backend/
├── auth/__tests__/test_auth.py
├── db/__tests__/test_user_service.py
├── sourcing/__tests__/test_sourcing.py
└── conftest.py
```

### Service Layer Pattern
| Layer | Location | Purpose |
|-------|----------|---------|
| Model | `models/<name>.py` | SQLAlchemy table definition |
| Service | `db/<name>_service.py` | CRUD operations |
| Routes | `api/<name>_routes.py` | HTTP endpoints |

### CSS Naming Convention
**Rule**: All CSS classes must use component-specific prefixes to avoid conflicts.

| Component | Prefix | Example Classes |
|-----------|--------|-----------------|
| Stage1Configure | `s1-` | `s1-layout`, `s1-available-card`, `s1-save-btn` |
| FilterModal | `fm-` | `fm-overlay`, `fm-content`, `fm-header` |
| TokenInput | `token-` | `token-input-container`, `token-input-wrapper` |
| IngestPage | `ingest-` | `ingest-page`, `ingest-stepper` |

**Why**: Generic class names (e.g., `.modal-content`, `.spinner`, `.save-btn`) can be overwritten by other components' CSS, causing unexpected styling issues.

**Format**:
```css
/* ComponentName - All classes prefixed with 'xx-' to avoid conflicts */
.xx-layout { ... }
.xx-header { ... }
```

### Gitignore Comments
**Rule**: Comments in `.gitignore` files must be on their own line. Inline comments do NOT work.

```gitignore
# ✅ Correct - comment on separate line
# This file contains secrets
samconfig.toml

# ❌ Wrong - inline comments are treated as part of the pattern
samconfig.toml  # This file contains secrets
```

---

## Workflow Rules

### dev.sh Automation
**Always use dev.sh commands** instead of manual commands.

| Task | Command | Don't Do |
|------|---------|----------|
| Create migration | `jdbcreate <name>` | `alembic revision ...` |
| Apply migrations | `jdbpush` | `alembic upgrade head` manually |
| Check migration status | `jdbstatus` | `alembic current` manually |
| Deploy backend | `jpushapi` | `sam build && sam deploy` |
| Deploy frontend | `jpushvercel` | `git push` + manual Vercel |
| Check env vars | `jenvcheck` | Manual AWS/Vercel console |
| Start services | `jbe-bg && jfe-bg` | Manual uvicorn/npm |

**Propose new commands** when you notice repetitive multi-step tasks.

### Before Editing Extractors
1. **Check `trials/{company}/`** for API response snapshots
2. Understand actual API structure (avoid assumptions)
3. Common quirks: Amazon dual IDs, TikTok nested locations, Anthropic office field

### Learning Content
| Action | Rule |
|--------|------|
| Update existing | Proceed |
| New content | Suggest first, wait for approval |
| New file | Ask "Should I create `docs/learning/topic.md`?" |

### When Adding API Endpoints
1. Implement endpoint code (with permission)
2. **MANDATORY: Update** [API_DESIGN.md](./architecture/API_DESIGN.md) immediately after implementation
3. Include: endpoint, method, auth requirement, request body, response examples, error cases

**API_DESIGN.md format**:
```markdown
### N. Endpoint Name

**Endpoint:** `METHOD /path`
**Authentication:** Required (JWT) | Not required

**Request Body:** (if applicable)
```json
{ ... }
```

**Success Response:** `200 OK`
```json
{ ... }
```

**Error Response:** `4XX` (description)
```json
{ "detail": "..." }
```
```

### When Trade-offs Discussed
**Offer ADR**: "This involves trade-offs. Should I create an ADR?"
- Offer when: multiple approaches, architectural decisions, future-questioning choices
- Don't offer when: obvious details, established patterns, quick tactical changes

---

## Documentation Standards

### Phase Summary
**File**: `docs/logs/PHASE_X_SUMMARY.md`
**Template**: [PHASE_SUMMARY_TEMPLATE.md](./PHASE_SUMMARY_TEMPLATE.md)

**Structure** (13 sections):
1. Header (Status, Date, Goal)
2. Overview (scope: included/excluded)
3. Key Achievements (inline refs to ADRs/learning/deployment)
4. Database Schema (if applicable)
5. API Endpoints (if applicable)
6. Highlights (technical details)
7. Testing & Validation (manual vs automated)
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

### Dates in Documentation
**Rule**: Always use the **actual current date** when writing dates in docs (ADRs, phase summaries, learning files).

| Action | Do | Don't |
|--------|-----|-------|
| Writing ADR date | Check system date, use real date | Guess or use training data dates |
| Phase summary date | Use today's date | Copy dates from previous docs |

**How to verify**: The current date is provided in the system context at session start.

---

## Quick Reference

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
