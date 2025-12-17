from datetime import datetime, timezone
from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from models import Base

class User(Base):
    """
    User model for storing authenticated user information.

    Schema based on ADR-009: User Creation Strategy
    - Uses BIGSERIAL (BigInteger with autoincrement) for user_id
    - Stores Google OAuth profile information
    - Tracks creation and last login timestamps
    """
    __tablename__ = "users"

    # Primary key - BIGSERIAL maps to BigInteger with autoincrement
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    # Google OAuth email - unique identifier
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    # Profile information from Google OAuth
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email='{self.email}', name='{self.name}')>"
