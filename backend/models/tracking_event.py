from datetime import datetime, timezone, date, time
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Time, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from models import Base


class EventType:
    """Tracking event type constants."""
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    ONSITE = "onsite"
    HIRING_MANAGER = "hiring_manager"
    OFFER = "offer"
    NEGOTIATION = "negotiation"
    OTHER = "other"


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

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

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
