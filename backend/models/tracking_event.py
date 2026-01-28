from datetime import datetime, timezone, date, time
from enum import Enum
from typing import Optional
from sqlalchemy import Integer, Text, DateTime, Date, Time, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column
from models import Base


class EventType(str, Enum):
    """Tracking event type enum.

    Mirrors TrackingStage but excludes 'interested' since it's not an actionable event.
    """
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    REFERENCE = "reference"
    OFFER = "offer"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REJECTED = "rejected"


# PostgreSQL enum type for event_type
event_type_enum = PgEnum(
    EventType,
    name="event_type",
    create_type=False,  # Created by migration
    values_callable=lambda e: [member.value for member in e],
)


class TrackingEvent(Base):
    """
    Model for individual events within a tracked job.

    Per ADR-023: Stored in separate table (not JSONB in job_tracking) to enable
    efficient calendar queries:
        SELECT * FROM tracking_events
        WHERE event_date BETWEEN :start AND :end

    Events include interviews, phone screens, offers, etc.
    """
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    tracking_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_tracking.id", ondelete="CASCADE"),
        nullable=False
    )

    event_type: Mapped[EventType] = mapped_column(event_type_enum, nullable=False)

    event_date: Mapped[date] = mapped_column(Date, nullable=False)

    event_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<TrackingEvent(id={self.id}, tracking_id={self.tracking_id}, type='{self.event_type}', date={self.event_date})>"
