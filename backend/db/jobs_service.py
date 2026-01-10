"""
Database service functions for job records.

Provides UPSERT and expired job detection functions used by the ingestion worker.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from models.job import Job, JobStatus

# Import conditionally to avoid circular imports
# workers/types.py imports from this module
if TYPE_CHECKING:
    from workers.types import JobData

logger = logging.getLogger(__name__)


def upsert_jobs(
    db: Session,
    user_id: int,
    run_id: int,
    company: str,
    jobs: list[dict],
) -> dict:
    """
    UPSERT jobs for a company: insert new jobs, update existing ones.

    For each job:
    - If not exists: create with status='pending'
    - If exists: update run_id, reset status to 'pending', update metadata

    Args:
        db: Database session
        user_id: User ID who owns these jobs
        run_id: Current ingestion run ID
        company: Company name (e.g., "google")
        jobs: List of job dicts from extractor [{id, title, location, url}, ...]

    Returns:
        Dict with counts: {inserted: int, updated: int}
    """
    if not jobs:
        return {"inserted": 0, "updated": 0}

    # Use PostgreSQL's INSERT ... ON CONFLICT DO UPDATE
    stmt = insert(Job).values([
        {
            "user_id": user_id,
            "run_id": run_id,
            "company": company,
            "external_id": job["id"],
            "url": job["url"],
            "title": job.get("title"),
            "location": job.get("location"),
            "status": JobStatus.PENDING,
        }
        for job in jobs
    ])

    # ON CONFLICT: update existing records
    # Clear error_message when re-queueing jobs for a new run
    stmt = stmt.on_conflict_do_update(
        constraint="uq_user_company_job",
        set_={
            "run_id": stmt.excluded.run_id,
            "url": stmt.excluded.url,
            "title": stmt.excluded.title,
            "location": stmt.excluded.location,
            "status": JobStatus.PENDING,
            "error_message": None,
            "updated_at": datetime.now(timezone.utc),
        },
    )

    result = db.execute(stmt)
    db.commit()

    # PostgreSQL returns rowcount = number of rows affected (inserted + updated)
    # We can't easily distinguish inserted vs updated without more complex logic
    # For now, return total affected count
    total_affected = result.rowcount

    logger.info(f"UPSERT {total_affected} jobs for {company} (user={user_id}, run={run_id})")

    return {"total": total_affected}


def upsert_jobs_from_job_data(
    db: Session,
    user_id: int,
    run_id: int,
    jobs: list["JobData"],
) -> dict:
    """
    UPSERT jobs from typed JobData list.

    This is the typed version of upsert_jobs() that accepts JobData objects
    instead of raw dicts. Each JobData contains its own company via identifier.

    Args:
        db: Database session
        user_id: User ID who owns these jobs
        run_id: Current ingestion run ID
        jobs: List of JobData objects from initialization phase

    Returns:
        Dict with counts: {total: int}
    """
    if not jobs:
        return {"total": 0}

    # Use PostgreSQL's INSERT ... ON CONFLICT DO UPDATE
    stmt = insert(Job).values([
        {
            "user_id": user_id,
            "run_id": run_id,
            "company": job.identifier.company,
            "external_id": job.identifier.external_id,
            "url": job.url,
            "title": job.title,
            "location": job.location,
            "status": JobStatus.PENDING,
        }
        for job in jobs
    ])

    # ON CONFLICT: update existing records
    # Clear error_message when re-queueing jobs for a new run
    stmt = stmt.on_conflict_do_update(
        constraint="uq_user_company_job",
        set_={
            "run_id": stmt.excluded.run_id,
            "url": stmt.excluded.url,
            "title": stmt.excluded.title,
            "location": stmt.excluded.location,
            "status": JobStatus.PENDING,
            "error_message": None,
            "updated_at": datetime.now(timezone.utc),
        },
    )

    result = db.execute(stmt)
    db.commit()

    total_affected = result.rowcount
    # Log by company for visibility
    companies = set(job.identifier.company for job in jobs)
    logger.info(f"UPSERT {total_affected} jobs for {companies} (user={user_id}, run={run_id})")

    return {"total": total_affected}


def mark_expired_jobs(
    db: Session,
    user_id: int,
    run_id: int,
) -> int:
    """
    Mark jobs as expired if they weren't seen in the current run.

    A job is expired if:
    - It belongs to this user
    - Its run_id is NOT the current run (wasn't updated by UPSERT)
    - It's not already expired or in an error state

    Args:
        db: Database session
        user_id: User ID
        run_id: Current ingestion run ID (jobs with this run_id are NOT expired)

    Returns:
        Number of jobs marked as expired
    """
    # Bulk UPDATE: mark all jobs not updated in this run as expired
    # UPSERT already set run_id for current jobs, so run_id != current means expired
    result = db.execute(
        text("""
            UPDATE jobs
            SET status = :expired_status, updated_at = :now
            WHERE user_id = :user_id
              AND run_id != :run_id
              AND status NOT IN (:expired_status, :error_status)
        """),
        {
            "user_id": user_id,
            "run_id": run_id,
            "expired_status": JobStatus.EXPIRED,
            "error_status": JobStatus.ERROR,
            "now": datetime.now(timezone.utc),
        },
    )
    db.commit()

    logger.info(f"Marked {result.rowcount} jobs as expired for user={user_id}")

    return result.rowcount


def get_job_counts_for_run(db: Session, run_id: int) -> dict:
    """
    Get job status counts for a run.

    Args:
        db: Database session
        run_id: Ingestion run ID

    Returns:
        Dict with counts: {total, pending, ready, skipped, expired, error}
    """
    result = db.execute(
        text("""
            SELECT status, COUNT(*) as count
            FROM jobs
            WHERE run_id = :run_id
            GROUP BY status
        """),
        {"run_id": run_id},
    )

    counts = {
        "total": 0,
        "pending": 0,
        "ready": 0,
        "skipped": 0,
        "expired": 0,
        "error": 0,
    }

    for row in result:
        status = row[0]
        count = row[1]
        counts["total"] += count
        if status in counts:
            counts[status] = count

    return counts
