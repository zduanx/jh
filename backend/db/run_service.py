"""
Run service for ingestion run operations (Phase 2K).

Provides functions for distributed run finalization - checking if all jobs
are processed and marking the run as finished.

Reference: ADR-022 (Distributed Run Finalization)
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.ingestion_run import IngestionRun, RunStatus
from models.job import JobStatus


def get_run(db: Session, run_id: int) -> Optional[IngestionRun]:
    """Fetch run by ID."""
    return db.query(IngestionRun).filter(IngestionRun.id == run_id).first()


def check_run_complete(db: Session, run_id: int) -> bool:
    """
    Check if all jobs for a run have been processed.

    A run is complete when no jobs remain in 'pending' status.

    Args:
        db: Database session
        run_id: Run ID to check

    Returns:
        True if no pending jobs remain, False otherwise
    """
    result = db.execute(
        text("SELECT COUNT(*) FROM jobs WHERE run_id = :run_id AND status = :pending"),
        {"run_id": run_id, "pending": JobStatus.PENDING}
    )
    count = result.scalar()
    return count == 0


def finalize_run(db: Session, run_id: int) -> bool:
    """
    Mark a run as finished with final job counts.

    Uses idempotent guard (status = 'ingesting') to prevent race conditions
    when multiple workers try to finalize the same run.

    Args:
        db: Database session
        run_id: Run ID to finalize

    Returns:
        True if run was finalized, False if already finalized or not found
    """
    # Get current job counts
    counts_result = db.execute(
        text("""
            SELECT
                SUM(CASE WHEN status = :ready THEN 1 ELSE 0 END) as jobs_ready,
                SUM(CASE WHEN status = :skipped THEN 1 ELSE 0 END) as jobs_skipped,
                SUM(CASE WHEN status = :error THEN 1 ELSE 0 END) as jobs_failed,
                SUM(CASE WHEN status = :expired THEN 1 ELSE 0 END) as jobs_expired
            FROM jobs
            WHERE run_id = :run_id
        """),
        {
            "run_id": run_id,
            "ready": JobStatus.READY,
            "skipped": JobStatus.SKIPPED,
            "error": JobStatus.ERROR,
            "expired": JobStatus.EXPIRED,
        }
    )
    row = counts_result.fetchone()

    jobs_ready = row[0] or 0
    jobs_skipped = row[1] or 0
    jobs_failed = row[2] or 0
    jobs_expired = row[3] or 0

    # Update run with idempotent guard
    update_result = db.execute(
        text("""
            UPDATE ingestion_runs
            SET status = :finished,
                finished_at = :finished_at,
                jobs_ready = :jobs_ready,
                jobs_skipped = :jobs_skipped,
                jobs_failed = :jobs_failed,
                jobs_expired = :jobs_expired
            WHERE id = :run_id
              AND status = :ingesting
        """),
        {
            "run_id": run_id,
            "finished": RunStatus.FINISHED,
            "finished_at": datetime.now(timezone.utc),
            "jobs_ready": jobs_ready,
            "jobs_skipped": jobs_skipped,
            "jobs_failed": jobs_failed,
            "jobs_expired": jobs_expired,
            "ingesting": RunStatus.INGESTING,
        }
    )
    db.commit()

    # rowcount > 0 means we successfully updated (won the race)
    return update_result.rowcount > 0


def try_finalize_run(db: Session, run_id: int) -> bool:
    """
    Check if run is complete and finalize if so.

    This is the main entry point for workers to call after processing a job.
    Combines check_run_complete and finalize_run in a single call.

    Args:
        db: Database session
        run_id: Run ID to check and potentially finalize

    Returns:
        True if run was finalized by this call, False otherwise
    """
    if check_run_complete(db, run_id):
        return finalize_run(db, run_id)
    return False
