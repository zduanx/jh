"""
Ingestion Worker Lambda Handler

This Lambda is invoked asynchronously by the API Lambda (InvocationType='Event').
It handles the long-running job ingestion process (up to 15 minutes).

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
4. INGESTION PHASE (async via SQS, ~minutes):
   - Send job URLs to SQS for async crawling (Phase 2I)
   - For now: mock 30s wait, mark all jobs 'ready'
5. Finalize run: write snapshot counts, status → finished

Log Format:
All logs use prefix [IngestionWorker:run_id=X] for CloudWatch filtering.
Frontend can stream logs by filtering on this pattern.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import SessionLocal, get_test_session_local
from db.company_settings_service import get_enabled_settings
from db.jobs_service import upsert_jobs_from_job_data, mark_expired_jobs
from models.ingestion_run import IngestionRun, RunStatus
from sourcing.extractor_utils import run_extractors_sync
from workers.types import (
    JobData,
    CompanyResult,
    InitializationResult,
    IngestionResult,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# =============================================================================
# Logging Helpers - All logs use [IngestionWorker:run_id=X] prefix
# =============================================================================

def log_info(run_id: int, message: str) -> None:
    """Log info with standard prefix for CloudWatch filtering."""
    logger.info(f"[IngestionWorker:run_id={run_id}] {message}")


def log_warning(run_id: int, message: str) -> None:
    """Log warning with standard prefix for CloudWatch filtering."""
    logger.warning(f"[IngestionWorker:run_id={run_id}] {message}")


def log_error(run_id: int, message: str) -> None:
    """Log error with standard prefix for CloudWatch filtering."""
    logger.error(f"[IngestionWorker:run_id={run_id}] {message}")


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
        _run_extractors: Extractor function (for testing)
        _upsert_jobs: UPSERT function (for testing)
        _mark_expired_jobs: Mark expired function (for testing)

    Returns:
        InitializationResult with all jobs ready for ingestion phase
    """
    log_info(run.id, "Starting initialization phase")

    # Step 1: Run extractors for all enabled companies
    log_info(run.id, f"Running extractors for {len(settings)} companies")
    extractor_results = _run_extractors(settings)

    # Step 2: Convert to typed structures and UPSERT
    company_results: list[CompanyResult] = []

    for company_name, extractor_result in extractor_results.items():
        if extractor_result.status != "success":
            log_warning(run.id, f"Extractor failed for {company_name}: {extractor_result.error_message}")
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

        log_info(run.id, f"UPSERT {len(jobs)} jobs for {company_name}")

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

    log_info(run.id, f"Initialization complete - {result.total_jobs} jobs, {jobs_expired} expired")

    return result


def run_ingestion_phase(
    db: Session,
    run: IngestionRun,
    init_result: InitializationResult,
) -> IngestionResult:
    """
    Run ingestion phase: send jobs to SQS for crawling.

    Args:
        db: Database session
        run: Ingestion run record
        init_result: Result from initialization phase with all jobs

    Returns:
        IngestionResult with final job counts

    TODO Phase 2I: Implement real ingestion logic:
      1. Create CrawlMessage for each job using init_result.to_crawl_messages()
      2. Send messages to SQS crawl queue
      3. Return immediately (workers update DB async)
      4. Remove finalization - SQS workers will update status when done
    """
    # ==========================================================================
    # TEMPORARY MOCK - Phase 2G/2H
    # Simulates batched processing to test SSE reconnection and diff updates
    # Processes jobs in 10 batches with 6s delay between each (~60s total)
    # Each job randomly assigned: ready (70%), skipped (20%), error (10%)
    # Will be replaced with real SQS publishing in Phase 2I
    # ==========================================================================
    import random
    from models.job import Job, JobStatus

    log_info(run.id, "Starting ingestion phase (batched mock for SSE testing)")
    log_info(run.id, f"Would send {len(init_result.to_crawl_messages())} messages to SQS")

    # Get all pending job IDs for this run
    pending_jobs = db.query(Job.id).filter(
        Job.run_id == run.id,
        Job.status == JobStatus.PENDING
    ).all()
    job_ids = [j.id for j in pending_jobs]

    # Track counts for final result
    jobs_ready = 0
    jobs_skipped = 0
    jobs_failed = 0

    if job_ids:
        # Split into 10 batches (or fewer if less than 10 jobs)
        num_batches = min(10, len(job_ids))
        batch_size = len(job_ids) // num_batches
        remainder = len(job_ids) % num_batches

        batches = []
        start = 0
        for i in range(num_batches):
            # Distribute remainder across first batches
            extra = 1 if i < remainder else 0
            end = start + batch_size + extra
            batches.append(job_ids[start:end])
            start = end

        log_info(run.id, f"Processing {len(job_ids)} jobs in {len(batches)} batches (6s delay each)")

        for i, batch in enumerate(batches):
            # Wait 6s between batches (skip first batch)
            if i > 0:
                time.sleep(6)

            # Randomly assign each job a status: ready (70%), skipped (20%), error (10%)
            for job_id in batch:
                rand = random.random()
                if rand < 0.7:
                    status = JobStatus.READY
                    jobs_ready += 1
                elif rand < 0.9:
                    status = JobStatus.SKIPPED
                    jobs_skipped += 1
                else:
                    status = JobStatus.ERROR
                    jobs_failed += 1

                db.execute(
                    text("""
                        UPDATE jobs
                        SET status = :status, updated_at = :now
                        WHERE id = :job_id
                    """),
                    {
                        "job_id": job_id,
                        "status": status,
                        "now": datetime.now(timezone.utc),
                    },
                )

            db.commit()

            log_info(run.id, f"Batch {i+1}/{len(batches)}: processed {len(batch)} jobs")
    else:
        log_info(run.id, "No pending jobs to process")

    log_info(run.id, f"Processed {len(job_ids)} jobs: {jobs_ready} ready, {jobs_skipped} skipped, {jobs_failed} error")

    result = IngestionResult(
        jobs_ready=jobs_ready,
        jobs_skipped=jobs_skipped,
        jobs_expired=init_result.jobs_expired,
        jobs_failed=jobs_failed,
    )

    # Finalize run with snapshot (mock only - Phase 2I will move this to SQS workers)
    update_run_status(
        db, run,
        status=RunStatus.FINISHED,
        finished_at=datetime.now(timezone.utc),
        jobs_ready=result.jobs_ready,
        jobs_skipped=result.jobs_skipped,
        jobs_expired=result.jobs_expired,
        jobs_failed=result.jobs_failed,
    )

    log_info(run.id, f"Completed: status={RunStatus.FINISHED}, jobs_ready={result.jobs_ready}")

    return result


def process_run(
    db: Session,
    run_id: int,
    user_id: int,
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
        _*: Dependency injection for DB operations (for testing)

    Returns:
        Status dict with run_id and final status
    """
    # Get the run record
    run = _get_run(db, run_id)
    if not run:
        log_error(run_id, "Run not found")
        return {"error": f"Run {run_id} not found"}

    # Check if run was aborted before we started
    if run.status == RunStatus.ABORTED:
        log_info(run_id, "Run was aborted before worker started")
        return {"run_id": run_id, "status": RunStatus.ABORTED}

    # Update status: pending → initializing
    _update_run_status(
        db, run,
        status=RunStatus.INITIALIZING,
        started_at=datetime.now(timezone.utc),
    )
    log_info(run_id, f"Status: {RunStatus.INITIALIZING}")

    # Get enabled company settings
    settings = _get_user_enabled_settings(db, user_id)
    if not settings:
        log_error(run_id, "No enabled companies configured")
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
    init_result = _run_initialization_phase(db, run, settings)

    _update_run_status(
        db, run,
        status=run.status,
        total_jobs=init_result.total_jobs,
        jobs_expired=init_result.jobs_expired,
    )

    # Check for abort before proceeding
    _refresh_run(db, run)
    if run.status == RunStatus.ABORTED:
        log_info(run_id, "Run was aborted during initialization")
        return {"run_id": run_id, "status": RunStatus.ABORTED}

    # Update status: initializing → ingesting
    _update_run_status(db, run, status=RunStatus.INGESTING)
    log_info(run_id, f"Status: {RunStatus.INGESTING}")

    # =======================================================================
    # INGESTION PHASE
    # Runs the mock ingestion which also finalizes the run
    # Phase 2I: This will just publish to SQS and return immediately
    # =======================================================================
    ingestion_result = _run_ingestion_phase(db, run, init_result)

    # Return result (run status already updated by ingestion phase)
    return {
        "run_id": run_id,
        "status": run.status,
        **ingestion_result.to_dict(),
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
        }
        context: Lambda context (unused)

    Returns:
        Status dict with run_id and final status
    """
    run_id = event.get("run_id")
    user_id = event.get("user_id")
    use_test_db = event.get("use_test_db", False)

    if not run_id or not user_id:
        logger.error(f"Missing required fields: run_id={run_id}, user_id={user_id}")
        return {"error": "Missing run_id or user_id"}

    # Choose database based on use_test_db flag
    # When local dev invokes AWS worker, it passes use_test_db=true
    # so the worker uses TEST_DATABASE_URL instead of prod DATABASE_URL
    if use_test_db:
        log_info(run_id, "Using TEST database (use_test_db=true)")
        TestSessionLocal = get_test_session_local()
        db = TestSessionLocal()
    else:
        log_info(run_id, "Using PROD database")
        db = SessionLocal()

    log_info(run_id, f"Starting worker for user_id={user_id}")

    try:
        return process_run(db, run_id, user_id)

    except Exception as e:
        log_error(run_id, f"Worker error: {e}")
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
