# Phase 2F: Stage 3 UI + Run Lifecycle

**Status**: ✅ Complete
**Date**: December 31, 2025
**Goal**: Frontend Stage 3 layout and backend run lifecycle endpoints

---

## Overview

Phase 2F implements the foundational infrastructure for Stage 3 of the ingestion workflow. This includes the database schema, run lifecycle API endpoints, and frontend Stage 3 UI scaffolding.

**Included in this phase**:
- Database: `ingestion_runs` and `jobs` tables
- Backend: `/start`, `/current-run`, `/abort` endpoints
- Backend: `RunStatus` constants for consistent status handling
- Frontend: Stage 3 layout (run ID, abort button, status placeholder)
- Frontend: Stepper consolidation (5 → 3 stages)

**Explicitly excluded** (deferred to Phase 2G):
- Async worker Lambda
- SSE `/progress` endpoint
- Job record creation (UPSERT from dry-run results)
- Mock ingestion simulation

---

## Key Achievements

### 1. Database Schema ✅

**Migration**: `a2ef3e15d65e_jobs.py` - Applied to test and prod databases via `jdbpush`

**ingestion_runs table** - Run metadata + final snapshot:
```sql
CREATE TABLE ingestion_runs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    -- pending, initializing, ingesting, finished, error, aborted
    total_jobs INTEGER DEFAULT 0,
    -- Snapshot fields (written on completion)
    jobs_ready INTEGER,
    jobs_skipped INTEGER,
    jobs_expired INTEGER,
    jobs_failed INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);
```

**jobs table** - Individual job status and data:
```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES ingestion_runs(id) ON DELETE SET NULL,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    company VARCHAR(100) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    -- pending, ready, skipped, expired, error
    title TEXT,
    location TEXT,
    description TEXT,
    requirements TEXT,
    simhash BIGINT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, company, external_id)
);

CREATE INDEX idx_jobs_run_status ON jobs(run_id, status);
```

### 2. RunStatus Constants ✅

Created `RunStatus` class in `backend/models/ingestion_run.py`:

```python
class RunStatus:
    """Ingestion run status constants."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    INGESTING = "ingesting"
    FINISHED = "finished"
    ERROR = "error"
    ABORTED = "aborted"

    # Terminal states - run is no longer active
    TERMINAL = [FINISHED, ERROR, ABORTED]
```

Ensures consistent status checking across all endpoints.

### 3. API Endpoints ✅

**GET `/api/ingestion/current-run`** - Check for active run:
```json
Response: { "run_id": 123 }  // or { "run_id": null }
```

**POST `/api/ingestion/start`** - Start ingestion run:
```json
Response: { "run_id": 123 }
```

**POST `/api/ingestion/abort/{run_id}`** - Abort active run:
```json
Response: { "success": true, "message": "Run 123 aborted" }
```

### 4. Frontend Stage 3 Layout ✅

**Stage3Progress.js** component:
- Header row: Run ID (left) | Abort button (right)
- Compact status row with colored badge
- Details section placeholder for SSE data
- Error banner for abort failures

**CSS**: All classes prefixed with `s3-` per codebase conventions.

### 5. Stepper Consolidation ✅

Updated `IngestPage.js`:
- 5 stages → 3 stages: Configure, Preview, Ingest
- Action bar conditionally rendered (hidden for Stage 3)
- Page refresh detection via `/current-run` endpoint

---

## File Structure

```
backend/
├── models/
│   ├── __init__.py              # Exports IngestionRun, RunStatus
│   └── ingestion_run.py         # SQLAlchemy model + RunStatus constants
├── api/
│   └── ingestion_routes.py      # /start, /current-run, /abort endpoints
└── alembic/versions/
    └── a2ef3e15d65e_jobs.py     # Migration for ingestion_runs + jobs

frontend/src/pages/
├── IngestPage.js                # 3-stage stepper, page refresh detection
└── ingest/
    ├── Stage3Progress.js        # Run ID, abort button, status placeholder
    └── Stage3Progress.css       # s3-* prefixed styles
```

---

## Next Steps → Phase 2G

Phase 2G will add the async worker and SSE:
- Worker Lambda (async invoke from `/start`)
- SSE `/progress/{run_id}` endpoint
- Job UPSERT from dry-run results
- Mock ingestion simulation (1 min delay → all jobs ready)

---

## References

**Internal Documentation**:
- [SYSTEM_DESIGN.md](../architecture/SYSTEM_DESIGN.md) - Pipeline architecture
- [PHASE_2E_SUMMARY.md](./PHASE_2E_SUMMARY.md) - Dry-run implementation
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - API endpoints
