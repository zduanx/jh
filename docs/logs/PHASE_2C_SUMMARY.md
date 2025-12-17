# Phase 2C: Ingestion Workflow + Deployment Automation

**Status**: 🚧 In Progress
**Date**: Started December 2024
**Goal**: Design and implement the 5-stage ingestion workflow UI with company configuration, persistence, and automated deployment system

---

## Overview

Phase 2C establishes the ingestion workflow infrastructure with a 5-stage horizontal stepper UI, user company settings table, and Stage 1 company configuration interface.

**Included in this phase**:
- 5-stage horizontal stepper UI component
- User company settings table and CRUD endpoints
- Stage 1: Company configuration interface (frontend + backend)
- Workflow state management
- Multi-stage navigation logic
- Automated AWS SAM deployment system with config generation

**Explicitly excluded** (deferred to later phases):
- Dry run execution (Phase 2D)
- Ingestion runs table/persistence (Phase 2E)
- Job archiving (Phase 2E)
- Actual crawling (Phase 2E)

---

## Key Achievements

### 1. Automated Deployment System ✅
- **Python scripts**: Auto-generate `template.yaml` and `samconfig.toml` from configuration sources
  - [generate_template.py](../../backend/scripts/generate_template.py) - Generates CloudFormation template from `.sam-config` + `.env.local` metadata
  - [generate_samconfig.py](../../backend/scripts/generate_samconfig.py) - Generates SAM config from `.sam-config` + `.env.local` PROD_VALUE comments
- **Configuration files**:
  - [.sam-config](../../backend/.sam-config) - Deployment metadata (stack name, Lambda settings, static env vars) - **committed to git**
  - [.env.local](../../backend/.env.local) - Environment variables with PROD_VALUE comments and CloudFormation parameter metadata - **gitignored**
- **Deployment workflow** (`jpushapi` in [dev.sh](../../dev.sh)):
  1. Check git status (require clean state or commit)
  2. Compare Lambda env vars with local config
  3. Generate configs with change detection (exit codes: 0=no change, 1=modified, 2=new)
  4. Show changes and ask for confirmation
  5. Auto-commit with standard message
  6. SAM build and deploy
  7. Verify deployment
- **Benefits**: No manual YAML editing, consistent deployments, secrets never in git, parameter descriptions in source

### 2. Five-Stage Workflow Architecture
- **Stage 1: Configure** - Select companies and set title filters (this phase)
- **Stage 2: Preview** - Dry run URL extraction (Phase 2D)
- **Stage 3: Archive** - Remove outdated jobs (Phase 2E)
- **Stage 4: Ingest** - Crawl and parse jobs (Phase 2E)
- **Stage 5: Results** - Summary and history (Phase 2E)

### 2. Horizontal Stepper UI Component
- **Visual progress**: 5 circles connected by horizontal lines
- **State indicators**: Active (blue), completed (green + checkmark), locked (gray)
- **Non-clickable**: Navigation via buttons only (enforces linear workflow)
- **Responsive**: Collapses to vertical on mobile

### 3. User Company Settings Table
- **Storage**: PostgreSQL with JSONB for title filters
- **Unique constraint**: One configuration per company per user
- **Cascade deletion**: Cleanup when user deleted
- **Indexed**: Fast lookups by user_id

### 4. Stage 1 Company Configuration UI
- **Company cards**: Display logo, name, URL, active filters
- **Configuration modal**: Edit career page URL and title filters
- **Multi-input**: Add keywords by typing + Enter, remove by clicking X
- **Validation**: At least one company required to proceed

### 5. Backend CRUD Endpoints
- **GET `/api/ingestion/settings`**: Fetch user's company configurations
- **POST `/api/ingestion/settings`**: Create/update company setting
- **DELETE `/api/ingestion/settings/:setting_id`**: Remove company

---

## Database Schema

**user_company_settings table**:
- `setting_id`: Integer primary key (auto-increment)
- `user_id`: Foreign key to users table, indexed
- `company_name`: VARCHAR(255), company identifier
- `career_page_url`: TEXT, URL to company career page
- `title_filters`: JSONB array of keywords (e.g., `["software", "engineer"]`)
- `created_at`, `updated_at`: TIMESTAMP WITH TIMEZONE
- **Unique constraint**: `(user_id, company_name)`
- **ON DELETE CASCADE**: Cleanup when user deleted

**Design rationale**:
- JSONB for flexible filter storage (no schema changes for new filter types)
- Unique constraint prevents duplicate company entries per user
- Index on `user_id` for fast lookups
- Normalized schema (easier to query than JSONB in users table)

---

## API Endpoints

**GET `/api/ingestion/settings`**:
- Purpose: Fetch user's configured company settings
- Request: Headers with `Authorization: Bearer <jwt>`
- Response: Array of company settings `[{ setting_id, company_name, career_page_url, title_filters }]`
- Auth: JWT required

**POST `/api/ingestion/settings`**:
- Purpose: Create or update company setting
- Request: `{ company_name, career_page_url, title_filters: [string] }`
- Response: Created/updated setting object
- Validation: Unique constraint check `(user_id, company_name)`
- Auth: JWT required

**DELETE `/api/ingestion/settings/:setting_id`**:
- Purpose: Remove company setting
- Request: Path parameter `setting_id`
- Response: Success message
- Validation: Verify ownership (user_id match)
- Auth: JWT required

---

## Highlights

### Workflow State Management
**Key state variables**: `currentStage` (1-5), `configuredCompanies` (array), `isLoading`, `error`

**Persistence**: Fetch from database on mount, update local state after save operations, validate before stage transitions

**Navigation logic**: Stage 1 → 2 requires ≥1 company configured, "Next" button enabled/disabled based on validation

### Company Configuration Flow
User clicks "Configure" → Modal opens with pre-filled data → User edits URL/filters → Clicks "Save" → API call → Local state update → UI refresh

**Validation**: Career page URL must be valid HTTP(S), title filters optional (empty = all jobs)

### Why JSONB for Filters?
**Alternative**: Separate title_filters table with many-to-many relationship

**Chosen**: JSONB array in settings table

**Rationale**: Filters are user-specific (not shared), no need to query filters independently, simpler schema, easy to extend with new filter types

### Why Non-Clickable Stepper?
**Alternative**: Allow clicking on stepper circles to jump stages

**Chosen**: Navigation via buttons only

**Rationale**: Enforces linear workflow (prevents skipping validation), stages have dependencies (can't jump to Stage 4 without Stage 2 data), simpler state management

---

## Testing & Validation

**Manual Testing**:
- Add company → Save → Verify in database
- Edit company → Update filters → Verify changes
- Remove company → Confirm deletion
- Add duplicate → Verify unique constraint error
- Stage 1 with 0 companies → Next button disabled
- Stage 1 with 1+ companies → Next button enabled
- Stage 2 → Back → Returns to Stage 1 with data intact

**Automated Testing**:
- Future: Component tests for stepper, cards, modals
- Future: Integration tests for CRUD endpoints
- Future: End-to-end test for full Stage 1 flow

---

## Metrics

- **UI Components**: 7 (stepper, 5 stages, card, modal)
- **Database Tables**: 1 (user_company_settings)
- **API Endpoints**: 3 (GET, POST, DELETE settings)
- **Lines of Code**: ~800 (frontend + backend)
- **Target Completion**: Stage 1 fully functional with persistence

---

## Next Steps → Phase 2D

Phase 2D will implement **Dry Run (Stage 2)**:
- Integrate with Phase 2A extractors
- Backend endpoint to trigger URL extraction
- Frontend display of extracted URLs
- Validation before ingestion commitment
- Job count summary per company

**Target**: Complete Stage 2 with full URL preview functionality

---

## File Structure

```
backend/
├── scripts/
│   ├── generate_template.py    # Auto-generate template.yaml
│   └── generate_samconfig.py   # Auto-generate samconfig.toml
├── .sam-config                 # Deployment metadata (committed)
├── .env.local                  # Env vars with metadata (gitignored)
├── samconfig.toml.example      # Example config structure
├── models/
│   └── user_company_settings.py # SQLAlchemy model
├── db/
│   └── ingestion_service.py    # Settings CRUD operations
├── api/
│   └── ingestion_routes.py     # REST endpoints
└── alembic/versions/
    └── xxx_create_user_company_settings.py  # Migration

frontend/src/pages/Ingest/
├── IngestPage.js               # Main container
├── HorizontalStepper.js        # Stepper component
├── Stage1_Configure.js         # Company selection
├── Stage2_Preview.js           # Placeholder (Phase 2D)
├── Stage3_Archive.js           # Placeholder (Phase 2E)
├── Stage4_Ingest.js            # Placeholder (Phase 2E)
├── Stage5_Results.js           # Placeholder (Phase 2E)
├── CompanyCard.js              # Company card component
├── ConfigModal.js              # Configuration modal
└── IngestPage.css              # Styles

dev.sh                          # jpushapi deployment workflow
```

**Key Files**:
- [generate_template.py](../../backend/scripts/generate_template.py) - CloudFormation template generator
- [generate_samconfig.py](../../backend/scripts/generate_samconfig.py) - SAM config generator
- [.sam-config](../../backend/.sam-config) - Deployment metadata
- [dev.sh](../../dev.sh) - jpushapi deployment workflow (lines 635+)
- [user_company_settings.py](../../backend/models/user_company_settings.py) - SQLAlchemy model
- [ingestion_service.py](../../backend/db/ingestion_service.py) - CRUD operations
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - API endpoints
- [IngestPage.js](../../frontend/src/pages/Ingest/IngestPage.js) - Main container
- [HorizontalStepper.js](../../frontend/src/pages/Ingest/HorizontalStepper.js) - Stepper component

---

## Key Learnings

### Deployment Configuration as Code
**Challenge**: Manual YAML editing error-prone, secrets scattered across files, hard to track what's deployed vs what's configured.

**Solution**: Single source of truth (`.sam-config` + `.env.local`) → Python generates deployment files → Git tracks metadata, not secrets.

**Key insight**: Separation of concerns - deployment metadata (committed) vs environment values (gitignored) allows team collaboration without exposing secrets.

### String Comparison for Change Detection
**Challenge**: `git diff` doesn't work for gitignored files (samconfig.toml), but we need to know if configs changed.

**Solution**: Python scripts compare existing file content vs newly generated content, return exit codes (0=no change, 1=modified, 2=new file).

**Benefit**: Clean change detection without relying on git, works for both tracked and untracked files.

### Horizontal Stepper UX
Clear progress visualization reduces anxiety about multi-step processes. User always knows where they are and path forward.

### JSONB vs Separate Table
JSONB offers flexibility but requires validation in application layer. Use Pydantic models to validate JSONB structure before saving.

### State Management Complexity
Challenge: Keeping frontend state synced with database. Solution: Fetch fresh data on mount, optimistic updates with rollback on error.

---

## References

**External Documentation**:
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html) - JSON data types
- [React State Management](https://react.dev/learn/managing-state) - State patterns

---

**Status**: Ready for Phase 2D
