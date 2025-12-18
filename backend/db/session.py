"""Database session management"""
import os
from typing import Generator
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables for LOCAL development only
# In Lambda, env vars are set via CloudFormation - don't override them with .env files
# AWS_LAMBDA_FUNCTION_NAME is set by Lambda runtime
_is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None

if not _is_lambda:
    # Local development: load .env.local (takes precedence over .env)
    _backend_dir = Path(__file__).parent.parent
    env_local = _backend_dir / '.env.local'
    env_file = _backend_dir / '.env'

    if env_local.exists():
        load_dotenv(env_local, override=True)
    elif env_file.exists():
        load_dotenv(env_file, override=True)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Usage in FastAPI:
        from fastapi import Depends
        from db.session import get_db

        @app.get("/users")
        def read_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
