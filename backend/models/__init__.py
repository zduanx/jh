from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

# Import all models here for Alembic autogenerate
from models.user import User
from models.ingestion_run import IngestionRun, RunStatus
from models.job import Job, JobStatus
from models.job_tracking import JobTracking, TrackingStage
from models.tracking_event import TrackingEvent, EventType
from models.story import Story

__all__ = [
    "Base",
    "User",
    "IngestionRun", "RunStatus",
    "Job", "JobStatus",
    "JobTracking", "TrackingStage",
    "TrackingEvent", "EventType",
    "Story",
]
