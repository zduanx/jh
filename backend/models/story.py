from datetime import datetime, timezone
from sqlalchemy import BigInteger, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from models import Base


class Story(Base):
    """
    Model for behavioral interview stories using STAR format.

    Each story contains:
    - question: The behavioral interview question
    - type: Category (leadership, conflict, teamwork, etc.)
    - tags: Array of tags for filtering
    - STAR fields: situation, task, action, result
    """
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)

    type: Mapped[str] = mapped_column(Text, nullable=True)

    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        default=list,
        server_default='{}'
    )

    # STAR format fields
    situation: Mapped[str] = mapped_column(Text, nullable=True)
    task: Mapped[str] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
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
        Index('idx_stories_user_id', 'user_id'),
        Index('idx_stories_type', 'type'),
        Index('idx_stories_tags', 'tags', postgresql_using='gin'),
    )

    def __repr__(self) -> str:
        return f"<Story(id={self.id}, user_id={self.user_id}, question='{self.question[:30]}...', type='{self.type}')>"
