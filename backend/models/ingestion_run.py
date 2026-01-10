from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import BigInteger, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models import Base


class RunStatus:
    """Ingestion run status constants."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    INGESTING = "ingesting"
    FINISHED = "finished"
    ERROR = "error"
    ABORTED = "aborted"

    # Terminal states - run is no longer active
    TERMINAL = [FINISHED, ERROR, ABORTED]


class IngestionRun(Base):
    """
    Model for tracking ingestion run progress.

    Status flow: pending → initializing → ingesting → finished/error/aborted
    """
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending"
    )

    total_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Snapshot fields (written on completion)
    jobs_ready: Mapped[int] = mapped_column(Integer, nullable=True)
    jobs_skipped: Mapped[int] = mapped_column(Integer, nullable=True)
    jobs_expired: Mapped[int] = mapped_column(Integer, nullable=True)
    jobs_failed: Mapped[int] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Phase 2J: Per-company failure tracking for circuit breaker
    # Format: {"google_failures": 0, "amazon_failures": 2, ...}
    run_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<IngestionRun(id={self.id}, user_id={self.user_id}, status='{self.status}')>"
