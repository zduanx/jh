# Phase 2J: Crawler Queue Infrastructure

**Status**: ✅ Completed
**Date**: January 10, 2026
**Goal**: Implement SQS FIFO queue with CrawlerWorker Lambda for rate-limited job page crawling

---

## Overview

Phase 2J implements the real crawling infrastructure using AWS SQS FIFO queues. The IngestionWorker publishes job messages to CrawlerQueue.fifo, and CrawlerWorker Lambdas process them with per-company rate limiting via MessageGroupId.

This phase focuses on crawling only - fetching raw HTML and storing in S3. Each company gets its own message group, ensuring only one job per company is processed at a time with enforced delays between requests.

**Included in this phase**:
- SQS FIFO queue (CrawlerQueue.fifo) with MessageGroupId per company
- S3 bucket for raw HTML storage (30-day lifecycle)
- CrawlerWorker Lambda (SQS-triggered, BatchSize=1)
- SimHash for content deduplication (Hamming distance ≤ 3)
- Real SQS publishing in IngestionWorker
- Circuit breaker pattern (5 failures per company per run)
- Multi-worker CloudWatch log streaming (ADR-019)
- Frontend log viewer with 3 display modes (merged/tabs/cards)
- `[TEST]` prefix in logs for test database identification
- Dev commands for S3 debugging (`js3get`, `js3url`)

**Explicitly excluded** (deferred to Phase 2K):
- ExtractorQueue and ExtractorWorker
- Extraction from S3 content

---

## Key Achievements

### 1. SQS FIFO Queue with Rate Limiting
- MessageGroupId = company name ensures per-company ordering
- Only one message per group in-flight at a time
- Sleep before return enforces 2+ second gap between requests
- Reference: [ADR-020](../architecture/DECISIONS.md#adr-020-sqs-fifo-with-messagegroupid-for-crawler-rate-limiting)

### 2. CrawlerWorker Lambda
- SQS-triggered with BatchSize=1 for simple retry semantics
- Internal retry (3 attempts with backoff)
- SimHash deduplication skips unchanged content
- SimHash stored as signed BIGINT (converted from unsigned 64-bit)
- Reference: [ADR-017](../architecture/DECISIONS.md#adr-017-use-simhash-for-raw-content-deduplication)

### 3. Circuit Breaker Pattern
- Track failures in `ingestion_runs.run_metadata`
- After 5 failures, skip remaining jobs for that company
- Prevents wasting resources on broken APIs

### 4. IngestionWorker Integration
- Replaced mock batch processing with real SQS SendMessage
- Returns immediately after queuing (async processing)
- Propagates `use_test_db` flag for local development
- UPSERT clears `error_message` when re-queueing jobs for new runs

### 5. Multi-Worker Log Streaming
- Extended `/api/ingestion/logs/{run_id}` to query multiple CloudWatch log groups
- `groups` parameter: `ingestion`, `crawler` (comma-separated)
- Logs merged and sorted by timestamp with source tag
- Reference: [ADR-019](../architecture/DECISIONS.md#adr-019-configurable-cloudwatch-log-groups-for-multi-worker-logging)

### 6. Frontend Log Viewer with Display Modes
Three view modes for worker logs:
- **Merged**: All logs sorted by timestamp with source badges (ING/CRL)
- **Tabs**: Separate tabs per worker type with log counts
- **Cards**: Vertical stacked panels (1 per row) for simultaneous viewing
- **Smart auto-scroll**: Only auto-scrolls if user is already at bottom

### 7. Test Database Log Prefix
- Workers add `[TEST]` prefix when using test database
- Makes it immediately obvious which DB environment is active
- Format: `[TEST][WorkerType:context] message`

### 8. S3 Debugging Commands
Added to `dev.sh`:
- `js3get <path>` - Download S3 object to stdout
- `js3url <path>` - Generate presigned URL (1 hour expiry)
- Both accept full `s3://` URLs or just keys (auto-discovers bucket)

---

## Highlights

### Rate Limiting Strategy
Per-company rate limiting via FIFO MessageGroupId:
- Each company = one message group
- SQS guarantees single in-flight message per group
- CrawlerWorker sleeps before returning, creating 2+ second gaps
- 6 companies = max 6 concurrent Lambdas

### CrawlerWorker Flow
1. Parse message, check run status (abort/circuit breaker)
2. Crawl URL (3 retries with backoff)
3. SimHash check → skip if content unchanged
4. Save to S3 → update job status
5. Sleep → return (release message group)

### S3 Key Structure
Raw HTML stored at: `raw/{company}/{external_id}.html`
- 30-day lifecycle policy auto-deletes old content
- Presigned URLs available via `js3url` dev command

### SimHash Signed Conversion
SimHash produces unsigned 64-bit values (0 to 2^64-1), but PostgreSQL BIGINT is signed (-2^63 to 2^63-1).
- Convert: if value ≥ 2^63, subtract 2^64 to get signed equivalent
- Bit pattern preserved → Hamming distance still works correctly
- `hamming_distance()` masks XOR result to 64 bits for correct signed value handling

### Structured Log Patterns
Worker logs use structured prefixes for CloudWatch filtering:
- `[IngestionWorker:run_id=X]` - Initialization and SQS publishing
- `[CrawlerWorker:run_id=X:job=company/id]` - Per-job crawling progress
- `[TEST][WorkerType:...]` - Test database indicator

---

## Testing & Validation

**Manual Testing**:
- ✅ SQS message publishing from IngestionWorker
- ✅ CrawlerWorker processes messages per-company
- ✅ S3 upload and retrieval
- ✅ SimHash deduplication working (signed BIGINT storage)
- ✅ Circuit breaker triggers after 5 failures
- ✅ Multi-worker logs merged in frontend
- ✅ Log view mode toggle (merged/tabs/cards)
- ✅ `[TEST]` prefix appears for test database
- ✅ Smart auto-scroll respects user scroll position
- ✅ Error messages cleared on job re-queue

**Automated Testing**:
- ✅ Unit tests for worker logic
- ✅ Integration tests with mocked AWS services

---

## Metrics

| Metric | Value |
|--------|-------|
| New Lambda functions | 1 (CrawlerWorker) |
| New SQS queues | 1 (CrawlerQueue.fifo) |
| New S3 buckets | 1 (raw-content) |
| Rate limit | ~2s gap per company |
| Max concurrent Lambdas | 6 (one per company) |
| CloudWatch log groups | 2 (Ingestion + Crawler) |
| Frontend log view modes | 3 (merged/tabs/cards) |

---

## Next Steps → Phase 2K

Phase 2K implements the extraction pipeline:
- ExtractorQueue.fifo for job content extraction
- ExtractorWorker Lambda reads S3, extracts description/requirements
- Run finalization when all jobs processed

---

## File Structure

```
backend/
├── api/
│   └── ingestion_routes.py   # Multi-worker log endpoint (ADR-019)
├── workers/
│   ├── ingestion_worker.py   # Real SQS publishing
│   ├── crawler_worker.py     # SQS-triggered crawler
│   └── types.py              # Message types
├── utils/
│   ├── simhash.py            # SimHash implementation
│   └── worker_logging.py     # Structured log contexts with [TEST] prefix
└── template.yaml             # Queue, bucket, Lambda definitions

frontend/src/pages/ingest/
├── Stage3Progress.js         # Log viewer with 3 display modes
└── Stage3Progress.css        # Mode toggle and source badge styles

dev.sh                        # S3 debugging commands (js3get, js3url)
```

**Key Files**:
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - Multi-worker log endpoint
- [ingestion_worker.py](../../backend/workers/ingestion_worker.py) - SQS message publishing
- [crawler_worker.py](../../backend/workers/crawler_worker.py) - CrawlerWorker handler
- [simhash.py](../../backend/utils/simhash.py) - SimHash with signed BIGINT conversion
- [jobs_service.py](../../backend/db/jobs_service.py) - UPSERT with error_message clearing
- [worker_logging.py](../../backend/utils/worker_logging.py) - Structured log contexts with TEST prefix
- [Stage3Progress.js](../../frontend/src/pages/ingest/Stage3Progress.js) - Log viewer UI with smart auto-scroll
- [template.yaml](../../backend/template.yaml) - Infrastructure definitions

---

## References

**External Documentation**:
- [AWS SQS FIFO Queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues.html)
- [AWS Lambda SQS Event Source](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [CloudWatch FilterLogEvents](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_FilterLogEvents.html)
