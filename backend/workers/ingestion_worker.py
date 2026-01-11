"""
Ingestion Worker Lambda Handler

This Lambda is invoked asynchronously by the API Lambda (InvocationType='Event').
It handles job extraction and queues jobs for async crawling.

Event format:
{
    "run_id": 123,
    "user_id": 456,
    "use_test_db": false  // Optional: when true, uses TEST_DATABASE_URL (for local dev)
}

Workflow:
1. Update run status: pending → initializing
2. INITIALIZATION PHASE (sync, ~30s):
   - Run extractors to get job URLs from each enabled company
   - UPSERT job records to database (create new, update existing)
   - Mark expired jobs (jobs not in current extraction results)
3. Update run status: initializing → ingesting
4. INGESTION PHASE:
   - Send job URLs to SQS FIFO queue (CrawlerQueue.fifo)
   - Return immediately (CrawlerWorkers process async)
5. Run stays INGESTING until all jobs processed by CrawlerWorkers
   - Frontend polls /runs/{id}/status for progress
   - Run finalization TBD (Phase 2K or frontend-triggered)

Log Format:
All logs use prefix [IngestionWorker:run_id=X] for CloudWatch filtering.
Frontend can stream logs by filtering on this pattern.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from db.session import SessionLocal, get_test_session_local
from db.company_settings_service import get_enabled_settings
from db.jobs_service import upsert_jobs_from_job_data, mark_expired_jobs
from models.ingestion_run import IngestionRun, RunStatus
from sourcing.extractor_utils import run_extractors_sync
from utils.worker_logging import IngestionLogContext
from workers.types import (
    JobData,
    CompanyResult,
    InitializationResult,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# =============================================================================
# Database Operations (mockable for testing)
# =============================================================================

def get_run(db: Session, run_id: int) -> Optional[IngestionRun]:
    """Fetch ingestion run by ID."""
    return db.query(IngestionRun).filter(IngestionRun.id == run_id).first()


def update_run_status(
    db: Session,
    run: IngestionRun,
    status: str,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
    total_jobs: Optional[int] = None,
    jobs_ready: Optional[int] = None,
    jobs_skipped: Optional[int] = None,
    jobs_expired: Optional[int] = None,
    jobs_failed: Optional[int] = None,
) -> None:
    """Update run status and optional fields, then commit."""
    run.status = status
    if started_at is not None:
        run.started_at = started_at
    if finished_at is not None:
        run.finished_at = finished_at
    if error_message is not None:
        run.error_message = error_message
    if total_jobs is not None:
        run.total_jobs = total_jobs
    if jobs_ready is not None:
        run.jobs_ready = jobs_ready
    if jobs_skipped is not None:
        run.jobs_skipped = jobs_skipped
    if jobs_expired is not None:
        run.jobs_expired = jobs_expired
    if jobs_failed is not None:
        run.jobs_failed = jobs_failed
    db.commit()


def refresh_run(db: Session, run: IngestionRun) -> None:
    """Refresh run from DB to see latest changes (e.g., abort)."""
    db.refresh(run)


def get_user_enabled_settings(db: Session, user_id: int) -> list:
    """Get enabled company settings for user."""
    return get_enabled_settings(db, user_id)


# =============================================================================
# Worker Logic
# =============================================================================

def run_initialization_phase(
    db: Session,
    run: IngestionRun,
    settings: list,
    use_test_db: bool = False,
    _run_extractors=run_extractors_sync,
    _upsert_jobs=upsert_jobs_from_job_data,
    _mark_expired_jobs=mark_expired_jobs,
) -> InitializationResult:
    """
    Run initialization phase: extract URLs, UPSERT jobs, mark expired.

    Args:
        db: Database session
        run: Ingestion run record
        settings: List of enabled company settings
        use_test_db: Whether using test database (for log prefix)
        _run_extractors: Extractor function (for testing)
        _upsert_jobs: UPSERT function (for testing)
        _mark_expired_jobs: Mark expired function (for testing)

    Returns:
        InitializationResult with all jobs ready for ingestion phase
    """
    log = IngestionLogContext(run.id, use_test_db=use_test_db)
    log.log_info("Starting initialization phase")

    # Step 1: Run extractors for all enabled companies
    log.log_info(f"Running extractors for {len(settings)} companies")
    extractor_results = _run_extractors(settings)

    # Step 2: Convert to typed structures and UPSERT
    company_results: list[CompanyResult] = []

    for company_name, extractor_result in extractor_results.items():
        if extractor_result.status != "success":
            log.log_warning(f"Extractor failed for {company_name}: {extractor_result.error_message}")
            company_results.append(CompanyResult(
                company=company_name,
                status="error",
                error_message=extractor_result.error_message,
            ))
            continue

        # Convert extractor jobs to typed JobData
        # Extractor job format: {"id": "abc123", "title": "Engineer", "location": "NYC", "url": "https://..."}
        # → JobData(identifier=JobIdentifier(company, external_id), url, title, location)
        jobs = [
            JobData.from_extractor_job(company_name, job)
            for job in extractor_result.included_jobs
        ]

        # UPSERT jobs to database
        _upsert_jobs(
            db=db,
            user_id=run.user_id,
            run_id=run.id,
            jobs=jobs,
        )

        company_results.append(CompanyResult(
            company=company_name,
            status="success",
            jobs=jobs,
        ))

        log.log_info(f"UPSERT {len(jobs)} jobs for {company_name}")

    # Step 3: Mark expired jobs (not in current extraction results)
    # UPSERT already set run_id for current jobs, so mark_expired_jobs
    # uses run_id check to find jobs not updated in this run
    jobs_expired = _mark_expired_jobs(
        db=db,
        user_id=run.user_id,
        run_id=run.id,
    )

    # InitializationResult structure:
    # {
    #   user_id: 1,
    #   run_id: 5,
    #   companies: [
    #     CompanyResult(company="google", status="success", jobs=[
    #       JobData(identifier=JobIdentifier("google", "abc123"), url="https://...", title="Engineer", location="NYC"),
    #       JobData(identifier=JobIdentifier("google", "def456"), url="https://...", title="Manager", location="SF"),
    #     ]),
    #     CompanyResult(company="amazon", status="error", error_message="Request timed out"),
    #   ],
    #   jobs_expired: 3,
    #   total_jobs: 2,  # computed property: sum of successful company job counts
    # }
    result = InitializationResult(
        user_id=run.user_id,
        run_id=run.id,
        companies=company_results,
        jobs_expired=jobs_expired,
    )

    log.log_info(f"Initialization complete - {result.total_jobs} jobs, {jobs_expired} expired")

    return result


def run_ingestion_phase(
    db: Session,
    run: IngestionRun,
    init_result: InitializationResult,
    use_test_db: bool = False,
    force: bool = False,
) -> None:
    """
    Run ingestion phase: send jobs to SQS for async crawling.

    This function publishes CrawlMessages to the FIFO queue and returns immediately.
    The CrawlerWorker processes messages asynchronously and updates job statuses.
    Run finalization happens when all jobs are processed (tracked via SSE polling).

    Args:
        db: Database session
        run: Ingestion run record
        init_result: Result from initialization phase with all jobs
        use_test_db: Whether workers should use TEST_DATABASE_URL
        force: Phase 2L - bypass SimHash check when True
    """
    import json
    import os
    import boto3

    log = IngestionLogContext(run.id, use_test_db=use_test_db)
    log.log_info(f"Starting ingestion phase{' (force mode)' if force else ''}")

    # Get queue URL from environment
    queue_url = os.environ.get("CRAWLER_QUEUE_URL", "")
    if not queue_url:
        log.log_error("CRAWLER_QUEUE_URL not configured")
        update_run_status(
            db, run,
            status=RunStatus.ERROR,
            error_message="CRAWLER_QUEUE_URL not configured",
            finished_at=datetime.now(timezone.utc),
        )
        return

    # Generate crawl messages
    messages = init_result.to_crawl_messages(use_test_db=use_test_db, force=force)
    log.log_info(f"Sending {len(messages)} messages to SQS")

    if not messages:
        log.log_info("No jobs to crawl, marking run finished")
        update_run_status(
            db, run,
            status=RunStatus.FINISHED,
            finished_at=datetime.now(timezone.utc),
            jobs_ready=0,
            jobs_skipped=0,
            jobs_expired=init_result.jobs_expired,
            jobs_failed=0,
        )
        return

    # Send messages to SQS FIFO queue
    sqs = boto3.client("sqs")
    sent_count = 0
    failed_count = 0

    for msg in messages:
        try:
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(msg.to_dict()),
                MessageGroupId=msg.job.company,  # Per-company ordering
            )
            sent_count += 1
        except Exception as e:
            log.log_error(f"Failed to send message for {msg.job.company}/{msg.job.external_id}: {e}")
            failed_count += 1

    log.log_info(f"Sent {sent_count} messages, {failed_count} failed")

    # Run stays in INGESTING status - CrawlerWorkers update job statuses async
    # Frontend polls /runs/{id}/status to track progress
    # Run finalization happens when frontend detects all jobs processed
    log.log_info("Messages queued, returning (workers process async)")


def process_run(
    db: Session,
    run_id: int,
    user_id: int,
    use_test_db: bool = False,
    force: bool = False,
    # Dependency injection for testing
    _get_run=get_run,
    _update_run_status=update_run_status,
    _refresh_run=refresh_run,
    _get_user_enabled_settings=get_user_enabled_settings,
    _run_initialization_phase=run_initialization_phase,
    _run_ingestion_phase=run_ingestion_phase,
) -> dict:
    """
    Main worker logic - process an ingestion run.

    Args:
        db: Database session
        run_id: ID of the run to process
        user_id: ID of the user who owns the run
        use_test_db: Whether to pass use_test_db flag to SQS messages
        force: Phase 2L - bypass SimHash check when True
        _*: Dependency injection for DB operations (for testing)

    Returns:
        Status dict with run_id and final status
    """
    log = IngestionLogContext(run_id, use_test_db=use_test_db)

    # Get the run record
    run = _get_run(db, run_id)
    if not run:
        log.log_error("Run not found")
        return {"error": f"Run {run_id} not found"}

    # Check if run was aborted before we started
    if run.status == RunStatus.ABORTED:
        log.log_info("Run was aborted before worker started")
        return {"run_id": run_id, "status": RunStatus.ABORTED}

    # Update status: pending → initializing
    _update_run_status(
        db, run,
        status=RunStatus.INITIALIZING,
        started_at=datetime.now(timezone.utc),
    )
    log.log_info(f"Status: {RunStatus.INITIALIZING}")

    # Get enabled company settings
    settings = _get_user_enabled_settings(db, user_id)
    if not settings:
        log.log_error("No enabled companies configured")
        _update_run_status(
            db, run,
            status=RunStatus.ERROR,
            error_message="No enabled companies configured",
            finished_at=datetime.now(timezone.utc),
        )
        return {"run_id": run_id, "status": RunStatus.ERROR}

    # =======================================================================
    # INITIALIZATION PHASE
    # =======================================================================
    init_result = _run_initialization_phase(db, run, settings, use_test_db=use_test_db)

    _update_run_status(
        db, run,
        status=run.status,
        total_jobs=init_result.total_jobs,
        jobs_expired=init_result.jobs_expired,
    )

    # Check for abort before proceeding
    _refresh_run(db, run)
    if run.status == RunStatus.ABORTED:
        log.log_info("Run was aborted during initialization")
        return {"run_id": run_id, "status": RunStatus.ABORTED}

    # Update status: initializing → ingesting
    _update_run_status(db, run, status=RunStatus.INGESTING)
    log.log_info(f"Status: {RunStatus.INGESTING}")

    # =======================================================================
    # INGESTION PHASE
    # Publishes jobs to SQS and returns immediately
    # CrawlerWorkers process async and update job statuses in DB
    # =======================================================================
    _run_ingestion_phase(db, run, init_result, use_test_db=use_test_db, force=force)

    # Return current status (run stays INGESTING, workers update async)
    return {
        "run_id": run_id,
        "status": run.status,
        "total_jobs": init_result.total_jobs,
        "jobs_expired": init_result.jobs_expired,
    }


# =============================================================================
# Lambda Handler
# =============================================================================

def handler(event: dict, context) -> dict:
    """
    Lambda handler for async ingestion worker.

    Args:
        event: {
            run_id: int,
            user_id: int,
            use_test_db: bool  // Optional: when true, uses TEST_DATABASE_URL
            force: bool  // Optional: Phase 2L - bypass SimHash check
        }
        context: Lambda context (unused)

    Returns:
        Status dict with run_id and final status
    """
    run_id = event.get("run_id")
    user_id = event.get("user_id")
    use_test_db = event.get("use_test_db", False)
    force = event.get("force", False)

    if not run_id or not user_id:
        logger.error(f"Missing required fields: run_id={run_id}, user_id={user_id}")
        return {"error": "Missing run_id or user_id"}

    log = IngestionLogContext(run_id, use_test_db=use_test_db)

    # Choose database based on use_test_db flag
    # When local dev invokes AWS worker, it passes use_test_db=true
    # so the worker uses TEST_DATABASE_URL instead of prod DATABASE_URL
    if use_test_db:
        log.log_info("Using TEST database")
        TestSessionLocal = get_test_session_local()
        db = TestSessionLocal()
    else:
        log.log_info("Using PROD database")
        db = SessionLocal()

    log.log_info(f"Starting worker for user_id={user_id}")

    try:
        return process_run(db, run_id, user_id, use_test_db=use_test_db, force=force)

    except Exception as e:
        log.log_error(f"Worker error: {e}")
        logger.exception(f"Worker error for run {run_id}: {e}")

        # Try to mark run as error
        try:
            run = get_run(db, run_id)
            if run and run.status not in RunStatus.TERMINAL:
                update_run_status(
                    db, run,
                    status=RunStatus.ERROR,
                    error_message=str(e)[:500],  # Truncate long errors
                    finished_at=datetime.now(timezone.utc),
                )
        except Exception:
            logger.exception("Failed to update run status to error")

        return {"run_id": run_id, "status": RunStatus.ERROR, "error": str(e)}

    finally:
        db.close()
