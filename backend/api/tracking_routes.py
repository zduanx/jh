"""
API routes for job tracking (Phase 4A).

Endpoints:
- GET    /api/tracked/ids              Get tracked job IDs with stage info
- POST   /api/tracked                  Add job to tracking
- DELETE /api/tracked/{tracking_id}    Remove job from tracking
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from auth.dependencies import get_current_user
from db.session import get_db
from models.job import Job
from models.job_tracking import JobTracking, TrackingStage

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class TrackedInfo(BaseModel):
    """Tracking info for a single job."""
    tracking_id: int
    stage: str


class TrackedIdsResponse(BaseModel):
    """Response for GET /api/tracked/ids."""
    tracked: dict[str, TrackedInfo]  # job_id (as string) -> TrackedInfo


class TrackJobRequest(BaseModel):
    """Request for POST /api/tracked."""
    job_id: int


class TrackJobResponse(BaseModel):
    """Response for POST /api/tracked."""
    tracking_id: int
    job_id: int
    stage: str
    tracked_at: datetime

    model_config = {"from_attributes": True}


class DeleteTrackingResponse(BaseModel):
    """Response for DELETE /api/tracked/{tracking_id}."""
    success: bool


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/ids", response_model=TrackedIdsResponse)
async def get_tracked_ids(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all tracked job IDs with their tracking info for the current user.

    Used to populate frontend cache on Search page load.

    Auth: JWT required

    Returns:
        TrackedIdsResponse with tracked job IDs mapped to their tracking info

    Example:
        GET /api/tracked/ids
        Authorization: Bearer <jwt_token>

        Response:
        {
            "tracked": {
                "123": {"tracking_id": 5, "stage": "interested"},
                "456": {"tracking_id": 8, "stage": "applied"}
            }
        }
    """
    user_id = current_user["user_id"]

    # Get all tracked jobs for user (excluding archived)
    trackings = db.query(JobTracking).filter(
        JobTracking.user_id == user_id,
        JobTracking.is_archived == False,
    ).all()

    # Build response dict: job_id -> {tracking_id, stage}
    tracked = {}
    for t in trackings:
        tracked[str(t.job_id)] = TrackedInfo(
            tracking_id=t.id,
            stage=t.stage.value,
        )

    return TrackedIdsResponse(tracked=tracked)


@router.post("", response_model=TrackJobResponse)
async def track_job(
    request: TrackJobRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a job to the user's tracked list.

    Creates a new tracking entry with stage="interested".

    Auth: JWT required

    Request body:
        job_id: The job ID to track

    Returns:
        TrackJobResponse with the new tracking info

    Errors:
        404: Job not found or not owned by user
        409: Job already tracked

    Example:
        POST /api/tracked
        Authorization: Bearer <jwt_token>
        {"job_id": 123}

        Response:
        {
            "tracking_id": 5,
            "job_id": 123,
            "stage": "interested",
            "tracked_at": "2026-01-21T10:00:00Z"
        }
    """
    user_id = current_user["user_id"]
    job_id = request.job_id

    # Verify job exists and belongs to user
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user_id,
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Create tracking entry
    tracking = JobTracking(
        user_id=user_id,
        job_id=job_id,
        stage=TrackingStage.INTERESTED,
    )

    try:
        db.add(tracking)
        db.commit()
        db.refresh(tracking)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job {job_id} is already tracked"
        )

    logger.info(f"User {user_id} tracked job {job_id}")

    return TrackJobResponse(
        tracking_id=tracking.id,
        job_id=tracking.job_id,
        stage=tracking.stage.value,
        tracked_at=tracking.tracked_at,
    )


@router.delete("/{tracking_id}", response_model=DeleteTrackingResponse)
async def untrack_job(
    tracking_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a job from tracking.

    Only allowed when stage is "interested" to prevent accidental
    deletion of jobs with progress. For other stages, use archive instead.

    Auth: JWT required

    Path parameters:
        tracking_id: The tracking entry ID to delete

    Returns:
        DeleteTrackingResponse with success status

    Errors:
        404: Tracking not found or not owned by user
        400: Cannot delete - stage is not "interested"

    Example:
        DELETE /api/tracked/5
        Authorization: Bearer <jwt_token>

        Response:
        {"success": true}
    """
    user_id = current_user["user_id"]

    # Get tracking entry
    tracking = db.query(JobTracking).filter(
        JobTracking.id == tracking_id,
        JobTracking.user_id == user_id,
    ).first()

    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracking {tracking_id} not found"
        )

    # Only allow deletion if stage is "interested"
    if tracking.stage != TrackingStage.INTERESTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete tracking with stage '{tracking.stage.value}'. Archive it instead."
        )

    job_id = tracking.job_id
    db.delete(tracking)
    db.commit()

    logger.info(f"User {user_id} untracked job {job_id}")

    return DeleteTrackingResponse(success=True)
