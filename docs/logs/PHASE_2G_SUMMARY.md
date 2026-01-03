# Phase 2G: Worker Lambda

**Status**: 🔧 In Progress
**Date**: January 1, 2026
**Goal**: Async Worker Lambda for job initialization and mock ingestion

---

## Overview

Phase 2G adds the async processing layer between the `/start` endpoint and job management. The API Lambda triggers a Worker Lambda asynchronously, which handles URL sourcing and job record creation.

**Key insight**: Lambda async invoke (`InvocationType='Event'`) returns immediately while the worker runs independently for up to 15 minutes. This avoids API Gateway's 29-second timeout.

**Prerequisite**: Phase 2F must be complete (jobs table schema + run lifecycle endpoints).

**Included in this phase**:
- Worker Lambda (async invoke, 15 min timeout)
- Job UPSERT from dry-run results
- Expired job detection
- Mock ingestion (30s wait → all jobs ready)

**Explicitly excluded** (deferred to Phase 2H):
- SSE `/progress/{run_id}` endpoint
- Frontend SSE connection
- Real-time progress display

---

## Key Achievements

### 1. Worker Lambda
- New Lambda function triggered asynchronously from `/start` endpoint
- 15-minute timeout (vs 29s API Gateway limit)
- Processes jobs independently without blocking API response
- Reference: [AWS Lambda Async Invoke](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html)

### 2. Job UPSERT Logic
- PostgreSQL `ON CONFLICT DO UPDATE` for atomic insert-or-update
- New jobs: Insert with `status='pending'`
- Existing jobs: Update `run_id`, reset status to `'pending'`
- Reference: [PostgreSQL UPSERT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT)

### 3. Expired Job Detection
- Jobs not in current extraction results marked as `'expired'`
- Tracks when jobs are removed from company career pages

---

## Architecture

```
POST /start (API Lambda, <1s)
    ├─> Create ingestion_run (status=pending)
    ├─> lambda.invoke(worker, InvocationType='Event')
    └─> Return {run_id}

Worker Lambda (async, up to 15 min)
    ├─> status = 'initializing'
    ├─> Run extractors, UPSERT jobs
    ├─> Mark expired jobs
    ├─> status = 'ingesting'
    ├─> Mock wait (30s) → all jobs 'ready'
    └─> status = 'finished', write snapshot
```

---

## Highlights

### Worker Lifecycle

Worker receives `{run_id, user_id}` payload and:
1. Updates run status: `pending` → `initializing`
2. Runs extractors (reuses dry-run logic from Phase 2E)
3. UPSERTs job records to DB
4. Marks jobs not in results as expired
5. Updates run status: `initializing` → `ingesting`
6. Mocks ingestion by waiting 30s, then marking all jobs `'ready'`
7. Finalizes run with snapshot counts, status → `finished`

### UPSERT SQL Pattern

```sql
INSERT INTO jobs (user_id, company, external_id, title, url, status, run_id)
VALUES ($1, $2, $3, $4, $5, 'pending', $6)
ON CONFLICT (user_id, company, external_id) DO UPDATE SET
    run_id = EXCLUDED.run_id,
    status = 'pending',
    updated_at = NOW();
```

### Expired Job Detection

After UPSERT, mark jobs not in current results:
```sql
UPDATE jobs SET status = 'expired', updated_at = NOW()
WHERE user_id = $1 AND run_id != $2 AND status != 'expired';
```

---

## Testing & Validation

**Manual Testing**:
- Start ingestion → Verify worker invoked asynchronously
- Check jobs table → Verify UPSERT creates/updates records
- Run twice → Verify existing jobs get updated run_id
- Remove company → Verify jobs marked as expired

**Automated Testing**:
- Future: Worker unit tests
- Future: Integration tests for UPSERT logic

---

## Next Steps → Phase 2H

Phase 2H adds real-time progress display:
- SSE `/progress/{run_id}` endpoint
- Frontend EventSource connection (Stage3Progress)
- Full state + diff update protocol
- Reconnection handling

**Target**: Complete end-to-end progress monitoring

---

## File Structure

```
backend/
├── workers/
│   └── ingestion_worker.py      # Worker Lambda handler
├── api/
│   └── ingestion_routes.py      # Updated /start with async invoke
└── template.yaml                # SAM template with IngestionWorkerFunction
```

**Key Files**:
- [ingestion_worker.py](../../backend/workers/ingestion_worker.py) - Worker Lambda implementation
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - /start endpoint with async invoke

---

## References

**External Documentation**:
- [AWS Lambda Async Invoke](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html) - Async invocation pattern
- [PostgreSQL UPSERT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT) - ON CONFLICT clause

**Internal Documentation**:
- [PHASE_2F_SUMMARY.md](./PHASE_2F_SUMMARY.md) - Run lifecycle endpoints + jobs table
- [PHASE_2H_SUMMARY.md](./PHASE_2H_SUMMARY.md) - SSE + Frontend
