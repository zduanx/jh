# Phase 2G: Worker Lambda

**Status**: ✅ Completed
**Date**: January 1-3, 2026
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
- Test database switching for local development
- Structured log prefixes for CloudWatch filtering
- CloudWatch logs streaming endpoint
- Stage 3 real-time log viewer UI
- Stage 4 summary UI with completion stepper

**Explicitly excluded** (deferred to Phase 2H):
- SSE `/progress/{run_id}` endpoint for run status
- Frontend SSE connection for progress updates

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

### 4. Test Database for Local Development
- `use_test_db` flag in worker payload switches between prod/test databases
- Local backend (`jbe`) passes `use_test_db=true` when invoking AWS worker
- Worker uses `TEST_DATABASE_URL` environment variable when flag is set
- Avoids mixing local dev data with production data

### 5. Structured Logging for CloudWatch
- All worker logs use prefix `[IngestionWorker:run_id=X]`
- Enables CloudWatch FilterLogEvents pattern matching
- Frontend can stream logs filtered by specific run_id

### 6. CloudWatch Logs Streaming Endpoint
- `GET /api/ingestion/logs/{run_id}` endpoint
- Uses CloudWatch FilterLogEvents API (free tier: 1M requests/month)
- Supports incremental fetching with `start_time` parameter

### 7. Stage 3 Log Viewer UI
- Real-time CloudWatch log display with 3-second polling
- Dark terminal-style UI with monospace font
- Auto-scrolls to latest logs, stops polling on terminal state

### 8. Stage 4 Summary UI
- Added Stage 4 "Summary" to stepper for terminal states
- Summary banner with status-specific styling (success/error/aborted)
- "Start New Run" button to reset workflow
- All stepper stages show green checkmarks on completion

---

## API Endpoints

**GET `/api/ingestion/logs/{run_id}`**
- Purpose: Stream CloudWatch logs for a specific run
- Query params: `token` (JWT), `start_time` (optional, ms since epoch)
- Response: `{ logs: [{ timestamp, message }], next_token }`
- Auth: JWT required via query param (for EventSource compatibility)

---

## Highlights

### Worker Lifecycle

Worker receives `{run_id, user_id, use_test_db}` payload and:
1. Selects database based on `use_test_db` flag
2. Updates run status: `pending` → `initializing`
3. Runs extractors (reuses dry-run logic from Phase 2E)
4. UPSERTs job records to DB
5. Marks jobs not in results as expired
6. Updates run status: `initializing` → `ingesting`
7. Mocks ingestion (30s wait), marks all jobs `'ready'`
8. Finalizes run with snapshot counts, status → `finished`

### Local Dev → AWS Worker Flow

When running locally (`jbe`), the API detects it's not in Lambda (via `AWS_LAMBDA_FUNCTION_NAME` env var) and passes `use_test_db=true` to the worker. The worker then uses `TEST_DATABASE_URL` instead of `DATABASE_URL`, keeping local dev data separate from production.

### CloudWatch Log Filtering

FilterLogEvents uses pattern `"[IngestionWorker:run_id=X]"` to match logs for a specific run. Much cheaper than Live Tail ($0.01/min) - FilterLogEvents is in free tier (1M requests/month).

---

## Testing & Validation

**Manual Testing**:
- ✅ Start ingestion → Verify worker invoked asynchronously
- ✅ Check jobs table → Verify UPSERT creates/updates records
- ✅ Run twice → Verify existing jobs get updated run_id
- ✅ Remove company → Verify jobs marked as expired
- ✅ Local `jbe` → Verify worker uses test database
- ✅ CloudWatch logs → Verify structured prefix filtering works
- ✅ Stage 3 UI → Verify logs display in real-time
- ✅ Stage 4 UI → Verify summary banner and stepper completion

**Automated Testing**:
- ✅ 13 worker unit tests passing
- Tests cover: initialization phase, ingestion phase, abort handling, error cases

---

## Metrics

- **Lambda functions**: 2 (API + Worker)
- **API endpoints added**: 1 (`/logs/{run_id}`)
- **Worker timeout**: 15 minutes
- **Unit tests**: 13 passing
- **Log poll interval**: 3 seconds

---

## Next Steps → Phase 2H

Phase 2H adds real-time progress display via SSE:

**Key Features**:
- SSE `/progress/{run_id}` endpoint
- Frontend EventSource connection (Stage3Progress)
- Full state + diff update protocol
- Reconnection handling

**Target**: Complete end-to-end progress monitoring with live status updates

---

## File Structure

```
backend/
├── workers/
│   └── ingestion_worker.py      # Worker Lambda handler
├── api/
│   └── ingestion_routes.py      # /start + /logs endpoints
├── db/
│   └── session.py               # Test database session factory
├── .env.local                   # WORKER_FUNCTION_NAME config
└── template.yaml                # SAM template with worker

frontend/src/pages/ingest/
├── Stage3Progress.js            # Log viewer component
└── Stage3Progress.css           # Terminal-style display
```

**Key Files**:
- [ingestion_worker.py](../../backend/workers/ingestion_worker.py) - Worker Lambda with structured logging
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - /start with async invoke + /logs endpoint
- [Stage3Progress.js](../../frontend/src/pages/ingest/Stage3Progress.js) - Log viewer component

---

## Key Learnings

### Lambda Async Invoke
`InvocationType='Event'` returns 202 immediately while Lambda runs async. No response body - must poll for results or use SSE.

### CloudWatch FilterLogEvents
Pattern matching with quoted strings. Free tier includes 1M requests/month - much cheaper than Live Tail.

### Environment Detection
`AWS_LAMBDA_FUNCTION_NAME` env var exists only in Lambda runtime. Use to detect local vs deployed.

---

## References

**External Documentation**:
- [AWS Lambda Async Invoke](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html) - Async invocation pattern
- [PostgreSQL UPSERT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT) - ON CONFLICT clause
- [CloudWatch FilterLogEvents](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_FilterLogEvents.html) - Log filtering API

**Internal Documentation**:
- [PHASE_2F_SUMMARY.md](./PHASE_2F_SUMMARY.md) - Run lifecycle endpoints + jobs table
- [PHASE_2H_SUMMARY.md](./PHASE_2H_SUMMARY.md) - SSE + Frontend progress
