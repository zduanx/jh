# Phase 2H: Real Workers (SQS + Lambda)

**Status**: 📋 Planning
**Date**: TBD
**Goal**: Replace mock ingestion with real SQS + Lambda workers for scalable job crawling

---

## Overview

Phase 2H upgrades the mock ingestion from Phase 2G to production-ready infrastructure. The core flow (SSE progress, results display) remains unchanged - we only replace the mock worker with real SQS queues and Lambda functions.

**Key insight**: SQS provides reliable message delivery with retries and DLQ. Each job is processed independently, enabling parallel crawling at scale.

**Prerequisite**: Phase 2G must be complete (async Lambda + SSE working end-to-end).

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

## Key Components

### 1. CrawlerLambda

Triggered by SQS Crawl Queue (batch size 1):
- Fetches job page HTML
- Computes SimHash fingerprint
- Compares with previous SimHash
- If unchanged: marks job as 'skipped'
- If changed: saves HTML to S3, queues for extraction

### 2. ExtractorLambda

Triggered by SQS Extract Queue (batch size 1):
- Downloads HTML from S3
- Extracts structured data (title, location, description)
- Updates job record with extracted data
- Marks job as 'ready'

### 3. SimHash Deduplication

Fuzzy hashing to detect content changes:
- 64-bit fingerprint stored in jobs.simhash
- Hamming distance threshold for "unchanged"
- Handles dynamic page noise (timestamps, view counts)
- Saves ~80% extraction cost on repeat crawls

Reference: [ADR-017](../architecture/DECISIONS.md)

### 4. Stale Run Detection

EventBridge scheduled rule (every 5 minutes):
- Finds runs stuck in 'ingesting' for >15 minutes
- If all jobs processed: finalize run
- If jobs stuck: mark run as error

### 5. Run Completion

Each worker checks after processing:
- Count pending jobs for this run
- If zero pending: finalize run (write snapshot)
- Race-safe via SQL WHERE clause

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

## Changes from Phase 2G

| Aspect | Phase 2G (Mock) | Phase 2H (Real) |
|--------|-----------------|-----------------|
| Job processing | Wait 1 min, mark all ready | Real crawl + extract |
| Parallelism | Sequential | SQS-driven parallel |
| Dedup | None | SimHash comparison |
| Storage | None | S3 for HTML |
| Failure handling | None | DLQ, stale detection |

---

## Next Steps → Phase 3

Phase 3 focuses on **Search & Track**:
- Job search with filters
- Application status tracking
- Notes and reminders
- Job recommendations

---

## References

**External Documentation**:
- [Amazon SQS](https://docs.aws.amazon.com/sqs/) - Message queue service
- [AWS Lambda + SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html) - Event source mapping
- [SimHash Paper](https://www.cs.princeton.edu/courses/archive/spring04/cos598B/bib/ChsijffeRS.pdf)

**Internal Documentation**:
- [PHASE_2G_SUMMARY.md](./PHASE_2G_SUMMARY.md) - Async Lambda + SSE
- [DECISIONS.md](../architecture/DECISIONS.md) - ADR-016 (SSE), ADR-017 (SimHash)
