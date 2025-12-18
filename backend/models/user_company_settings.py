"""UserCompanySettings model for storing per-user company extraction configurations."""
from datetime import datetime, timezone
from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models import Base


class UserCompanySettings(Base):
    """
    User company settings for job extraction.

    Stores per-user configuration for each company:
    - Which companies the user has enabled
    - Title filters (include/exclude keywords)

    Schema matches migration: 87f2af0cf6df_user_company_settings.py
    """
    __tablename__ = "user_company_settings"

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    # Foreign key to users table
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    # Company identifier (matches extractor registry keys)
    company_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    # Title filters as JSONB: {"include": [...], "exclude": [...]}
    # Use TitleFilters.from_dict() to convert to dataclass when needed
    title_filters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default='{}'
    )

    # Quick toggle without deleting settings
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default='true'
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default='now()'
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default='now()',
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'company_name', name='uq_user_company'),
        Index('ix_user_company_settings_user_id', 'user_id'),
    )

    def __repr__(self) -> str:
        return f"<UserCompanySettings(id={self.id}, user_id={self.user_id}, company={self.company_name}, enabled={self.is_enabled})>"
