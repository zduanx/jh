# Phase 2E: Full Ingestion Pipeline (Stages 3-5)

**Status**: 📋 Planning
**Date**: TBD
**Goal**: Complete end-to-end job ingestion with archiving, async crawling, and results display

---

## Overview

Phase 2E implements the final three stages of the ingestion workflow, completing the job ingestion pipeline with job archiving, asynchronous SQS-based crawling via Lambda workers, and results display with ingestion history. This phase adds production-grade features including stale run recovery, real-time progress tracking, and comprehensive error handling.

**Included in this phase**:
- Ingestion runs table for workflow persistence
- Stage 3: Job archiving based on source URLs
- Stage 4: Async crawling via SQS + Lambda with decentralized completion detection
- Stage 5: Results summary and ingestion history
- Stale run detection and automated recovery
- User-triggered reset functionality

**Explicitly excluded** (deferred to Phase 3):
- Job search functionality
- Application tracking
- User preferences and recommendations

---

## Key Achievements

### 1. Ingestion Runs Table
- **Purpose**: Persist workflow state across async operations
- **Key fields**: Run metadata, progress counters (processed, added, failed, archived), status tracking, heartbeat timestamps
- **Design features**: JSONB for company config, atomic counter updates, retry count for recovery
- **Stale detection**: Heartbeat field enables timeout detection for stuck runs

### 2. Stage 3 - Job Archiving
- **Strategy**: Query-based soft delete (mark as archived, not hard delete)
- **Process**: Extract current URLs via dry run, find jobs with source URLs not in current list, update status='archived'
- **Per-company archiving**: Prevents accidentally archiving jobs from companies not being updated
- **Historical tracking**: Preserved for audit trail and future "show archived" feature

### 3. Stage 4 - Async Job Crawling
- **Architecture**: SQS queue with Lambda workers processing jobs in parallel
- **Decentralized completion**: Each Lambda checks if it processed the last job, WHERE clause prevents race conditions
- **Progress tracking**: Atomic counter updates with heartbeat timestamps
- **Scalability**: Auto-scaling up to account concurrency limit (default 100)
- **Error handling**: Per-job failures don't block queue, increment jobs_failed counter
- Reference: [AWS Lambda Guide](../learning/aws.md), [Lambda-SQS Integration](../learning/lambda-sqs.md)

### 4. Stage 5 - Results Display
- **Success metrics**: Jobs added, jobs archived, jobs failed, total duration
- **Actions**: Start new ingestion (reset to Stage 1), Go to search (navigate with pre-fill)
- **Ingestion history**: Past runs table with date, companies, job counts, duration, status
- **Display format**: Success checkmark, summary cards, color-coded values

### 5. Stale Run Detection & Recovery
- **Background job**: Runs every 5 minutes (Celery Beat or EventBridge)
- **Detection logic**: Query runs with old heartbeats (15+ minutes), retry up to 3 times
- **User reset**: Manual abort button for stuck runs with confirmation dialog
- **Failure threshold**: After 3 retries, mark as failed with error message

### 6. Real-Time Progress Tracking
- **Polling**: Frontend polls every 3 seconds during Stage 4
- **Displayed metrics**: Progress bar, jobs processed/added/failed, elapsed time
- **Auto-navigation**: When status='completed', navigate to Stage 5
- **Non-blocking**: User can close page, progress continues

---

## Database Schema

**ingestion_runs table**:
- `run_id`: Integer primary key (auto-increment)
- `user_id`: Foreign key to users table, indexed
- `status`: VARCHAR (archiving, ingesting, completed, failed)
- `current_stage`: Integer (3-5)
- `total_jobs_found`, `jobs_processed`, `jobs_added`, `jobs_failed`, `jobs_archived`: Integer counters
- `companies`: JSONB array of company configurations
- `created_at`, `started_at`, `completed_at`, `last_heartbeat`: TIMESTAMP WITH TIMEZONE
- `retry_count`: Integer for recovery attempts
- `error_message`: TEXT for failure details

**Design rationale**:
- JSONB for flexible company config storage
- Atomic counters prevent race conditions in Lambda workers
- Heartbeat field enables stale run detection
- Retry count for automatic recovery attempts

Reference: [SQLAlchemy Guide](../learning/sqlalchemy.md)

---

## API Endpoints

**POST `/api/ingest/start`**:
- Purpose: Create ingestion run and start archiving (Stage 3)
- Request: Company configurations from user settings
- Response: Run object with run_id, status, current_stage
- Process: Create run record, trigger archiving, send URLs to SQS
- Auth: JWT required

**GET `/api/ingest/runs/{run_id}/progress`**:
- Purpose: Get real-time progress for Stage 4 polling
- Request: Path parameter run_id
- Response: Progress counters, status, current_stage, elapsed time
- Auth: JWT required, verify ownership

**GET `/api/ingest/history?limit=10`**:
- Purpose: Fetch past ingestion runs for history table
- Request: Query parameter limit (default 10)
- Response: Array of completed/failed runs ordered by created_at DESC
- Auth: JWT required

**POST `/api/ingest/runs/{run_id}/reset`**:
- Purpose: User-triggered abort of stuck run
- Request: Path parameter run_id
- Response: Success message
- Validation: Verify ownership, check status is archiving/ingesting
- Auth: JWT required

Reference: [API_DESIGN.md](../architecture/API_DESIGN.md)

---

## Highlights

### Decentralized Completion Detection
**Alternative**: Central coordinator tracks job count

**Chosen**: Each Lambda checks completion independently

**Rationale**: No single point of failure, scales horizontally without bottleneck, simple implementation via WHERE clause, Lambdas are stateless

**Implementation**: WHERE clause prevents race condition (`WHERE status = 'ingesting'`), only one Lambda's UPDATE succeeds

### Soft Delete for Archived Jobs
**Alternative**: Hard delete (DELETE FROM jobs)

**Chosen**: Set status='archived', keep records

**Rationale**: Historical tracking for debugging, audit trail, potential future "show archived jobs" feature, easy to purge later if needed

### Heartbeat-Based Stale Detection
**Alternative**: Timeout based on created_at only

**Chosen**: Update last_heartbeat on every Lambda execution

**Rationale**: Distinguishes "not started" from "stuck mid-execution", more accurate for long-running ingestions, allows flexible timeout thresholds, enables health monitoring

### Lambda Performance Optimization
**Batch size**: 10 messages per invocation balances cold start overhead vs parallelism

**Timeout**: 5 minutes prevents hanging

**Memory**: 512 MB estimated for crawling + parsing

**Connection pooling**: Lambda reuses DB connections when warm

Reference: [AWS Lambda Guide](../learning/aws.md)

### SQS Configuration
**Visibility timeout**: 6 minutes (longer than Lambda timeout)

**Message retention**: 24 hours

**Dead letter queue**: Captures permanent failures after retries

**Long polling**: 20 seconds receive message wait time

Reference: [Lambda-SQS Integration](../learning/lambda-sqs.md)

---

## Testing & Validation

**Manual Testing**:
- Start ingestion → Verify Stage 3 archiving works
- Verify Stage 4 progress updates every 3 seconds
- Check jobs appear in database as processed
- Confirm auto-navigation to Stage 5 on completion
- Test user reset button aborts run
- Verify stale run detector catches stuck runs (simulate old heartbeat)
- Check history page shows past runs with correct data

**Automated Testing**:
- Future: Unit tests for ingestion run creation, atomic progress updates
- Future: Completion detection test (simulate race condition)
- Future: Stale run detection logic test
- Future: Integration test for end-to-end flow (Stage 3 → 4 → 5)
- Future: Partial success test (some jobs succeed, some fail)

---

## Metrics

- **Database Tables**: 1 (ingestion_runs)
- **API Endpoints**: 4 (start, progress, history, reset)
- **Frontend Components**: 4 (Stage 3, 4, 5, history table)
- **Lambda Functions**: 1 (crawl job worker)
- **SQS Queues**: 1 (crawl jobs queue + DLQ)
- **Background Jobs**: 1 (stale run detector)
- **Target Performance**: 10-20 jobs/second at peak
- **Target Completion**: Complete end-to-end ingestion workflow

---

## Next Steps → Phase 3

Phase 3 will focus on **Search & Track**:
- Job search with filters (title, location, company)
- Advanced search (salary, remote, date posted)
- Job tracking dashboard with application status
- Notes and reminders
- Job recommendations based on user preferences

**Target**: Complete user-facing job search and tracking features

---

## File Structure

```
backend/
├── models/
│   └── ingestion_run.py          # SQLAlchemy model
├── lambda/
│   └── crawl_job_lambda.py       # SQS-triggered Lambda worker
├── jobs/
│   └── stale_run_detector.py     # Background stale run detector
├── api/
│   └── ingest_routes.py          # Add /start, /progress, /history, /reset
├── celery_config.py              # Celery Beat schedule (if using Celery)
└── alembic/versions/
    └── xxx_create_ingestion_runs.py  # Migration

frontend/src/pages/Ingest/
├── Stage3_Archive.js             # Stage 3 loading state
├── Stage4_Ingest.js              # Stage 4 with progress polling
├── Stage5_Results.js             # Results summary
├── IngestionHistory.js           # History table component
└── ResetRunButton.js             # User-triggered reset

cloudformation/
├── sqs-queues.yml                # SQS queue definitions
└── lambda-functions.yml          # Lambda function definitions
```

**Key Files**:
- [ingestion_run.py](../../backend/models/ingestion_run.py) - SQLAlchemy model
- [crawl_job_lambda.py](../../backend/lambda/crawl_job_lambda.py) - Lambda worker
- [stale_run_detector.py](../../backend/jobs/stale_run_detector.py) - Background job
- [Stage4_Ingest.js](../../frontend/src/pages/Ingest/Stage4_Ingest.js) - Progress UI

---

## Key Learnings

### Atomic Operations in Distributed Systems
Single UPDATE statement with RETURNING clause enables thread-safe progress tracking across concurrent Lambda workers. PostgreSQL handles high write throughput with proper indexing.

**Reference**: [SQLAlchemy Guide](../learning/sqlalchemy.md)

### Heartbeat Pattern for Long-Running Jobs
Regular heartbeat updates distinguish active processing from stuck jobs, enabling accurate timeout detection and automated recovery without false positives.

### Graceful Degradation in Async Pipelines
Per-job error handling with continued queue processing provides better user experience than blocking entire run on single failures. Users get partial results even with errors.

### SQS + Lambda Scalability
Auto-scaling Lambda workers with SQS queue provides cost-effective horizontal scaling for bursty workloads. Pay only for actual processing time.

**Reference**: [AWS Lambda Guide](../learning/aws.md), [Lambda-SQS Integration](../learning/lambda-sqs.md)

---

## References

**External Documentation**:
- [AWS Lambda](https://docs.aws.amazon.com/lambda/) - Serverless compute
- [Amazon SQS](https://docs.aws.amazon.com/sqs/) - Message queue service
- [PostgreSQL Atomic Operations](https://www.postgresql.org/docs/current/sql-update.html) - UPDATE with RETURNING
- [CloudWatch Metrics](https://docs.aws.amazon.com/cloudwatch/) - Monitoring and logging

---

**Status**: Ready for Phase 3
