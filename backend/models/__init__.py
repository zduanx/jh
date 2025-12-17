from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

# Import all models here for Alembic autogenerate
from models.user import User

__all__ = ["Base", "User"]
