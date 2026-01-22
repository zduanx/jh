# Phase 2K: Extractor Queue Infrastructure

**Status**: ✅ Completed
**Date**: January 10, 2026
**Goal**: Implement standard SQS queue with ExtractorWorker Lambda for job content extraction

---

## Overview

Phase 2K adds the extraction pipeline after Phase 2J's crawling infrastructure. The CrawlerWorker sends messages to ExtractorQueue after saving raw HTML to S3, and ExtractorWorker Lambdas extract structured job data (description, requirements).

This phase separates extraction from crawling for independent scaling, cleaner failure handling, and future flexibility (could add LLM extraction, different extractors per company).

**Included in this phase**:
- Standard SQS queue (ExtractorQueue) - not FIFO, no rate limiting needed
- ExtractorWorker Lambda with ReservedConcurrentExecutions=5
- Distributed run finalization (both workers check completion)
- CrawlerWorker updates to send to ExtractorQueue
- Frontend log viewer extended with Extractor logs (EXT badge)

**Explicitly excluded** (deferred to future phases):
- LLM-based extraction
- Per-company custom extractors

---

## Key Achievements

### 1. Standard SQS Queue (not FIFO)
- No external rate limiting needed (reads from our S3, writes to our Neon)
- Higher throughput than FIFO (no 300 msg/s limit)
- Reference: [ADR-021](../architecture/DECISIONS.md#adr-021-standard-sqs-with-reserved-concurrency-for-extractor-rate-limiting)

### 2. ExtractorWorker Lambda
- ReservedConcurrentExecutions=5 to protect Neon from connection exhaustion
- BatchSize=1 for simple retry semantics
- Downloads raw HTML from S3, extracts structured data
- Updates job: status='ready', description, requirements

### 3. Distributed Run Finalization
- Both CrawlerWorker and ExtractorWorker check for run completion
- After setting terminal status, check: `SELECT COUNT(*) WHERE status = 'pending'`
- If 0, mark run as 'finished' with idempotent guard (`AND status = 'ingesting'`)
- Reference: [ADR-022](../architecture/DECISIONS.md#adr-022-distributed-run-finalization)

### 4. CrawlerWorker Updates
- After S3 save (content changed), send message to ExtractorQueue
- Job stays `pending` until ExtractorWorker completes
- After terminal status (skipped/error), check run finalization

### 5. Frontend Log Viewer Extended
- Added Extractor tab/card with EXT badge (purple theme)
- Three workers visible: ING (blue), CRL (teal), EXT (purple)
- Smart auto-scroll respects user scroll position per container

---

## Highlights

### Why Standard SQS (not FIFO)
Unlike CrawlerWorker, ExtractorWorker has no external rate limiting requirements:
- Reads from our S3 bucket (no third-party throttling)
- Writes to our Neon database (we control the limits)
- No per-company ordering needed

### Why ReservedConcurrentExecutions=5
- Each Lambda = 1 DB connection
- 5 Lambdas = max 5 connections (Neon free tier has 100)
- Estimated QPS: 10-25 (well within Neon capacity)

### ExtractMessage Structure
```python
@dataclass
class ExtractMessage:
    run_id: int           # For run finalization check
    job_id: int           # For DB update
    company: str          # For extractor lookup
    raw_s3_url: str       # S3 URL (e.g., "s3://bucket/raw/google/abc123.html")
    use_test_db: bool     # For test database routing
```

### Run Finalization Logic
```python
def try_finalize_run(db, run_id):
    """Called by workers after setting terminal job status."""
    # Check if any pending jobs remain
    pending_count = db.execute(
        "SELECT COUNT(*) FROM jobs WHERE run_id = :run_id AND status = 'pending'"
    ).scalar()

    if pending_count == 0:
        # Idempotent guard prevents race conditions
        db.execute("""
            UPDATE ingestion_runs
            SET status = 'finished', finished_at = NOW(), ...
            WHERE id = :run_id AND status = 'ingesting'
        """)
```

### Job Status Flow
```
pending → ready      (crawl + extraction success)
pending → skipped    (SimHash match, content unchanged)
pending → error      (crawl or extraction failed)
pending → expired    (job not in current extraction results)
```

---

## Configuration

| Setting | Value | Reason |
|---------|-------|--------|
| Queue Type | Standard | No rate limiting needed |
| BatchSize | 1 | Simple retry semantics |
| ReservedConcurrentExecutions | 5 | Limit DB connections |
| VisibilityTimeout | 60s | Longer than Lambda timeout |
| Lambda Timeout | 30s | Extraction is fast |
| Lambda Memory | 256MB | Parsing is lightweight |

---

## Testing & Validation

**Manual Testing**:
- ✅ ExtractorQueue receives messages from CrawlerWorker
- ✅ ExtractorWorker processes messages correctly
- ✅ S3 download and extraction works
- ✅ Job status updated to 'ready' on success
- ✅ Run finalization triggers when all jobs complete
- ✅ All-skipped scenario finalizes run correctly
- ✅ ExtractorWorker logs appear in frontend (EXT badge)
- ✅ Aborted runs handled correctly (workers skip, no finalization needed)

**Automated Testing**:
- ✅ Unit tests for CrawlerWorker with ExtractorQueue mocking
- ✅ Unit tests for run finalization logic

---

## Metrics

| Metric | Value |
|--------|-------|
| New Lambda functions | 1 (ExtractorWorker) |
| New SQS queues | 1 (ExtractorQueue) |
| Max concurrent ExtractorWorkers | 5 |
| Estimated extraction QPS | 10-25 |
| CloudWatch log groups | 3 (Ingestion + Crawler + Extractor) |

---

## Next Steps → Phase 3

Phase 2 (Ingestion Pipeline) is complete. Phase 3 will focus on:
- Job matching and scoring
- User preferences and filters
- Application tracking

---

## File Structure

```
backend/
├── workers/
│   ├── crawler_worker.py      # Updated: send to ExtractorQueue, check finalization
│   ├── extractor_worker.py    # NEW: SQS-triggered extractor
│   └── types.py               # Added ExtractMessage
├── db/
│   └── run_service.py         # NEW: check_run_complete(), finalize_run()
├── api/
│   └── ingestion_routes.py    # Added 'extractor' to log groups
├── scripts/
│   └── generate_template.py   # Updated for ExtractorQueue/Worker
├── .sam-config                # Added Extractor config
└── template.yaml              # Added ExtractorQueue, ExtractorWorker

frontend/src/pages/ingest/
├── Stage3Progress.js          # Added Extractor tab/card (EXT badge)
└── Stage3Progress.css         # Already had .s3-log-source-extractor
```

**Key Files**:
- [extractor_worker.py](../../backend/workers/extractor_worker.py) - ExtractorWorker handler
- [crawler_worker.py](../../backend/workers/crawler_worker.py) - Updated for ExtractorQueue
- [types.py](../../backend/workers/types.py) - ExtractMessage dataclass
- [run_service.py](../../backend/db/run_service.py) - Run finalization functions
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - Log streaming with extractor group
- [Stage3Progress.js](../../frontend/src/pages/ingest/Stage3Progress.js) - Log viewer with EXT badge

---

## References

**ADRs**:
- [ADR-021](../architecture/DECISIONS.md#adr-021-standard-sqs-with-reserved-concurrency-for-extractor-rate-limiting) - Standard SQS + reserved concurrency
- [ADR-022](../architecture/DECISIONS.md#adr-022-distributed-run-finalization) - Distributed run finalization

**Related Phases**:
- [Phase 2J: Crawler Queue](./PHASE_2J_SUMMARY.md) - Prerequisite

**External Documentation**:
- [AWS SQS Standard Queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html)
- [AWS Lambda Reserved Concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)
