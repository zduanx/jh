"""
Pytest configuration and fixtures for testing.

Industry-standard approach: Separate test database on Neon PostgreSQL.
- Uses TEST_DATABASE_URL from .env.local
- Runs Alembic migrations to keep schema in sync
- Each test runs in isolated transaction with rollback
- Test data persists in database for manual inspection
- Production database completely unaffected
"""
import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

# Load environment variables (.env.local takes precedence over .env)
env_local = Path('.env.local')
env_file = Path('.env')

if env_local.exists():
    load_dotenv(env_local)
elif env_file.exists():
    load_dotenv(env_file)


@pytest.fixture(scope="session")
def test_engine():
    """
    Create test database engine and run migrations.

    - Uses TEST_DATABASE_URL from .env (separate Neon database)
    - Runs Alembic migrations to ensure schema is up to date
    - Runs once per test session
    - Ensures test database matches production schema

    Note: This connects to a separate test database, not production.
    You need to create 'neondb_test' database in Neon console first.
    """
    # Get test database URL
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

    # Create engine
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

    # Run Alembic migrations to ensure schema is up to date
    print("Running Alembic migrations on test database...")
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    # Upgrade to latest migration
    command.upgrade(alembic_cfg, "head")
    print("✓ Test database schema is up to date\n")

    yield engine

    # Do NOT clean up test data - user wants to inspect it manually
    print("\n✓ Test data persisted in database for manual inspection")


@pytest.fixture(scope="function")
def test_db(test_engine):
    """
    Create a database session for each test with automatic rollback.

    - Fresh transaction for every test (complete isolation)
    - All changes automatically rolled back after test
    - No test data persists to database
    - Fast and safe - tests don't interfere with each other

    Usage:
        def test_create_user(test_db):
            from db.user_service import create_user

            user = create_user(test_db, "test@example.com", "Test User")
            assert user.user_id is not None
            # Automatically rolled back after test finishes
    """
    # Create connection and begin transaction
    connection = test_engine.connect()
    transaction = connection.begin()

    # Create session bound to this transaction
    TestSessionLocal = sessionmaker(bind=connection)
    db = TestSessionLocal()

    try:
        yield db  # Give to test
    finally:
        db.close()
        transaction.rollback()  # Rollback all changes
        connection.close()


@pytest.fixture(scope="function")
def test_db_commit(test_engine):
    """
    Create a database session that COMMITS changes (persists data).

    - Changes are committed and persist in test database
    - Useful for manual inspection after test run
    - Data stays in database until manually deleted

    Usage:
        def test_create_and_inspect_user(test_db_commit):
            from db.user_service import create_user

            user = create_user(test_db_commit, "inspect@example.com", "Inspect Me")
            test_db_commit.commit()
            # Data persists - you can query test database to see this user
    """
    TestSessionLocal = sessionmaker(bind=test_engine)
    db = TestSessionLocal()

    try:
        yield db
    finally:
        db.close()
