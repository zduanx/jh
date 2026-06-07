from datetime import datetime, timezone
from sqlalchemy import BigInteger, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from models import Base
from models.job import EMBEDDING_DIM


class Resume(Base):
    """
    Phase 7A: Profile-level resume for the chat assistant — ONE per user.

    Distinct from the Phase 4C per-tracked-job resume (job_tracking.resume_s3_url),
    which is the resume sent for a specific application. This is the user's default
    resume the assistant reasons over (and embeds for semantic job matching).

    Unique constraint: (user_id) — one resume per user.
    """
    __tablename__ = "resumes"
    __table_args__ = (UniqueConstraint("user_id", name="uq_resumes_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    # S3 location of the uploaded PDF.
    s3_url: Mapped[str] = mapped_column(Text, nullable=True)

    # Original filename (for display); S3 key is always profile.pdf (overwrites).
    filename: Mapped[str] = mapped_column(Text, nullable=True)

    # Text parsed from the PDF — needed to embed AND for the LLM to read.
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)

    # Voyage embedding (1024-dim); nullable until text is extracted + embedded. ADR-032.
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, user_id={self.user_id}, has_embedding={self.embedding is not None})>"
