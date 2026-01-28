"""
API routes for job tracking (Phase 4A/4B/4C).

Endpoints:
- GET    /api/tracked/ids              Get tracked job IDs with stage info (4A)
- GET    /api/tracked                  List all tracked jobs with details + events (4B/4C)
- POST   /api/tracked                  Add job to tracking (4A)
- PATCH  /api/tracked/{tracking_id}    Update tracking (archive, stage, notes) (4B/4C)
- DELETE /api/tracked/{tracking_id}    Remove job from tracking (4A)

Event endpoints (Phase 4C):
- POST   /api/tracked/{tracking_id}/events              Create event
- PATCH  /api/tracked/{tracking_id}/events/{event_id}   Update event
- DELETE /api/tracked/{tracking_id}/events/{event_id}   Delete latest event (auto-rollback)

Resume endpoints (Phase 4D):
- GET    /api/tracked/{tracking_id}/resume/upload-url   Get presigned URL for direct S3 upload
- POST   /api/tracked/{tracking_id}/resume/confirm      Confirm upload and save S3 URL to DB
- GET    /api/tracked/{tracking_id}/resume/url          Get presigned URL for download/preview

Note: Rejection is handled via PATCH with stage="rejected" and notes containing
rejected_at/rejection_reason - no separate endpoint needed.
"""

import logging
import os
from datetime import datetime, date, time
from typing import Optional, Literal, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from auth.dependencies import get_current_user
from db.session import get_db
from models.job import Job
from models.job_tracking import JobTracking, TrackingStage, STAGE_ORDER
from models.tracking_event import TrackingEvent, EventType
from api.ingestion_routes import COMPANY_METADATA

logger = logging.getLogger(__name__)

# S3 bucket for resume storage
RESUME_BUCKET = os.environ.get("RESUME_CONTENT_BUCKET", "")

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


# Phase 4B models

class JobInfo(BaseModel):
    """Job details embedded in tracking response."""
    id: int
    title: Optional[str]
    company: str
    company_logo_url: Optional[str] = None
    location: Optional[str]
    description: Optional[str]
    url: str

    model_config = {"from_attributes": True}


class TrackedJobEventInfo(BaseModel):
    """Event info embedded in tracked job response."""
    id: int
    event_type: str
    event_date: date
    event_time: Optional[time] = None
    location: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    is_deletable: bool = False


class TrackedJobResponse(BaseModel):
    """Single tracked job with full details."""
    id: int
    job_id: int
    stage: str
    is_archived: bool
    notes: Optional[dict]  # JSONB (includes resume_filename)
    has_resume: bool = False  # True if resume_s3_url exists
    tracked_at: datetime
    updated_at: datetime
    job: JobInfo
    events: list[TrackedJobEventInfo] = []

    model_config = {"from_attributes": True}


class TrackedJobsListResponse(BaseModel):
    """Response for GET /api/tracked."""
    tracked_jobs: list[TrackedJobResponse]
    total: int


class UpdateTrackingRequest(BaseModel):
    """Request for PATCH /api/tracked/{tracking_id}. All fields optional."""
    is_archived: Optional[bool] = None
    stage: Optional[str] = None
    notes: Optional[dict] = None  # JSONB: full or partial notes update


class UpdateTrackingResponse(BaseModel):
    """Response for PATCH /api/tracked/{tracking_id}."""
    id: int
    job_id: int
    stage: str
    is_archived: bool
    notes: Optional[dict]  # JSONB (includes resume_filename)
    has_resume: bool = False  # True if resume_s3_url exists
    tracked_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Phase 4C: Event Pydantic Models
# =============================================================================

class TrackingEventResponse(BaseModel):
    """Single tracking event with is_deletable flag."""
    id: int
    tracking_id: int
    event_type: str
    event_date: date
    event_time: Optional[time] = None
    location: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    is_deletable: bool = False

    model_config = {"from_attributes": True}


class CreateEventRequest(BaseModel):
    """Request for POST /api/tracked/{tracking_id}/events."""
    event_type: str
    event_date: date
    event_time: Optional[time] = None
    location: Optional[str] = None
    note: Optional[str] = None


class UpdateEventRequest(BaseModel):
    """Request for PATCH /api/tracked/{tracking_id}/events/{event_id}."""
    event_date: Optional[date] = None
    event_time: Optional[time] = None
    location: Optional[str] = None
    note: Optional[str] = None


class DeleteEventResponse(BaseModel):
    """Response for DELETE /api/tracked/{tracking_id}/events/{event_id}."""
    deleted_event_id: int
    new_stage: str
    next_deletable_event: Optional[dict] = None


# =============================================================================
# Phase 4C: Stage Data Schemas
# =============================================================================

class AppliedData(BaseModel):
    """Schema for 'applied' stage data."""
    datetime: Optional[datetime] = None
    type: Optional[Literal["online", "referral"]] = "online"
    referrer_name: Optional[str] = None
    referrer_content: Optional[str] = None
    note: Optional[str] = None


class ScreeningData(BaseModel):
    """Schema for 'screening' stage data."""
    datetime: Optional[datetime] = None
    type: Optional[Literal["phone", "video"]] = "phone"
    with_person: Optional[str] = None
    note: Optional[str] = None


class InterviewData(BaseModel):
    """Schema for 'interview' stage data."""
    datetime: Optional[datetime] = None
    round: Optional[Literal["1st", "2nd", "3rd", "final"]] = "1st"
    type: Optional[Literal["technical", "behavioral", "onsite"]] = "technical"
    interviewers: Optional[str] = None
    note: Optional[str] = None


class ReferenceData(BaseModel):
    """Schema for 'reference' stage data."""
    datetime: Optional[datetime] = None
    contacts_provided: Optional[str] = None
    note: Optional[str] = None


class OfferData(BaseModel):
    """Schema for 'offer' stage data."""
    datetime: Optional[datetime] = None
    amount: Optional[str] = None
    intention: Optional[Literal["pending", "leaning accept", "leaning decline"]] = None
    note: Optional[str] = None


class RejectedData(BaseModel):
    """Schema for 'rejected' stage data."""
    datetime: Optional[datetime] = None
    note: Optional[str] = None


# Registry mapping stage name to its schema class
STAGE_SCHEMAS: dict[str, type[BaseModel]] = {
    "applied": AppliedData,
    "screening": ScreeningData,
    "interview": InterviewData,
    "reference": ReferenceData,
    "offer": OfferData,
    "rejected": RejectedData,
}


class TrackingNotes(BaseModel):
    """Root schema for notes JSONB column."""
    # Job metadata (always editable)
    salary: Optional[str] = None
    location: Optional[str] = None
    general_note: Optional[str] = None

    # Per-stage data (keyed by stage name, includes "rejected")
    stages: Optional[dict[str, Any]] = None


# =============================================================================
# Serialization / Deserialization Helpers
# =============================================================================

def parse_notes(notes_dict: Optional[dict]) -> TrackingNotes:
    """
    Deserialize JSONB notes dict into typed TrackingNotes object.

    Handles malformed data gracefully - returns defaults for invalid fields.

    Args:
        notes_dict: Raw dict from database JSONB column (or None)

    Returns:
        TrackingNotes instance with validated data (defaults for invalid fields)
    """
    if not notes_dict:
        return TrackingNotes()
    try:
        return TrackingNotes.model_validate(notes_dict)
    except Exception as e:
        # Log but don't fail - return empty notes
        logger.warning(f"Failed to parse notes, using defaults: {e}")
        return TrackingNotes()


def serialize_notes(notes: TrackingNotes) -> dict:
    """
    Serialize TrackingNotes to dict for JSONB storage.

    Args:
        notes: TrackingNotes instance

    Returns:
        Dict suitable for JSONB column (excludes None values)
    """
    return notes.model_dump(exclude_none=True)


def parse_stage_data(stage_name: str, data: dict) -> Optional[BaseModel]:
    """
    Deserialize stage-specific data using the appropriate schema.

    Handles malformed data gracefully - returns None if parsing fails.

    Args:
        stage_name: Stage key (e.g., "applied", "screening")
        data: Raw dict from notes.stages[stage_name]

    Returns:
        Typed stage data instance (AppliedData, ScreeningData, etc.)
        or None if stage_name has no schema or data is invalid
    """
    schema_class = STAGE_SCHEMAS.get(stage_name)
    if not schema_class:
        return None
    try:
        return schema_class.model_validate(data)
    except Exception as e:
        logger.warning(f"Failed to parse {stage_name} stage data: {e}")
        return None


def validate_stage_data(stage_name: str, data: dict) -> dict:
    """
    Validate stage data against its schema and return cleaned dict.

    If validation fails, returns the original data unchanged (permissive).
    This allows updates to fix invalid data while preserving unknown fields.

    Args:
        stage_name: Stage key (e.g., "applied", "screening")
        data: Raw dict to validate

    Returns:
        Validated dict (excludes None values) or original data if validation fails
    """
    parsed = parse_stage_data(stage_name, data)
    if parsed:
        return parsed.model_dump(exclude_none=True)
    # If parsing failed, return original data - let the update go through
    # This allows fixing bad data by overwriting it
    return data


def merge_notes(existing: Optional[dict], updates: dict) -> dict:
    """
    Deep merge updates into existing notes dict.

    Handles special 'stages' key by merging per-stage data.
    Updates always win - they overwrite existing data (allowing fixes).

    Args:
        existing: Current notes dict from database (or None)
        updates: New data to merge in

    Returns:
        Merged dict ready for JSONB storage
    """
    result = dict(existing) if existing else {}

    for key, value in updates.items():
        if key == "stages" and value is not None:
            # Deep merge stages
            if "stages" not in result:
                result["stages"] = {}
            for stage_name, stage_data in value.items():
                # Validate stage data if schema exists (permissive - allows fixing bad data)
                if stage_name in STAGE_SCHEMAS and stage_data:
                    stage_data = validate_stage_data(stage_name, stage_data)
                result["stages"][stage_name] = stage_data
        else:
            # Allow None to explicitly clear a field
            result[key] = value

    return result


def get_stage_data(notes: Optional[dict], stage_name: str) -> Optional[dict]:
    """
    Safely extract and validate stage data from notes.

    Returns validated data if parseable, raw data if not, or None if missing.
    Useful for reading stage data with graceful fallback.

    Args:
        notes: Notes dict from database
        stage_name: Stage key to extract

    Returns:
        Stage data dict (validated if possible) or None if not present
    """
    if not notes or "stages" not in notes:
        return None
    stages = notes.get("stages", {})
    if not stages or stage_name not in stages:
        return None

    raw_data = stages[stage_name]
    if not raw_data:
        return None

    # Try to validate, but return raw data if validation fails
    parsed = parse_stage_data(stage_name, raw_data)
    if parsed:
        return parsed.model_dump(exclude_none=True)
    return raw_data  # Return raw data as fallback


def get_events_for_tracking(db: Session, tracking_id: int, is_rejected: bool = False) -> list[TrackedJobEventInfo]:
    """
    Get all events for a tracking entry with is_deletable flag set.

    Only the latest event (by event_date, then created_at) is deletable.
    Exception: if job is rejected, only the rejected event is deletable (to allow undo).

    Args:
        db: Database session
        tracking_id: The tracking entry ID
        is_rejected: Whether the job is in rejected state

    Returns:
        List of TrackedJobEventInfo with is_deletable flags set
    """
    events = db.query(TrackingEvent).filter(
        TrackingEvent.tracking_id == tracking_id
    ).order_by(
        TrackingEvent.event_date.asc(),
        TrackingEvent.created_at.asc(),
    ).all()

    if not events:
        return []

    # Find the latest event (last in sorted list)
    latest_event_id = events[-1].id if events else None

    result = []
    for event in events:
        # Only latest event is deletable
        # Exception: rejected event IS deletable (to allow undo rejection)
        if is_rejected:
            # When rejected, only the rejected event itself is deletable
            is_deletable = event.event_type == EventType.REJECTED
        else:
            is_deletable = event.id == latest_event_id

        result.append(TrackedJobEventInfo(
            id=event.id,
            event_type=event.event_type.value,
            event_date=event.event_date,
            event_time=event.event_time,
            location=event.location,
            note=event.note,
            created_at=event.created_at,
            is_deletable=is_deletable,
        ))

    return result


def get_latest_event(db: Session, tracking_id: int) -> Optional[TrackingEvent]:
    """
    Get the latest event for a tracking entry.

    Args:
        db: Database session
        tracking_id: The tracking entry ID

    Returns:
        Latest TrackingEvent or None if no events
    """
    return db.query(TrackingEvent).filter(
        TrackingEvent.tracking_id == tracking_id
    ).order_by(
        TrackingEvent.event_date.desc(),
        TrackingEvent.created_at.desc(),
    ).first()


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=TrackedJobsListResponse)
async def list_tracked_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all tracked jobs with full job details for the Track page.

    Auth: JWT required

    Returns:
        TrackedJobsListResponse with all tracked jobs including job details

    Example:
        GET /api/tracked
        Authorization: Bearer <jwt_token>

        Response:
        {
            "tracked_jobs": [
                {
                    "id": 1,
                    "job_id": 123,
                    "stage": "interested",
                    "is_archived": false,
                    "notes": null,
                    "tracked_at": "2026-01-22T10:00:00Z",
                    "updated_at": "2026-01-22T10:00:00Z",
                    "job": {
                        "id": 123,
                        "title": "Senior Software Engineer",
                        "company": "google",
                        "location": "Seattle, WA",
                        "description": "Build scalable...",
                        "url": "https://..."
                    }
                }
            ],
            "total": 1
        }
    """
    user_id = current_user["user_id"]

    # Get all tracked jobs for user with job details
    trackings = db.query(JobTracking).options(
        joinedload(JobTracking.job)
    ).filter(
        JobTracking.user_id == user_id,
    ).order_by(
        JobTracking.is_archived,  # Active first, archived last
        JobTracking.tracked_at.desc(),
    ).all()

    # Build response
    tracked_jobs = []
    for t in trackings:
        # Skip if job was deleted
        if not t.job:
            continue

        # Get company logo URL from metadata
        company_meta = COMPANY_METADATA.get(t.job.company, {})
        logo_url = company_meta.get("logo_url")

        # Get events with is_deletable flag
        is_rejected = t.stage == TrackingStage.REJECTED
        events = get_events_for_tracking(db, t.id, is_rejected)

        tracked_jobs.append(TrackedJobResponse(
            id=t.id,
            job_id=t.job_id,
            stage=t.stage.value,
            is_archived=t.is_archived,
            notes=t.notes,
            has_resume=bool(t.resume_s3_url),
            tracked_at=t.tracked_at,
            updated_at=t.updated_at,
            job=JobInfo(
                id=t.job.id,
                title=t.job.title,
                company=t.job.company,
                company_logo_url=logo_url,
                location=t.job.location,
                description=t.job.description,
                url=t.job.url,
            ),
            events=events,
        ))

    return TrackedJobsListResponse(
        tracked_jobs=tracked_jobs,
        total=len(tracked_jobs),
    )


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


@router.patch("/{tracking_id}", response_model=UpdateTrackingResponse)
async def update_tracking(
    tracking_id: int,
    request: UpdateTrackingRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a tracking entry (archive status, stage, notes).

    All fields are optional - only include what you want to change.

    Auth: JWT required

    Path parameters:
        tracking_id: The tracking entry ID to update

    Request body (all optional):
        is_archived: Toggle archive status (Phase 4B)
        stage: Update stage (Phase 4C)
        notes: Update notes (Phase 4C)

    Returns:
        UpdateTrackingResponse with updated tracking info

    Errors:
        404: Tracking not found or not owned by user
        422: Invalid stage value

    Example:
        PATCH /api/tracked/5
        Authorization: Bearer <jwt_token>
        {"is_archived": true}

        Response:
        {
            "id": 5,
            "job_id": 123,
            "stage": "interested",
            "is_archived": true,
            "notes": null,
            "tracked_at": "2026-01-22T10:00:00Z",
            "updated_at": "2026-01-22T15:30:00Z"
        }
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

    # Update fields if provided
    if request.is_archived is not None:
        tracking.is_archived = request.is_archived

    if request.stage is not None:
        # Validate stage value
        valid_stages = [s.value for s in TrackingStage]
        if request.stage not in valid_stages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid stage. Must be one of: {', '.join(valid_stages)}"
            )
        tracking.stage = TrackingStage(request.stage)

    if request.notes is not None:
        # Merge new notes with existing (validates stage data against schemas)
        tracking.notes = merge_notes(tracking.notes, request.notes)

    db.commit()
    db.refresh(tracking)

    logger.info(f"User {user_id} updated tracking {tracking_id}")

    return UpdateTrackingResponse(
        id=tracking.id,
        job_id=tracking.job_id,
        stage=tracking.stage.value,
        is_archived=tracking.is_archived,
        notes=tracking.notes,
        has_resume=bool(tracking.resume_s3_url),
        tracked_at=tracking.tracked_at,
        updated_at=tracking.updated_at,
    )


@router.delete("/{tracking_id}", response_model=DeleteTrackingResponse)
async def untrack_job(
    tracking_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a job from tracking.

    Only allowed when stage is "interested" (initial stage) to prevent accidental
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

    # Only allow deletion if stage is "interested" (initial stage)
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


# =============================================================================
# Event Endpoints (Phase 4C)
# =============================================================================

@router.post("/{tracking_id}/events", response_model=TrackingEventResponse)
async def create_event(
    tracking_id: int,
    request: CreateEventRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new tracking event.

    Also updates the tracking stage to match the event type.

    Auth: JWT required

    Path parameters:
        tracking_id: The tracking entry ID

    Request body:
        event_type: Event type (applied, screening, interview, etc.)
        event_date: Date of the event
        event_time: Optional time of the event
        location: Optional location
        note: Optional note

    Returns:
        TrackingEventResponse with the new event

    Errors:
        404: Tracking not found or not owned by user
        422: Invalid event type
        400: Job is rejected, cannot add events

    Example:
        POST /api/tracked/5/events
        Authorization: Bearer <jwt_token>
        {
            "event_type": "interview",
            "event_date": "2026-01-25",
            "event_time": "10:00:00",
            "location": "Video call",
            "note": "Technical interview"
        }
    """
    user_id = current_user["user_id"]

    # Verify tracking exists and belongs to user
    tracking = db.query(JobTracking).filter(
        JobTracking.id == tracking_id,
        JobTracking.user_id == user_id,
    ).first()

    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracking {tracking_id} not found"
        )

    # Cannot add events if job is rejected
    if tracking.stage == TrackingStage.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add events to a rejected job"
        )

    # Validate event type
    valid_event_types = [e.value for e in EventType]
    if request.event_type not in valid_event_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid event type. Must be one of: {', '.join(valid_event_types)}"
        )

    # Create event
    event = TrackingEvent(
        tracking_id=tracking_id,
        event_type=EventType(request.event_type),
        event_date=request.event_date,
        event_time=request.event_time,
        location=request.location,
        note=request.note,
    )

    db.add(event)

    # Update tracking stage to match event type
    # Map event type to tracking stage (they share the same values except "interested")
    new_stage = TrackingStage(request.event_type)
    tracking.stage = new_stage

    db.commit()
    db.refresh(event)

    logger.info(f"User {user_id} created event {event.id} for tracking {tracking_id}")

    return TrackingEventResponse(
        id=event.id,
        tracking_id=event.tracking_id,
        event_type=event.event_type.value,
        event_date=event.event_date,
        event_time=event.event_time,
        location=event.location,
        note=event.note,
        created_at=event.created_at,
        is_deletable=True,  # Newly created event is always latest
    )


@router.patch("/{tracking_id}/events/{event_id}", response_model=TrackingEventResponse)
async def update_event(
    tracking_id: int,
    event_id: int,
    request: UpdateEventRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing tracking event.

    Event type cannot be changed. To change type, delete and recreate.

    Auth: JWT required

    Path parameters:
        tracking_id: The tracking entry ID
        event_id: The event ID to update

    Request body (all optional):
        event_date: New date
        event_time: New time
        location: New location
        note: New note

    Returns:
        TrackingEventResponse with the updated event

    Errors:
        404: Tracking or event not found
        400: Job is rejected, cannot update events

    Example:
        PATCH /api/tracked/5/events/10
        Authorization: Bearer <jwt_token>
        {"event_time": "11:00:00", "note": "Rescheduled"}
    """
    user_id = current_user["user_id"]

    # Verify tracking exists and belongs to user
    tracking = db.query(JobTracking).filter(
        JobTracking.id == tracking_id,
        JobTracking.user_id == user_id,
    ).first()

    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracking {tracking_id} not found"
        )

    # Cannot update events if job is rejected
    if tracking.stage == TrackingStage.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update events for a rejected job"
        )

    # Get the event
    event = db.query(TrackingEvent).filter(
        TrackingEvent.id == event_id,
        TrackingEvent.tracking_id == tracking_id,
    ).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )

    # Update fields if provided
    if request.event_date is not None:
        event.event_date = request.event_date
    if request.event_time is not None:
        event.event_time = request.event_time
    if request.location is not None:
        event.location = request.location
    if request.note is not None:
        event.note = request.note

    db.commit()
    db.refresh(event)

    # Check if this event is the latest (deletable)
    latest_event = get_latest_event(db, tracking_id)
    is_deletable = latest_event and latest_event.id == event.id

    logger.info(f"User {user_id} updated event {event_id} for tracking {tracking_id}")

    return TrackingEventResponse(
        id=event.id,
        tracking_id=event.tracking_id,
        event_type=event.event_type.value,
        event_date=event.event_date,
        event_time=event.event_time,
        location=event.location,
        note=event.note,
        created_at=event.created_at,
        is_deletable=is_deletable,
    )


@router.delete("/{tracking_id}/events/{event_id}", response_model=DeleteEventResponse)
async def delete_event(
    tracking_id: int,
    event_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete the latest tracking event with automatic stage rollback.

    Only the latest event can be deleted. Deleting triggers automatic stage
    rollback to the previous event's type, or "interested" if no events remain.

    Auth: JWT required

    Path parameters:
        tracking_id: The tracking entry ID
        event_id: The event ID to delete

    Returns:
        DeleteEventResponse with new stage and next deletable event info

    Errors:
        404: Tracking or event not found
        400: Cannot delete - not the latest event or job is rejected

    Example:
        DELETE /api/tracked/5/events/10
        Authorization: Bearer <jwt_token>

        Response:
        {
            "deleted_event_id": 10,
            "new_stage": "screening",
            "next_deletable_event": {"id": 9, "event_type": "screening", "event_date": "2026-01-23"}
        }
    """
    user_id = current_user["user_id"]

    # Verify tracking exists and belongs to user
    tracking = db.query(JobTracking).filter(
        JobTracking.id == tracking_id,
        JobTracking.user_id == user_id,
    ).first()

    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracking {tracking_id} not found"
        )

    # Cannot delete events if job is rejected, UNLESS deleting the rejected event itself
    # (This allows "undo rejection" by deleting the rejected event)
    if tracking.stage == TrackingStage.REJECTED:
        # Check if user is trying to delete the rejected event
        rejected_event = db.query(TrackingEvent).filter(
            TrackingEvent.tracking_id == tracking_id,
            TrackingEvent.event_type == EventType.REJECTED,
        ).first()
        if not rejected_event or rejected_event.id != event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete events for a rejected job. Delete the rejected event first to undo rejection."
            )

    # Get the event
    event = db.query(TrackingEvent).filter(
        TrackingEvent.id == event_id,
        TrackingEvent.tracking_id == tracking_id,
    ).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )

    # Check if this is the latest event
    latest_event = get_latest_event(db, tracking_id)
    if not latest_event or latest_event.id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only the latest event can be deleted"
        )

    # Delete the event
    db.delete(event)
    db.commit()

    # Find the new latest event (if any) and update stage
    new_latest = get_latest_event(db, tracking_id)

    if new_latest:
        # Rollback to previous event's type
        new_stage = TrackingStage(new_latest.event_type.value)
        tracking.stage = new_stage
        next_deletable = {
            "id": new_latest.id,
            "event_type": new_latest.event_type.value,
            "event_date": new_latest.event_date.isoformat(),
        }
    else:
        # No events left, reset to interested
        new_stage = TrackingStage.INTERESTED
        tracking.stage = new_stage
        next_deletable = None

    db.commit()

    logger.info(f"User {user_id} deleted event {event_id} for tracking {tracking_id}, new stage: {new_stage.value}")

    return DeleteEventResponse(
        deleted_event_id=event_id,
        new_stage=new_stage.value,
        next_deletable_event=next_deletable,
    )


# =============================================================================
# Resume Endpoints (Phase 4D)
# =============================================================================

class ResumeUploadUrlResponse(BaseModel):
    """Response for GET /api/tracked/{tracking_id}/resume/upload-url."""
    upload_url: str
    s3_key: str


class ResumeConfirmRequest(BaseModel):
    """Request for POST /api/tracked/{tracking_id}/resume/confirm."""
    s3_key: str
    filename: str


class ResumeConfirmResponse(BaseModel):
    """Response for POST /api/tracked/{tracking_id}/resume/confirm."""
    has_resume: bool
    resume_filename: str


class ResumeDownloadUrlResponse(BaseModel):
    """Response for GET /api/tracked/{tracking_id}/resume/url."""
    url: str


@router.get("/{tracking_id}/resume/upload-url", response_model=ResumeUploadUrlResponse)
async def get_resume_upload_url(
    tracking_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a presigned URL for direct S3 upload.

    Frontend uploads directly to S3 using this URL, bypassing backend.
    After upload completes, call POST /resume/confirm to save to DB.

    Auth: JWT required

    Path parameters:
        tracking_id: The tracking entry ID

    Returns:
        ResumeUploadUrlResponse with presigned PUT URL and s3_key

    Flow:
        1. GET /resume/upload-url -> {upload_url, s3_key}
        2. PUT file directly to upload_url
        3. POST /resume/confirm with {s3_key, filename}
    """
    import boto3
    from botocore.config import Config

    user_id = current_user["user_id"]

    # Verify tracking exists and belongs to user
    tracking = db.query(JobTracking).filter(
        JobTracking.id == tracking_id,
        JobTracking.user_id == user_id,
    ).first()

    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracking {tracking_id} not found"
        )

    if not RESUME_BUCKET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume storage not configured"
        )

    # Generate S3 key: resumes/{user_id}/{tracking_id}.pdf
    # Simple key - overwrites on re-upload (no timestamp needed)
    s3_key = f"resumes/{user_id}/{tracking_id}.pdf"

    # Generate presigned URL for PUT
    s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))

    upload_url = s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": RESUME_BUCKET,
            "Key": s3_key,
            "ContentType": "application/pdf",
        },
        ExpiresIn=300,  # 5 minutes to upload
    )

    logger.info(f"Generated upload URL for user {user_id}, tracking {tracking_id}")

    return ResumeUploadUrlResponse(
        upload_url=upload_url,
        s3_key=s3_key,
    )


@router.post("/{tracking_id}/resume/confirm", response_model=ResumeConfirmResponse)
async def confirm_resume_upload(
    tracking_id: int,
    request: ResumeConfirmRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Confirm resume upload and save S3 URL to database.

    Call this after successfully uploading to S3 via presigned URL.

    Auth: JWT required

    Path parameters:
        tracking_id: The tracking entry ID

    Request body:
        s3_key: The S3 key returned from upload-url endpoint
        filename: Original filename for display

    Returns:
        ResumeConfirmResponse with has_resume and filename
    """
    user_id = current_user["user_id"]

    # Verify tracking exists and belongs to user
    tracking = db.query(JobTracking).filter(
        JobTracking.id == tracking_id,
        JobTracking.user_id == user_id,
    ).first()

    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracking {tracking_id} not found"
        )

    # Validate s3_key matches expected pattern for this user/tracking
    expected_key = f"resumes/{user_id}/{tracking_id}.pdf"
    if request.s3_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid S3 key"
        )

    # Update tracking record
    tracking.resume_s3_url = request.s3_key
    tracking.notes = merge_notes(tracking.notes, {"resume_filename": request.filename})

    db.commit()

    logger.info(f"Confirmed resume upload for user {user_id}, tracking {tracking_id}")

    return ResumeConfirmResponse(
        has_resume=True,
        resume_filename=request.filename,
    )


@router.get("/{tracking_id}/resume/url", response_model=ResumeDownloadUrlResponse)
async def get_resume_download_url(
    tracking_id: int,
    download: bool = Query(False, description="If true, sets Content-Disposition for download"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a presigned URL to download/preview a resume from S3.

    Auth: JWT required

    Path parameters:
        tracking_id: The tracking entry ID

    Query parameters:
        download: If true, includes Content-Disposition header for download

    Returns:
        ResumeDownloadUrlResponse with presigned download URL
    """
    import boto3
    from botocore.config import Config

    user_id = current_user["user_id"]

    # Verify tracking exists and belongs to user
    tracking = db.query(JobTracking).filter(
        JobTracking.id == tracking_id,
        JobTracking.user_id == user_id,
    ).first()

    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracking {tracking_id} not found"
        )

    if not tracking.resume_s3_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume uploaded for this tracking"
        )

    if not RESUME_BUCKET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume storage not configured"
        )

    # Generate presigned URL for GET
    s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))

    params = {
        "Bucket": RESUME_BUCKET,
        "Key": tracking.resume_s3_url,
    }

    # Add Content-Disposition for download mode
    if download:
        filename = tracking.notes.get("resume_filename", "resume.pdf") if tracking.notes else "resume.pdf"
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

    url = s3_client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=3600,  # 1 hour
    )

    logger.info(f"Generated download URL for user {user_id}, tracking {tracking_id}")

    return ResumeDownloadUrlResponse(url=url)


