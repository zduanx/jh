# Phase 2D: Ingestion Stage 1 (Configure)

**Status**: ✅ Completed
**Date**: December 18, 2025
**Goal**: Build Stage 1 of ingestion workflow - company selection with title filters, 5-stage stepper skeleton

---

## Overview

Phase 2D implements Stage 1 of the 5-stage ingestion workflow, allowing users to select companies and configure title filters before running job extraction.

**Included in this phase**:
- 5-stage horizontal stepper UI (skeleton with Stage 1 functional)
- `user_company_settings` database table
- Backend endpoints: companies list, settings CRUD with batch operations
- Frontend: two-column layout, company cards, filter configuration modal
- Local state management with snapshot comparison
- CSS naming convention (component prefixes)
- Performance optimizations (batch API, stable callbacks)

**Explicitly excluded** (deferred to Phase 2E):
- Dry run execution (Stage 2)
- URL extraction preview
- Extractor integration for preview

---

## Key Achievements

### 1. Database Schema
- **Migration**: `87f2af0cf6df_user_company_settings.py` applied to test + prod
- **Table**: `user_company_settings` with JSONB `title_filters`
- **Constraints**: Unique `(user_id, company_name)`, cascade delete on user
- **Index**: `ix_user_company_settings_user_id` for fast lookups

### 2. Backend Service Layer
- **Model**: `models/user_company_settings.py` - SQLAlchemy definition
- **Service**: `db/company_settings_service.py` - CRUD + batch operations
- **Validation**: `TitleFilters` dataclass with `from_dict()` / `to_dict()`
- **Tests**: `db/__tests__/test_company_settings_service.py`

### 3. Backend API Endpoints
- **GET `/api/ingestion/companies`**: List available companies (public)
- **GET `/api/ingestion/settings`**: Fetch user's settings (auth required)
- **POST `/api/ingestion/settings`**: Batch operations with explicit `op` field
- **Pydantic models**: `SettingOperation`, `OperationResult`, `CompanySettingResponse`

### 4. Frontend Stage 1 UI
- **IngestPage.js**: Main container with 5-stage stepper, DB mode indicator
- **Stage1Configure.js**: Two-column layout (available | selected companies)
- **FilterModal.js**: Modal for editing include/exclude filters
- **TokenInput.js**: Reusable keyword input with Enter-to-add, X-to-remove

### 5. State Management
- **Snapshot comparison**: Track original state, compute dirty/new/modified per item
- **Local-first editing**: All changes local until explicit Save
- **Frontend merge**: Response merged into local state (no refetch needed)

### 6. CSS Architecture
- **Prefix convention**: `s1-` (Stage1), `fm-` (FilterModal), `token-` (TokenInput)
- **Added to SESSION_GUIDE.md**: Rule for all new components
- **Responsive**: Grid layouts adapt to screen size

### 7. Performance Optimizations
- **Batch API**: Single POST with array of operations (not N separate calls)
- **Operation results**: Backend returns `{success, id, updated_at}` per operation
- **UserContext fix**: `useRef` pattern prevents `/api/user` refetch on navigation
- **No extra GET**: Frontend merges response directly into state

---

## Database Schema

**user_company_settings table** (migration: `87f2af0cf6df`):
```sql
CREATE TABLE user_company_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    company_name VARCHAR(100) NOT NULL,
    title_filters JSONB DEFAULT '{}' NOT NULL,
    is_enabled BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_user_company UNIQUE(user_id, company_name)
);
CREATE INDEX ix_user_company_settings_user_id ON user_company_settings(user_id);
```

**title_filters JSONB structure**:
```json
{"include": ["engineer", "developer"], "exclude": ["intern", "staff"]}
```
- `include`: null = all jobs, list = OR match any term
- `exclude`: list of terms to reject (AND logic)

---

## API Endpoints

### GET `/api/ingestion/companies`
- **Purpose**: List available companies from extractor registry
- **Auth**: None (public)
- **Response**: `[{ name, display_name, logo_url }]`

### GET `/api/ingestion/settings`
- **Purpose**: Fetch user's configured company settings
- **Auth**: JWT required
- **Response**: `[{ id, company_name, title_filters, is_enabled, updated_at }]`

### POST `/api/ingestion/settings`
- **Purpose**: Batch create/update/delete operations
- **Auth**: JWT required
- **Request**:
```json
[
  {"op": "upsert", "company_name": "google", "title_filters": {"include": ["engineer"]}, "is_enabled": true},
  {"op": "delete", "company_name": "netflix"}
]
```
- **Response**:
```json
[
  {"op": "upsert", "success": true, "company_name": "google", "id": 1, "updated_at": "2025-12-18T..."},
  {"op": "delete", "success": true, "company_name": "netflix"}
]
```

---

## Highlights

### Batch API Design
**Problem**: Frontend making N API calls for N changes (inefficient, race conditions)

**Solution**: Single POST endpoint accepting array of operations with explicit `op` field

**Why not full sync?**: Would require full DB query on every save. Operation-result pattern confirms each change without refetch.

**Industry patterns referenced**: Elasticsearch Bulk API, GraphQL mutations

### CSS Prefix Convention
**Problem**: Generic class names (`.modal`, `.spinner`) conflicting between components

**Solution**: Component-specific prefixes (`s1-`, `fm-`, `token-`)

**Rule added to SESSION_GUIDE.md**: All new components must use prefixes

### UserContext Stability
**Problem**: `/api/user` called on every navigation (useCallback recreated when navigate changes)

**Solution**: Store navigate in `useRef`, use `navigateRef.current()` in callback

**Pattern**: Industry-standard React pattern for stable callbacks with changing dependencies

### Snapshot Comparison
**Problem**: Need to track which items are new/modified/deleted for efficient saves

**Solution**: Store original snapshot on load, compare current state to compute deltas

**Benefits**: Visual indicators (New/Modified badges), only send changed items to API

---

## Testing & Validation

**Manual Testing**:
- Add company from available list -> appears in selected with "New" badge
- Edit filters -> "Modified" badge appears
- Toggle enabled -> "Modified" badge appears
- Remove company -> disappears, available again in left column
- Save -> badges clear, timestamps update
- Cancel -> reverts all local changes
- Page refresh -> settings persist from database

**Automated Testing**:
- `pytest backend/db/__tests__/test_company_settings_service.py`
- Tests: CRUD operations, batch upsert/delete, filter validation

---

## Metrics

| Metric | Count |
|--------|-------|
| Database Tables | 1 (user_company_settings) |
| API Endpoints | 3 (companies, GET settings, POST batch) |
| Frontend Components | 5 (IngestPage, Stage1Configure, FilterModal, TokenInput, CSS files) |
| Lines of CSS | ~550 (Stage1Configure.css) |
| Test Coverage | Service layer unit tests |

---

## Next Steps -> Phase 2E

Phase 2E will implement **Stage 2: Preview**:
- Integrate with Phase 2A extractors
- Backend endpoint to trigger URL extraction (dry run)
- Frontend display of extracted URLs with filtering results
- Validation before proceeding to Archive stage

---

## File Structure

```
backend/
├── models/
│   └── user_company_settings.py      # SQLAlchemy model
├── db/
│   ├── company_settings_service.py   # CRUD + batch operations
│   └── __tests__/
│       └── test_company_settings_service.py
├── api/
│   └── ingestion_routes.py           # REST endpoints
└── alembic/versions/
    └── 87f2af0cf6df_user_company_settings.py

frontend/src/
├── context/
│   └── UserContext.js                # Fixed useRef pattern
├── pages/
│   ├── IngestPage.js                 # Main container + stepper
│   ├── IngestPage.css
│   └── ingest/
│       ├── Stage1Configure.js        # Two-column layout
│       ├── Stage1Configure.css       # s1- prefixed styles
│       └── components/
│           ├── FilterModal.js
│           ├── FilterModal.css       # fm- prefixed styles
│           ├── TokenInput.js
│           └── TokenInput.css        # token- prefixed styles
```

---

## Key Learnings

### Batch Operation Pattern
Use explicit `op` field in request array, return per-operation results. Avoids N+1 API calls and provides clear success/failure feedback per item.

### React Callback Stability
When callbacks depend on values that change frequently (like router navigate), use `useRef` to store the value and access via `.current` in the callback. Keeps callback reference stable.

### CSS Isolation
Always prefix component CSS classes. Generic names will eventually conflict as the app grows. Establish the convention early.

---

## References

**External Documentation**:
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [SQLAlchemy Upsert](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert)
- [Elasticsearch Bulk API](https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-bulk.html) - batch operation pattern
