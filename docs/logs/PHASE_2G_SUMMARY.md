# Phase 2G: Async Worker Lambda + SSE Progress

**Status**: 📋 Planning
**Date**: TBD
**Goal**: Async Lambda worker for job initialization + SSE endpoint for real-time progress

---

## Overview

Phase 2G adds the async processing layer between the `/start` endpoint and real-time progress display. The API Lambda triggers a worker Lambda asynchronously, which handles URL sourcing and job record creation. An SSE endpoint provides real-time progress updates to the frontend.

**Key insight**: Lambda async invoke (`InvocationType='Event'`) returns immediately while the worker runs independently for up to 15 minutes. This avoids API Gateway's 29-second timeout.

**Included in this phase**:
- Worker Lambda (async invoke, 15 min timeout)
- Job UPSERT from dry-run results
- Expired job detection
- SSE `/progress/{run_id}` endpoint
- Mock ingestion (1 min wait → all jobs ready)
- Frontend SSE connection

**Explicitly excluded** (deferred to Phase 2H):
- Real job crawling (just mock status updates)
- SQS queues
- S3 storage for raw HTML
- SimHash deduplication

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
    ├─> Mock wait (1 min) → all jobs 'ready'
    └─> status = 'finished', write snapshot

GET /progress/{run_id} (SSE)
    └─> Poll jobs table every 3s
    └─> Emit counts until terminal status
```

---

## Key Components

### 1. Worker Lambda

New Lambda function in SAM template:
- **Trigger**: Async invoke from API Lambda (no API Gateway event)
- **Timeout**: 15 minutes (vs 29s for API endpoints)
- **Permissions**: DB access, no public endpoint

Worker receives `{run_id, user_id}` and:
1. Updates run status through lifecycle
2. Runs extractors (reuses dry-run logic)
3. UPSERTs job records to DB
4. Marks jobs not in results as expired
5. Mocks ingestion by waiting, then marking all ready
6. Finalizes run with snapshot counts

### 2. Updated /start Endpoint

Add async invoke after creating run record:
- Get worker function name from env var
- Call `lambda.invoke()` with `InvocationType='Event'`
- Return immediately with run_id

### 3. SSE Progress Endpoint

`GET /progress/{run_id}`:
- Returns `text/event-stream`
- Polls job counts every 3 seconds
- Emits `progress` events with status + counts
- Emits `complete` event when run reaches terminal status
- Handles API Gateway's 29s limit via client reconnection

### 4. Job UPSERT Logic

PostgreSQL `ON CONFLICT DO UPDATE`:
- New jobs: Insert with status='pending'
- Existing jobs: Update run_id, reset status to 'pending'
- Jobs not in results: Mark as 'expired'

### 5. Frontend SSE Connection

EventSource in Stage3Progress:
- Connect to `/progress/{run_id}`
- Update status badge and counts on each event
- Handle reconnection on disconnect
- Navigate to results on completion

---

## Infrastructure Changes

**SAM template additions**:
- `IngestionWorkerFunction` - New Lambda (15 min timeout)
- IAM policy for API Lambda to invoke worker
- Environment variable for worker function name

**No new AWS resources** (queues, S3 added in Phase 2H)

---

## Next Steps → Phase 2H

Phase 2H replaces mock with real infrastructure:
- SQS queues for job distribution
- Crawler Lambda for fetching HTML
- Extractor Lambda for parsing content
- S3 storage for raw HTML
- SimHash deduplication

---

## References

**External Documentation**:
- [AWS Lambda Async Invoke](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html)
- [SSE EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [PostgreSQL UPSERT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT)

**Internal Documentation**:
- [PHASE_2F_SUMMARY.md](./PHASE_2F_SUMMARY.md) - Run lifecycle endpoints
- [PHASE_2H_SUMMARY.md](./PHASE_2H_SUMMARY.md) - Real SQS + Lambda workers
