from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import BigInteger, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column
from models import Base


class TrackingStage(str, Enum):
    """Job tracking stage enum."""
    INTERESTED = "interested"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# PostgreSQL enum type for stage
# Use values_callable to ensure lowercase values match what's in the database
tracking_stage_enum = PgEnum(
    TrackingStage,
    name="tracking_stage",
    create_type=False,  # Already created by migration
    values_callable=lambda e: [member.value for member in e],
)


class JobTracking(Base):
    """
    Model for tracking jobs that users are interested in.

    Per ADR-023: Uses separate table (not JSONB) for events to enable
    efficient calendar queries with date-range filtering.

    Unique constraint: (user_id, job_id)
    """
    __tablename__ = "job_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False
    )

    stage: Mapped[TrackingStage] = mapped_column(
        tracking_stage_enum,
        nullable=False,
        default=TrackingStage.INTERESTED
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    notes: Mapped[str] = mapped_column(Text, nullable=True)

    resume_s3_url: Mapped[str] = mapped_column(Text, nullable=True)

    tracked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        # Ensure each user can only track a job once
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<JobTracking(id={self.id}, user_id={self.user_id}, job_id={self.job_id}, stage='{self.stage.value}', archived={self.is_archived})>"
