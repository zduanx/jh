"""
Pytest configuration and fixtures for database service tests.

- Uses TEST_DATABASE_URL from .env.local (separate Neon test database)
- Runs Alembic migrations to keep schema in sync
- Each test runs in isolated transaction with rollback
- Production database completely unaffected
"""
import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv
from db.__tests__.db_test_utils import get_or_create_fixed_test_user

# Find backend directory (works from any working directory)
BACKEND_DIR = Path(__file__).parent.parent.parent

# Load environment variables (.env.local takes precedence over .env)
env_local = BACKEND_DIR / '.env.local'
env_file = BACKEND_DIR / '.env'

if env_local.exists():
    load_dotenv(env_local)
elif env_file.exists():
    load_dotenv(env_file)


@pytest.fixture(scope="session")
def test_engine():
    """
    Create test database engine and run migrations.

    - Uses TEST_DATABASE_URL from .env.local (separate Neon database)
    - Runs Alembic migrations to ensure schema is up to date
    - Runs once per test session
    """
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        raise ValueError(
            "TEST_DATABASE_URL not found in .env.local file.\n\n"
            "Steps to set up:\n"
            "1. Go to Neon console (https://console.neon.tech)\n"
            "2. In your project, create a new database called 'neondb_test'\n"
            "3. Copy the connection string\n"
            "4. Add to .env.local: TEST_DATABASE_URL=postgresql://...\n"
        )

    engine = create_engine(
        test_db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    # Verify connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print(f"\n✓ Connected to test database: {test_db_url.split('@')[1].split('/')[0]}")
    except Exception as e:
        raise ConnectionError(
            f"Failed to connect to test database.\n"
            f"Error: {e}\n"
            f"Please verify TEST_DATABASE_URL in .env.local is correct."
        )

    # Run Alembic migrations
    print("Running Alembic migrations on test database...")
    alembic_ini = BACKEND_DIR / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    command.upgrade(alembic_cfg, "head")
    print("✓ Test database schema is up to date\n")

    yield engine

    print("\n✓ Test session complete")


@pytest.fixture(scope="function")
def test_db(test_engine):
    """
    Create a database session for each test with automatic rollback.

    - Fresh transaction for every test (complete isolation)
    - All changes automatically rolled back after test
    - Tests don't interfere with each other
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    TestSessionLocal = sessionmaker(bind=connection)
    db = TestSessionLocal()

    try:
        yield db
    finally:
        db.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def test_db_commit(test_engine):
    """
    Create a database session that COMMITS changes (persists data).

    - Changes persist in test database for manual inspection
    - Data stays until manually deleted
    """
    TestSessionLocal = sessionmaker(bind=test_engine)
    db = TestSessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db):
    """
    Get the fixed test user for settings tests.

    Uses a pre-defined user that persists in test DB.
    For tests that need a user but aren't testing user creation.
    """
    return get_or_create_fixed_test_user(test_db)
