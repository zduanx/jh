# Phase 2K: Extractor Queue Infrastructure

**Status**: 📋 Future
**Date**: TBD
**Goal**: Implement SQS FIFO queue with ExtractorWorker Lambda for job content extraction

---

## Overview

Phase 2K adds the extraction pipeline after Phase 2J's crawling infrastructure. The CrawlerWorker will send messages to ExtractorQueue after saving raw HTML to S3, and ExtractorWorker Lambdas will extract structured job data.

This phase separates extraction from crawling for:
- Independent scaling (extraction may be slower than crawling)
- Cleaner failure handling (crawl success != extraction success)
- Future flexibility (could add LLM extraction, etc.)

**Included in this phase**:
- SQS FIFO queue (ExtractorQueue.fifo)
- ExtractorWorker Lambda (SQS-triggered)
- Add CRAWLED job status
- Update CrawlerWorker to send to ExtractorQueue after S3 save

**Prerequisites (Phase 2J)**:
- CrawlerQueue.fifo operational
- CrawlerWorker saving raw HTML to S3
- SimHash deduplication working

---

## Key Achievements

### 1. ExtractorQueue.fifo
- FIFO queue for consistent processing order
- MessageGroupId = company (optional, could use run_id)
- Receives messages from CrawlerWorker after S3 save

### 2. ExtractorWorker Lambda
- SQS-triggered with BatchSize: 1
- Downloads raw HTML from S3
- Extracts structured data (description, requirements)
- Updates job record in DB

### 3. CRAWLED Job Status
- New intermediate status between PENDING and READY
- Flow: PENDING → CRAWLED → READY
- Allows tracking crawl vs extraction progress separately

### 4. CrawlerWorker Updates
- After S3 save, send message to ExtractorQueue
- Update job status to CRAWLED (not READY)
- READY status set by ExtractorWorker

---

## Job Status Flow (Phase 2K)

```
PENDING → CRAWLED → READY
    ↘        ↘
     → SKIPPED  → ERROR
     → ERROR
     → EXPIRED
```

| Status | Description |
|--------|-------------|
| `pending` | Job created, waiting for crawler |
| `crawled` | HTML fetched and saved to S3, waiting for extraction |
| `ready` | Extraction complete, job data available |
| `skipped` | SimHash similar to previous run - no changes |
| `error` | Processing failed (crawl or extraction) |
| `expired` | Job URL returned 404 |

---

## Highlights

### Message Format
```json
{
  "run_id": 123,
  "user_id": 456,
  "company": "google",
  "external_id": "jobs/123456"
}
```

Note: No URL needed - ExtractorWorker reads S3 path from job record or constructs from company/external_id.

SQS-specific:
- `MessageGroupId`: company (e.g., "google")
- `MessageDeduplicationId`: "{run_id}-{company}-{external_id}"

### ExtractorWorker Flow
```
1. Parse message
2. Query job record (get raw_s3_url)
3. Download raw HTML from S3
4. Extract structured data:
   - description
   - requirements
   - (existing: title, location from extractor)
5. Update job (READY, description, requirements)
6. Return
```

### CrawlerWorker Flow (Updated for 2K)
```
1. Parse message
2. Query run (status + metadata)
   ├─ ABORTED → return
   └─ failures >= 5 → mark job ERROR, return
3. try:
     Crawl (3 retries, 1s backoff)
     SimHash check (skip if similar)
     S3 save
   except: increment failures, mark job ERROR, return
4. Update job (CRAWLED, simhash, raw_s3_url)  # Changed from READY
5. Send to ExtractorQueue.fifo                 # NEW
6. sleep(1)
7. Return
```

---

## Infrastructure (template.yaml additions)

```yaml
# ExtractorQueue FIFO
ExtractorQueue:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: ExtractorQueue.fifo
    FifoQueue: true
    ContentBasedDeduplication: false
    VisibilityTimeout: 120

# ExtractorWorker Lambda
ExtractorWorker:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: ExtractorWorker
    Handler: workers.extractor_worker.handler
    Timeout: 60
    MemorySize: 256
    Policies:
      - S3ReadPolicy:
          BucketName: !Ref RawContentBucket
      - SQSPollerPolicy:
          QueueName: !GetAtt ExtractorQueue.QueueName
    Environment:
      Variables:
        RAW_BUCKET: !Ref RawContentBucket
    Events:
      SQSEvent:
        Type: SQS
        Properties:
          Queue: !GetAtt ExtractorQueue.Arn
          BatchSize: 1

# CrawlerWorker needs SQS send permission for ExtractorQueue
CrawlerWorker:
  Policies:
    - SQSSendMessagePolicy:
        QueueName: !GetAtt ExtractorQueue.QueueName
  Environment:
    Variables:
      EXTRACTOR_QUEUE_URL: !Ref ExtractorQueue
```

---

## Database Schema

### jobs (modified)
```sql
-- Add CRAWLED to status enum/check constraint
-- No new columns needed (raw_s3_url added in Phase 2J)
```

### JobStatus constants
```python
class JobStatus:
    PENDING = "pending"
    CRAWLED = "crawled"  # NEW
    READY = "ready"
    SKIPPED = "skipped"
    EXPIRED = "expired"
    ERROR = "error"
```

---

## Metrics

| Metric | Value |
|--------|-------|
| New Lambda functions | 1 (ExtractorWorker) |
| New SQS queues | 1 (ExtractorQueue.fifo) |
| Job statuses added | 1 (CRAWLED) |
| Max concurrent Lambdas | 12 (6 crawler + 6 extractor) |

---

## Run Completion Detection

With two queues, completion detection changes:

```python
def check_run_complete(run_id: int):
    """Called by ExtractorWorker after updating job status"""
    pending = db.query(
        """SELECT COUNT(*) FROM jobs
           WHERE run_id = ? AND status IN ('pending', 'crawled')""",
        run_id
    )
    if pending == 0:
        db.execute(
            "UPDATE ingestion_runs SET status = 'finished', finished_at = NOW() WHERE id = ?",
            run_id
        )
```

Note: Only ExtractorWorker checks completion (not CrawlerWorker), since CRAWLED jobs are still in-progress.

---

## File Structure

```
backend/
├── workers/
│   ├── ingestion_worker.py    # No changes from 2J
│   ├── crawler_worker.py      # Update: send to ExtractorQueue, status=CRAWLED
│   └── extractor_worker.py    # NEW: SQS-triggered extractor
├── models/
│   └── job.py                 # Add CRAWLED status
└── template.yaml              # Add ExtractorQueue, ExtractorWorker
```

**Key Files**:
- [workers/extractor_worker.py](../../backend/workers/extractor_worker.py) - ExtractorWorker handler
- [workers/crawler_worker.py](../../backend/workers/crawler_worker.py) - Updated for ExtractorQueue

---

## Design Decisions

### Why Separate Queues?
1. **Independent scaling** - Extraction may need more time/memory than crawling
2. **Cleaner status tracking** - CRAWLED vs READY distinguishes pipeline stage
3. **Failure isolation** - Crawl success preserved even if extraction fails
4. **Future flexibility** - Could add LLM extraction without touching crawler

### Why FIFO for Extractor?
- Consistency with CrawlerQueue
- MessageGroupId allows per-company ordering if needed
- Built-in deduplication prevents double extraction

### Why No Rate Limiting for Extractor?
- No external API calls (just S3 + DB)
- Can process as fast as Lambda scales
- No sleep() needed

---

## References

**Related Phases**:
- [Phase 2J: Crawler Queue](./PHASE_2J_SUMMARY.md) - Prerequisite
- [ADR-020](../architecture/DECISIONS.md#adr-020-sqs-fifo-with-messagegroupid-for-crawler-rate-limiting) - Queue design

**External Documentation**:
- [AWS SQS FIFO Queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues.html)
- [AWS Lambda SQS Event Source](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
