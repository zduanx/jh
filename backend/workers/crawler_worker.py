"""
Crawler Worker Lambda Handler (Phase 2J)

This Lambda is triggered by SQS FIFO queue (CrawlerQueue.fifo).
It processes one job at a time, crawling the job page and storing raw HTML in S3.

SQS Message format (from IngestionWorker):
{
    "user_id": 123,
    "run_id": 456,
    "company": "google",
    "external_id": "jobs/123456",
    "url": "https://careers.google.com/jobs/results/123456",
    "use_test_db": false
}

SQS Configuration:
- MessageGroupId: company (e.g., "google") - ensures per-company ordering
- BatchSize: 1 - one message at a time
- VisibilityTimeout: 120s - enough time for crawl + retry + sleep

Workflow:
1. Parse SQS message
2. Query run status + run_metadata (single DB call)
   - If ABORTED → return (message deleted)
   - If failures >= 5 for this company → mark job ERROR, return
3. Try crawl with internal retry (3 attempts, 1s backoff)
4. Compare SimHash with previous value
   - If similar (Hamming distance ≤ 3) → mark SKIPPED, return
   - If different → save to S3, mark READY
5. Sleep 1s before return (rate limiting)

Environment Variables:
- DATABASE_URL: PostgreSQL connection string
- RAW_BUCKET: S3 bucket for raw HTML storage
- CRAWLER_QUEUE_URL: SQS queue URL (for DLQ handling)

Log Format:
All logs use prefix [CrawlerWorker:run_id=X:job=company/external_id] for CloudWatch filtering.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import boto3
from sqlalchemy.orm import Session

from db.session import SessionLocal, get_test_session_local
from extractors import get_extractor
from extractors.config import TitleFilters
from models.ingestion_run import IngestionRun, RunStatus
from models.job import Job, JobStatus
from utils.simhash import compute_simhash, is_similar
from utils.worker_logging import CrawlerLogContext
from workers.types import CrawlMessage

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
RAW_BUCKET = os.environ.get("RAW_BUCKET", "")

# Constants
MAX_CRAWL_RETRIES = 3
CRAWL_RETRY_DELAY = 1.0  # seconds
CIRCUIT_BREAKER_THRESHOLD = 5
RATE_LIMIT_SLEEP = 1.0  # seconds before return


# =============================================================================
# S3 Operations
# =============================================================================

def save_to_s3(bucket: str, key: str, content: str) -> str:
    """
    Save raw HTML content to S3.

    Args:
        bucket: S3 bucket name
        key: S3 object key (e.g., "raw/google/jobs_123456.html")
        content: Raw HTML content

    Returns:
        S3 URL (s3://bucket/key)
    """
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType="text/html; charset=utf-8",
    )
    return f"s3://{bucket}/{key}"


def build_s3_key(company: str, external_id: str) -> str:
    """
    Build S3 key for raw HTML storage.

    Args:
        company: Company name (e.g., "google")
        external_id: Job external ID (e.g., "jobs/123456")

    Returns:
        S3 key (e.g., "raw/google/jobs_123456.html")
    """
    # Replace slashes in external_id with underscores for S3 key
    safe_id = external_id.replace("/", "_")
    return f"raw/{company}/{safe_id}.html"


# =============================================================================
# Database Operations
# =============================================================================

def get_run_with_metadata(db: Session, run_id: int) -> Optional[IngestionRun]:
    """Fetch run with run_metadata in a single query."""
    return db.query(IngestionRun).filter(IngestionRun.id == run_id).first()


def get_job(db: Session, user_id: int, company: str, external_id: str) -> Optional[Job]:
    """Fetch job by unique key."""
    return db.query(Job).filter(
        Job.user_id == user_id,
        Job.company == company,
        Job.external_id == external_id,
    ).first()


def increment_failure_count(db: Session, run: IngestionRun, company: str) -> int:
    """
    Increment failure count for a company in run_metadata.

    Args:
        db: Database session
        run: IngestionRun record
        company: Company name

    Returns:
        New failure count
    """
    key = f"{company}_failures"
    current = run.run_metadata.get(key, 0)
    new_count = current + 1

    # Update JSONB (need to reassign for SQLAlchemy to detect change)
    run.run_metadata = {**run.run_metadata, key: new_count}
    db.commit()

    return new_count


def update_job_status(
    db: Session,
    job: Job,
    status: str,
    simhash: Optional[int] = None,
    raw_s3_url: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Update job status and optional fields."""
    job.status = status
    job.updated_at = datetime.now(timezone.utc)

    if simhash is not None:
        job.simhash = simhash
    if raw_s3_url is not None:
        job.raw_s3_url = raw_s3_url
    if error_message is not None:
        job.error_message = error_message

    db.commit()


# =============================================================================
# Crawl Logic
# =============================================================================

async def crawl_with_retry(
    company: str,
    url: str,
    max_retries: int = MAX_CRAWL_RETRIES,
    retry_delay: float = CRAWL_RETRY_DELAY,
) -> str:
    """
    Crawl a job URL with retry logic.

    Args:
        company: Company name (for extractor selection)
        url: Job URL to crawl
        max_retries: Maximum number of attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Raw HTML content

    Raises:
        Exception: If all retries fail
    """
    extractor = get_extractor(company, config=TitleFilters())
    last_error = None

    for attempt in range(max_retries):
        try:
            content = await extractor.crawl_raw_info(url)
            return content
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    raise last_error or Exception("Crawl failed with no error details")


def process_crawl_message(
    db: Session,
    message: CrawlMessage,
    bucket: str,
) -> dict:
    """
    Process a single crawl message.

    Args:
        db: Database session
        message: Parsed CrawlMessage
        bucket: S3 bucket name

    Returns:
        Result dict with status and details
    """
    job_key = f"{message.job.company}/{message.job.external_id}"
    log = CrawlerLogContext(message.run_id, job_key, use_test_db=message.use_test_db)

    # Step 1: Get run status and metadata
    run = get_run_with_metadata(db, message.run_id)
    if not run:
        log.log_error("Run not found")
        return {"status": "error", "reason": "run_not_found"}

    # Check if run is aborted
    if run.status == RunStatus.ABORTED:
        log.log_info("Run aborted, skipping")
        return {"status": "skipped", "reason": "run_aborted"}

    # Check circuit breaker
    failure_key = f"{message.job.company}_failures"
    failures = run.run_metadata.get(failure_key, 0)
    if failures >= CIRCUIT_BREAKER_THRESHOLD:
        log.log_warning(f"Circuit breaker open ({failures} failures)")
        # Mark job as error
        job = get_job(db, message.user_id, message.job.company, message.job.external_id)
        if job:
            update_job_status(db, job, JobStatus.ERROR, error_message="Circuit breaker: too many failures")
        return {"status": "error", "reason": "circuit_breaker"}

    # Step 2: Crawl with retry (using URL from message, no DB query needed)
    try:
        log.log_info(f"Crawling {message.url}")
        raw_content = asyncio.run(
            crawl_with_retry(message.job.company, message.url)
        )
        log.log_info(f"Crawled {len(raw_content)} chars")
    except Exception as e:
        log.log_error(f"Crawl failed: {e}")
        # Increment failure count
        new_count = increment_failure_count(db, run, message.job.company)
        log.log_warning(f"Failure count: {new_count}")
        # Mark job as error
        job = get_job(db, message.user_id, message.job.company, message.job.external_id)
        if job:
            update_job_status(db, job, JobStatus.ERROR, error_message=str(e)[:500])
        return {"status": "error", "reason": "crawl_failed", "error": str(e)}

    # Step 3: Get job record (needed for simhash comparison and status update)
    job = get_job(db, message.user_id, message.job.company, message.job.external_id)
    if not job:
        log.log_error("Job not found in DB")
        return {"status": "error", "reason": "job_not_found"}

    # Step 4: SimHash comparison
    new_simhash = compute_simhash(raw_content)
    old_simhash = job.simhash

    if is_similar(old_simhash, new_simhash, threshold=3):
        log.log_info("Content similar (SKIPPED)")
        update_job_status(db, job, JobStatus.SKIPPED, simhash=new_simhash)
        return {"status": "skipped", "reason": "content_similar"}

    # Step 5: Save to S3
    s3_key = build_s3_key(message.job.company, message.job.external_id)
    try:
        s3_url = save_to_s3(bucket, s3_key, raw_content)
        log.log_info(f"Saved to {s3_url}")
    except Exception as e:
        log.log_error(f"S3 save failed: {e}")
        # Increment failure count
        increment_failure_count(db, run, message.job.company)
        update_job_status(db, job, JobStatus.ERROR, error_message=f"S3 error: {e}")
        return {"status": "error", "reason": "s3_failed", "error": str(e)}

    # Step 6: Update job status
    # TODO Phase 2K: Change READY → CRAWLED (new intermediate status)
    update_job_status(
        db,
        job,
        JobStatus.READY,
        simhash=new_simhash,
        raw_s3_url=s3_url,
    )
    log.log_info("Marked READY")

    # TODO Phase 2K: Step 7 - Send to ExtractorQueue.fifo for description/requirements extraction
    # extract_message = ExtractMessage(user_id=message.user_id, run_id=message.run_id, ...)
    # sqs.send_message(QueueUrl=EXTRACTOR_QUEUE_URL, MessageBody=..., MessageGroupId=company)

    return {"status": "ready", "s3_url": s3_url}


# =============================================================================
# Lambda Handler
# =============================================================================

def handler(event: dict, context) -> dict:
    """
    Lambda handler for SQS-triggered crawler worker.

    Args:
        event: SQS event with Records array
        context: Lambda context (unused)

    Returns:
        Result dict
    """
    # SQS events have Records array
    records = event.get("Records", [])
    if not records:
        logger.warning("No records in event")
        return {"status": "no_records"}

    # Process single record (BatchSize: 1)
    record = records[0]
    body = json.loads(record.get("body", "{}"))

    # Parse message
    try:
        message = CrawlMessage.from_dict(body)
    except (KeyError, TypeError) as e:
        logger.error(f"Invalid message format: {e}, body={body}")
        return {"status": "error", "reason": "invalid_message"}

    job_key = f"{message.job.company}/{message.job.external_id}"
    log = CrawlerLogContext(message.run_id, job_key, use_test_db=message.use_test_db)
    log.log_info("Processing message")

    # Get database session
    if message.use_test_db:
        log.log_info("Using TEST database")
        TestSessionLocal = get_test_session_local()
        db = TestSessionLocal()
    else:
        db = SessionLocal()

    try:
        # Process the message
        result = process_crawl_message(db, message, RAW_BUCKET)

        # Rate limit: sleep before return
        log.log_info(f"Sleeping {RATE_LIMIT_SLEEP}s (rate limit)")
        time.sleep(RATE_LIMIT_SLEEP)

        log.log_info(f"Done: {result.get('status')}")
        return result

    except Exception as e:
        log.log_error(f"Unexpected error: {e}")
        logger.exception(f"Unexpected error processing {job_key}")

        # Try to mark job as error
        try:
            job = get_job(db, message.user_id, message.job.company, message.job.external_id)
            if job and job.status == JobStatus.PENDING:
                update_job_status(db, job, JobStatus.ERROR, error_message=str(e)[:500])
        except Exception:
            pass

        return {"status": "error", "reason": "unexpected_error", "error": str(e)}

    finally:
        db.close()
