# Phase 2I: Real Workers (SQS + Lambda)

**Status**: 📋 Planning
**Date**: TBD
**Goal**: Replace mock ingestion with real SQS + Lambda workers for scalable job crawling

---

## Overview

Phase 2I upgrades the mock ingestion from Phase 2H to production-ready infrastructure. The core flow (SSE progress, results display) remains unchanged - we only replace the mock worker with real SQS queues and Lambda functions.

**Key insight**: SQS provides reliable message delivery with retries and DLQ. Each job is processed independently, enabling parallel crawling at scale.

**Prerequisite**: Phase 2H must be complete (SSE + frontend working end-to-end).

**Included in this phase**:
- SQS queues (crawl queue, extract queue, DLQ)
- Lambda workers (CrawlerLambda, ExtractorLambda)
- S3 storage for raw HTML
- SimHash deduplication (skip unchanged content)
- Stale run detection and recovery

**Explicitly excluded** (deferred to Phase 3):
- Job search functionality
- Application tracking
- User preferences

---

## Key Achievements

### 1. SQS-Driven Job Processing
- Crawl queue for HTML fetching
- Extract queue for content parsing
- Dead letter queue for failed messages
- Parallel processing at scale

### 2. CrawlerLambda
- Fetches job page HTML
- Computes SimHash fingerprint
- Skips unchanged content (deduplication)
- Saves changed HTML to S3

### 3. ExtractorLambda
- Downloads HTML from S3
- Extracts structured data (title, location, description)
- Updates job record with extracted data
- Marks job as 'ready'

### 4. SimHash Deduplication
- 64-bit fingerprint for fuzzy content comparison
- Hamming distance threshold for "unchanged"
- Saves ~80% extraction cost on repeat crawls
- Reference: [ADR-017](../architecture/DECISIONS.md#adr-017-simhash-for-raw-content-deduplication)

### 5. Stale Run Detection
- EventBridge scheduled rule (every 5 minutes)
- Detects runs stuck in 'ingesting' for >15 minutes
- Auto-finalize or error based on job states

---

## Architecture

```
Worker Lambda (from 2G)
    ├─> UPSERT jobs (same as before)
    ├─> Publish each job to SQS Crawl Queue  ← NEW
    └─> status = 'ingesting'

SQS Crawl Queue
    └─> CrawlerLambda (per job)
        ├─> Fetch HTML
        ├─> Compute SimHash
        ├─> If unchanged → status='skipped'
        ├─> If changed → Save to S3, queue for extraction
        └─> Check if run complete

SQS Extract Queue
    └─> ExtractorLambda (per job)
        ├─> Download HTML from S3
        ├─> Parse job details
        ├─> Update DB → status='ready'
        └─> Check if run complete
```

---

## Highlights

### Run Completion Logic

Each worker checks after processing:
- Count pending jobs for this run
- If zero pending: finalize run (write snapshot)
- Race-safe via SQL WHERE clause

### SimHash Algorithm

Fuzzy hashing to detect content changes:
- 64-bit fingerprint stored in `jobs.simhash`
- Hamming distance threshold for "unchanged"
- Handles dynamic page noise (timestamps, view counts)

### Changes from Phase 2H

| Aspect | Phase 2H (Mock) | Phase 2I (Real) |
|--------|-----------------|-----------------|
| Job processing | Wait 30s, mark all ready | Real crawl + extract |
| Parallelism | Sequential | SQS-driven parallel |
| Dedup | None | SimHash comparison |
| Storage | None | S3 for HTML |
| Failure handling | None | DLQ, stale detection |

---

## Infrastructure

**SQS Queues**:
| Queue | Purpose | Visibility | DLQ |
|-------|---------|------------|-----|
| `jh-crawl-queue` | Jobs to crawl | 6 min | Yes |
| `jh-extract-queue` | Jobs to extract | 6 min | Yes |

**Lambda Functions**:
| Function | Trigger | Timeout | Memory |
|----------|---------|---------|--------|
| CrawlerLambda | SQS | 5 min | 512 MB |
| ExtractorLambda | SQS | 5 min | 512 MB |
| StaleRunDetector | EventBridge | 30 sec | 256 MB |

**S3 Bucket**:
- Path: `raw/{run_id}/{job_id}.html`
- Lifecycle: Delete after 7 days

---

## Testing & Validation

**Manual Testing**:
- Start ingestion → Verify jobs published to SQS
- Watch crawler → Verify HTML fetched and saved to S3
- Watch extractor → Verify data extracted and job marked ready
- Repeat ingestion → Verify SimHash skips unchanged jobs
- Kill worker mid-run → Verify stale detection triggers

**Automated Testing**:
- Future: Lambda unit tests with mocked SQS/S3
- Future: Integration tests with LocalStack

---

## Next Steps → Phase 3

Phase 3 focuses on **Search & Track**:
- Job search with filters
- Application status tracking
- Notes and reminders
- Job recommendations

**Target**: Complete job management workflow

---

## File Structure

```
backend/
├── workers/
│   ├── ingestion_worker.py      # Updated to publish to SQS
│   ├── crawler_worker.py        # CrawlerLambda handler
│   └── extractor_worker.py      # ExtractorLambda handler
├── stale_detector.py            # StaleRunDetector handler
└── template.yaml                # SAM template with SQS + Lambda resources
```

**Key Files**:
- [ingestion_worker.py](../../backend/workers/ingestion_worker.py) - Job sourcing + SQS publish
- [crawler_worker.py](../../backend/workers/crawler_worker.py) - HTML fetching + SimHash
- [extractor_worker.py](../../backend/workers/extractor_worker.py) - Content extraction
- [template.yaml](../../backend/template.yaml) - AWS infrastructure

---

## References

**External Documentation**:
- [Amazon SQS](https://docs.aws.amazon.com/sqs/) - Message queue service
- [AWS Lambda + SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html) - Event source mapping
- [SimHash Paper](https://www.cs.princeton.edu/courses/archive/spring04/cos598B/bib/ChsijffeRS.pdf) - Original algorithm

**Internal Documentation**:
- [PHASE_2H_SUMMARY.md](./PHASE_2H_SUMMARY.md) - SSE + Frontend
- [ADR-017](../architecture/DECISIONS.md#adr-017-simhash-for-raw-content-deduplication) - SimHash decision
