"""
Test suite for user service (database operations).

Tests use separate test database (TEST_DATABASE_URL) with:
- Automatic Alembic migrations (schema always in sync)
- Transaction rollback for isolation (test_db fixture)
- Timestamp-based emails (avoid collisions, always unique)
- Optional persistence for inspection (test_db_commit fixture)

Running Tests (from backend/):
    pytest db/__tests__/test_user_service.py -v                              # All tests
    pytest db/__tests__/test_user_service.py::TestCreateUser -v              # One class
    pytest db/__tests__/test_user_service.py::TestCreateUser::test_create_user_minimal -v  # One test
    pytest db/__tests__/test_user_service.py -v -s                           # With print output
    pytest db/__tests__/ -v                                                  # All db tests
"""
import pytest
import time
from datetime import datetime, timezone
from db.user_service import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_profile,
    get_or_create_user,
)
from models import User


def unique_email(prefix: str = "test") -> str:
    """
    Generate unique email using timestamp.

    Format: prefix_<timestamp_ms>@example.com
    Example: test_1702847123456@example.com

    This ensures tests can run multiple times without email collisions,
    even when using test_db_commit fixture that persists data.
    """
    timestamp = int(time.time() * 1000)
    return f"{prefix}_{timestamp}@example.com"


class TestCreateUser:
    """
    Test user creation

    Run this class:
        pytest tests/test_user_service.py::TestCreateUser -v
    """

    def test_create_user_minimal(self, test_db):
        """
        Test creating user with minimal required fields

        Run this test:
            pytest tests/test_user_service.py::TestCreateUser::test_create_user_minimal -v
        """
        email = unique_email("minimal")

        user = create_user(
            db=test_db,
            email=email,
            name="Test User Minimal"
        )

        assert user.user_id is not None
        assert user.email == email
        assert user.name == "Test User Minimal"
        assert user.picture_url is None
        assert user.created_at is not None
        assert user.last_login is not None

    def test_create_user_with_picture(self, test_db):
        """
        Test creating user with picture URL

        Run this test:
            pytest tests/test_user_service.py::TestCreateUser::test_create_user_with_picture -v
        """
        email = unique_email("withpic")

        user = create_user(
            db=test_db,
            email=email,
            name="Test User With Picture",
            picture_url="https://example.com/pic.jpg"
        )

        assert user.user_id is not None
        assert user.email == email
        assert user.picture_url == "https://example.com/pic.jpg"

    def test_create_duplicate_email_fails(self, test_db):
        """
        Test that creating user with duplicate email fails

        Run this test:
            pytest tests/test_user_service.py::TestCreateUser::test_create_duplicate_email_fails -v
        """
        email = unique_email("duplicate")

        # Create first user
        create_user(test_db, email, "User 1")

        # Try to create second user with same email - should fail
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            create_user(test_db, email, "User 2")
            test_db.commit()


class TestGetUser:
    """
    Test user retrieval

    Run this class:
        pytest tests/test_user_service.py::TestGetUser -v
    """

    def test_get_user_by_email_exists(self, test_db):
        """
        Test getting existing user by email

        Run this test:
            pytest tests/test_user_service.py::TestGetUser::test_get_user_by_email_exists -v
        """
        email = unique_email("getbyemail")

        # Create user
        created_user = create_user(test_db, email, "Get Me By Email")

        # Retrieve user
        found_user = get_user_by_email(test_db, email)

        assert found_user is not None
        assert found_user.user_id == created_user.user_id
        assert found_user.email == email

    def test_get_user_by_email_not_exists(self, test_db):
        """
        Test getting non-existent user returns None

        Run this test:
            pytest tests/test_user_service.py::TestGetUser::test_get_user_by_email_not_exists -v
        """
        user = get_user_by_email(test_db, "nonexistent@example.com")
        assert user is None

    def test_get_user_by_id_exists(self, test_db):
        """
        Test getting existing user by ID

        Run this test:
            pytest tests/test_user_service.py::TestGetUser::test_get_user_by_id_exists -v
        """
        email = unique_email("getbyid")

        # Create user
        created_user = create_user(test_db, email, "Get By ID")

        # Retrieve user
        found_user = get_user_by_id(test_db, created_user.user_id)

        assert found_user is not None
        assert found_user.user_id == created_user.user_id
        assert found_user.email == email

    def test_get_user_by_id_not_exists(self, test_db):
        """
        Test getting non-existent user by ID returns None

        Run this test:
            pytest tests/test_user_service.py::TestGetUser::test_get_user_by_id_not_exists -v
        """
        user = get_user_by_id(test_db, 999999)
        assert user is None


class TestUpdateUser:
    """
    Test user profile updates

    Run this class:
        pytest tests/test_user_service.py::TestUpdateUser -v
    """

    def test_update_user_profile(self, test_db):
        """
        Test updating user name and picture

        Run this test:
            pytest tests/test_user_service.py::TestUpdateUser::test_update_user_profile -v
        """
        email = unique_email("update")

        # Create user
        user = create_user(test_db, email, "Original Name")
        original_login = user.last_login

        # Small delay to ensure last_login timestamp is different
        time.sleep(0.01)

        # Update profile
        updated_user = update_user_profile(
            db=test_db,
            user_id=user.user_id,
            name="Updated Name",
            picture_url="https://example.com/new.jpg"
        )

        assert updated_user is not None
        assert updated_user.name == "Updated Name"
        assert updated_user.picture_url == "https://example.com/new.jpg"
        assert updated_user.last_login >= original_login

    def test_update_nonexistent_user(self, test_db):
        """
        Test updating non-existent user returns None

        Run this test:
            pytest tests/test_user_service.py::TestUpdateUser::test_update_nonexistent_user -v
        """
        result = update_user_profile(
            db=test_db,
            user_id=999999,
            name="Ghost",
            picture_url=None
        )
        assert result is None


class TestGetOrCreateUser:
    """
    Test the main auth flow function

    Run this class:
        pytest tests/test_user_service.py::TestGetOrCreateUser -v
    """

    def test_get_or_create_new_user(self, test_db):
        """
        Test creating new user via get_or_create

        Run this test:
            pytest tests/test_user_service.py::TestGetOrCreateUser::test_get_or_create_new_user -v
        """
        email = unique_email("newuser")

        user, is_new = get_or_create_user(
            db=test_db,
            email=email,
            name="New User",
            picture_url="https://example.com/new.jpg"
        )

        assert user is not None
        assert user.email == email
        assert user.name == "New User"
        assert user.picture_url == "https://example.com/new.jpg"
        assert is_new is True

    def test_get_or_create_existing_user(self, test_db):
        """
        Test getting existing user via get_or_create

        Run this test:
            pytest tests/test_user_service.py::TestGetOrCreateUser::test_get_or_create_existing_user -v
        """
        email = unique_email("existing")

        # First call - creates user
        user1, is_new1 = get_or_create_user(
            db=test_db,
            email=email,
            name="Original Name",
            picture_url="https://example.com/original.jpg"
        )
        assert is_new1 is True
        original_id = user1.user_id

        # Second call - gets existing user and updates profile
        user2, is_new2 = get_or_create_user(
            db=test_db,
            email=email,
            name="Updated Name",
            picture_url="https://example.com/updated.jpg"
        )

        assert is_new2 is False
        assert user2.user_id == original_id  # Same user
        assert user2.name == "Updated Name"  # Profile updated
        assert user2.picture_url == "https://example.com/updated.jpg"

    def test_get_or_create_updates_last_login(self, test_db):
        """
        Test that get_or_create updates last_login on returning users

        Run this test:
            pytest tests/test_user_service.py::TestGetOrCreateUser::test_get_or_create_updates_last_login -v
        """
        email = unique_email("login")

        # Create user
        user1, _ = get_or_create_user(
            db=test_db,
            email=email,
            name="Login User"
        )
        first_login = user1.last_login

        # Small delay to ensure timestamp is different
        time.sleep(0.01)

        # Simulate user logging in again
        user2, is_new = get_or_create_user(
            db=test_db,
            email=email,
            name="Login User"
        )

        assert is_new is False
        assert user2.last_login >= first_login


class TestManualInspection:
    """
    Tests that persist data for manual inspection

    Run this class:
        pytest tests/test_user_service.py::TestManualInspection -v
    """

    def test_create_inspection_users(self, test_db_commit):
        """
        Create users that persist in test database for manual inspection.

        Uses timestamp-based emails to avoid collisions on repeated runs.
        Data persists in test database after test completes.

        Run this test:
            pytest tests/test_user_service.py::TestManualInspection::test_create_inspection_users -v

        To inspect in psql:
            SELECT * FROM users WHERE email LIKE 'inspect_%@example.com'
            ORDER BY created_at DESC LIMIT 10;
        """
        # Create test users with timestamp-based emails
        email1 = unique_email("inspect_persistent1")
        email2 = unique_email("inspect_persistent2")

        user1 = create_user(
            test_db_commit,
            email1,
            "Inspection User 1",
            "https://example.com/inspect1.jpg"
        )

        user2 = create_user(
            test_db_commit,
            email2,
            "Inspection User 2",
            "https://example.com/inspect2.jpg"
        )

        # Commit changes (data persists)
        test_db_commit.commit()

        print(f"\n✓ Created persistent user 1: ID={user1.user_id}, email={email1}")
        print(f"✓ Created persistent user 2: ID={user2.user_id}, email={email2}")
        print("\nTo inspect in psql:")
        print("SELECT * FROM users WHERE email LIKE 'inspect_%@example.com' ORDER BY created_at DESC LIMIT 10;")

    def test_auth_flow_simulation(self, test_db_commit):
        """
        Simulate complete auth flow with persistent data for inspection.

        This creates a user, then simulates them logging in again,
        demonstrating the get_or_create_user pattern used in production.

        Run this test:
            pytest tests/test_user_service.py::TestManualInspection::test_auth_flow_simulation -v
        """
        email = unique_email("authflow")

        # First login - creates user
        user1, is_new1 = get_or_create_user(
            test_db_commit,
            email=email,
            name="Auth Flow User",
            picture_url="https://example.com/authflow1.jpg"
        )
        test_db_commit.commit()

        assert is_new1 is True
        print(f"\n✓ First login (new user): ID={user1.user_id}, email={email}")

        # Second login - updates profile
        time.sleep(0.01)  # Ensure different timestamp
        user2, is_new2 = get_or_create_user(
            test_db_commit,
            email=email,
            name="Auth Flow User Updated",
            picture_url="https://example.com/authflow2.jpg"
        )
        test_db_commit.commit()

        assert is_new2 is False
        assert user2.user_id == user1.user_id
        print(f"✓ Second login (existing user): ID={user2.user_id}, profile updated")
        print(f"  Name: {user1.name} → {user2.name}")
        print(f"  Picture: {user1.picture_url} → {user2.picture_url}")
        print("\nTo inspect:")
        print(f"SELECT * FROM users WHERE email = '{email}';")
