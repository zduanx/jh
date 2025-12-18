"""
Test utilities for database tests.

Provides a fixed test user that persists in the test database.
Use this for tests that need a user but aren't testing user creation itself.
"""
import time
from db.user_service import get_user_by_email, create_user

# Fixed test user credentials - always the same across test runs
FIXED_TEST_USER_EMAIL = "fixed_test_user@example.com"
FIXED_TEST_USER_NAME = "Fixed Test User"


def unique_email(prefix: str = "test") -> str:
    """
    Generate unique email using timestamp.

    Format: prefix_<timestamp_ms>@example.com
    Use for tests that need to create unique users (e.g., cascade delete tests).
    """
    timestamp = int(time.time() * 1000)
    return f"{prefix}_{timestamp}@example.com"


def get_or_create_fixed_test_user(db):
    """
    Get or create the fixed test user.

    This user persists in the test database across test runs.
    Use for tests that need a user but aren't testing user creation.

    Args:
        db: Database session

    Returns:
        User object (always the same user)
    """
    user = get_user_by_email(db, FIXED_TEST_USER_EMAIL)
    if not user:
        user = create_user(db, FIXED_TEST_USER_EMAIL, FIXED_TEST_USER_NAME)
    return user
