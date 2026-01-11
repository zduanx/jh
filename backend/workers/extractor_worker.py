"""
Extractor Worker Lambda Handler (Phase 2K)

This Lambda is triggered by SQS Standard queue (ExtractorQueue).
It processes one job at a time, extracting description/requirements from raw HTML stored in S3.

SQS Message format (from CrawlerWorker):
{
    "run_id": 456,
    "job_id": 789,
    "company": "google",
    "raw_s3_url": "s3://bucket/raw/google/jobs_123456.html",
    "use_test_db": false
}

SQS Configuration:
- Queue Type: Standard (not FIFO - no rate limiting needed)
- BatchSize: 1 - simple retry semantics
- ReservedConcurrentExecutions: 5 - limit DB connections
- VisibilityTimeout: 60s - longer than Lambda timeout

Workflow:
1. Parse SQS message
2. Download raw HTML from S3
3. Get extractor for company
4. Call extract_raw_info() -> {description, requirements}
5. Update job: status='ready', description, requirements
6. Check run finalization (if all jobs done, mark run as 'finished')
7. Return (success removes message from queue)

Environment Variables:
- DATABASE_URL: PostgreSQL connection string
- RAW_CONTENT_BUCKET: S3 bucket for raw HTML storage

Log Format:
All logs use prefix [ExtractorWorker:run_id=X:job=job_id] for CloudWatch filtering.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import boto3
from sqlalchemy.orm import Session

from db.run_service import get_run, try_finalize_run
from db.session import SessionLocal, get_test_session_local
from extractors import get_extractor
from extractors.config import TitleFilters
from models.ingestion_run import RunStatus
from models.job import Job, JobStatus
from utils.worker_logging import ExtractorLogContext
from workers.types import ExtractMessage

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
RAW_BUCKET = os.environ.get("RAW_CONTENT_BUCKET", "")


# =============================================================================
# S3 Operations
# =============================================================================

def download_from_s3(s3_url: str) -> str:
    """
    Download raw HTML content from S3.

    Args:
        s3_url: Full S3 URL (s3://bucket/key) or just the key

    Returns:
        Raw HTML content as string
    """
    s3 = boto3.client("s3")

    # Parse S3 URL
    if s3_url.startswith("s3://"):
        # s3://bucket/key format
        parts = s3_url[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
    else:
        # Just the key, use default bucket
        bucket = RAW_BUCKET
        key = s3_url

    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")
    return content


# =============================================================================
# Database Operations
# =============================================================================

def get_job_by_id(db: Session, job_id: int) -> Optional[Job]:
    """Fetch job by ID."""
    return db.query(Job).filter(Job.id == job_id).first()


def update_job_extracted(
    db: Session,
    job: Job,
    description: str,
    requirements: str,
) -> None:
    """Update job with extracted data and mark as ready."""
    job.status = JobStatus.READY
    job.description = description
    job.requirements = requirements
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


def update_job_error(
    db: Session,
    job: Job,
    error_message: str,
) -> None:
    """Mark job as error with message."""
    job.status = JobStatus.ERROR
    job.error_message = error_message[:500]  # Truncate long errors
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


# =============================================================================
# Extract Logic
# =============================================================================

def process_extract_message(
    db: Session,
    message: ExtractMessage,
) -> dict:
    """
    Process a single extract message.

    Args:
        db: Database session
        message: Parsed ExtractMessage

    Returns:
        Result dict with status and details
    """
    job_key = f"{message.company}/{message.job_id}"
    log = ExtractorLogContext(message.run_id, job_key, use_test_db=message.use_test_db)

    # Step 1: Check if run is aborted
    run = get_run(db, message.run_id)
    if not run:
        log.log_error("Run not found")
        return {"status": "error", "reason": "run_not_found"}

    if run.status == RunStatus.ABORTED:
        log.log_info("Run aborted, skipping")
        return {"status": "skipped", "reason": "run_aborted"}

    # Step 2: Get job record
    job = get_job_by_id(db, message.job_id)
    if not job:
        log.log_error("Job not found in DB")
        return {"status": "error", "reason": "job_not_found"}

    # Step 3: Download raw HTML from S3
    try:
        log.log_info(f"Downloading from S3: {message.raw_s3_url}")
        raw_content = download_from_s3(message.raw_s3_url)
        log.log_info(f"Downloaded {len(raw_content)} chars")
    except Exception as e:
        log.log_error(f"S3 download failed: {e}")
        update_job_error(db, job, f"S3 download error: {e}")
        # Check finalization even on error (job now has terminal status)
        if try_finalize_run(db, message.run_id):
            log.log_info("Run finalized (was last job)")
        return {"status": "error", "reason": "s3_download_failed", "error": str(e)}

    # Step 4: Get extractor and extract
    try:
        extractor = get_extractor(message.company, config=TitleFilters())
        log.log_info("Extracting description/requirements")
        extracted = extractor.extract_raw_info(raw_content)

        description = extracted.get("description", "")
        requirements = extracted.get("requirements", "")
        log.log_info(f"Extracted: desc={len(description)} chars, req={len(requirements)} chars")
    except Exception as e:
        log.log_error(f"Extraction failed: {e}")
        update_job_error(db, job, f"Extraction error: {e}")
        # Check finalization even on error
        if try_finalize_run(db, message.run_id):
            log.log_info("Run finalized (was last job)")
        return {"status": "error", "reason": "extraction_failed", "error": str(e)}

    # Step 5: Update job with extracted data
    update_job_extracted(db, job, description, requirements)
    log.log_info("Marked READY")

    # Step 6: Check run finalization
    if try_finalize_run(db, message.run_id):
        log.log_info("Run finalized (was last job)")

    return {"status": "ready", "job_id": message.job_id}


# =============================================================================
# Lambda Handler
# =============================================================================

def handler(event: dict, context) -> dict:
    """
    Lambda handler for SQS-triggered extractor worker.

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
        message = ExtractMessage.from_dict(body)
    except (KeyError, TypeError) as e:
        logger.error(f"Invalid message format: {e}, body={body}")
        return {"status": "error", "reason": "invalid_message"}

    job_key = f"{message.company}/{message.job_id}"
    log = ExtractorLogContext(message.run_id, job_key, use_test_db=message.use_test_db)
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
        result = process_extract_message(db, message)

        # Log result
        status = result.get('status')
        reason = result.get('reason', '')
        error = result.get('error', '')
        if status == 'error':
            log.log_info(f"Done: {status} ({reason}) - {error[:200] if error else 'no details'}")
        else:
            log.log_info(f"Done: {status}")
        return result

    except Exception as e:
        log.log_error(f"Unexpected error: {e}")
        logger.exception(f"Unexpected error processing {job_key}")

        # Try to mark job as error
        try:
            job = get_job_by_id(db, message.job_id)
            if job and job.status == JobStatus.PENDING:
                update_job_error(db, job, str(e))
                # Check finalization
                try_finalize_run(db, message.run_id)
        except Exception:
            pass

        return {"status": "error", "reason": "unexpected_error", "error": str(e)}

    finally:
        db.close()
