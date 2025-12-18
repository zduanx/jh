"""
Test suite for company settings service (user company settings CRUD).

Tests use separate test database (TEST_DATABASE_URL) with:
- Automatic Alembic migrations (schema always in sync)
- Transaction rollback for isolation (test_db fixture)
- Fixed test user from db_test_utils (avoids creating users per test)
- Optional persistence for inspection (test_db_commit fixture)

Running Tests (from backend/):
    pytest db/__tests__/test_company_settings_service.py -v                         # All tests
    pytest db/__tests__/test_company_settings_service.py::TestCreateSetting -v      # One class
    pytest db/__tests__/test_company_settings_service.py::TestCreateSetting::test_create_minimal -v  # One test
    pytest db/__tests__/test_company_settings_service.py -v -s                      # With print output
    pytest db/__tests__/ -v                                                         # All db tests
"""
import pytest
import time
from db.user_service import create_user
from db.company_settings_service import (
    get_user_settings,
    get_setting_by_id,
    get_setting_by_company,
    create_setting,
    update_setting,
    upsert_setting,
    delete_setting,
    get_enabled_settings,
)
from extractors.config import TitleFilters
from db.__tests__.db_test_utils import unique_email


class TestCreateSetting:
    """
    Test setting creation.

    Run: pytest db/__tests__/test_ingestion_service.py::TestCreateSetting -v
    """

    def test_create_minimal(self, test_db, test_user):
        """Create setting with minimal fields."""
        setting = create_setting(
            db=test_db,
            user_id=test_user.user_id,
            company_name="anthropic"
        )

        assert setting.id is not None
        assert setting.user_id == test_user.user_id
        assert setting.company_name == "anthropic"
        assert setting.title_filters == {"include": None, "exclude": []}
        assert setting.is_enabled is True
        assert setting.created_at is not None
        assert setting.updated_at is not None

    def test_create_with_filters(self, test_db, test_user):
        """Create setting with title filters."""
        filters = {"include": ["engineer"], "exclude": ["senior", "intern"]}

        setting = create_setting(
            db=test_db,
            user_id=test_user.user_id,
            company_name="openai",
            title_filters=filters,
            is_enabled=True
        )

        assert setting.title_filters == filters
        assert setting.title_filters["include"] == ["engineer"]
        assert setting.title_filters["exclude"] == ["senior", "intern"]

    def test_create_disabled(self, test_db, test_user):
        """Create setting in disabled state."""
        setting = create_setting(
            db=test_db,
            user_id=test_user.user_id,
            company_name="amazon",
            is_enabled=False
        )

        assert setting.is_enabled is False

    def test_create_duplicate_fails(self, test_db, test_user):
        """Creating duplicate user+company fails."""
        create_setting(test_db, test_user.user_id, "google")

        with pytest.raises(Exception):  # IntegrityError
            create_setting(test_db, test_user.user_id, "google")
            test_db.commit()


class TestGetSettings:
    """
    Test setting retrieval.

    Run: pytest db/__tests__/test_ingestion_service.py::TestGetSettings -v
    """

    def test_get_user_settings_empty(self, test_db, test_user):
        """Get settings for user with none configured."""
        settings = get_user_settings(test_db, test_user.user_id)
        assert settings == []

    def test_get_user_settings_multiple(self, test_db, test_user):
        """Get all settings for a user."""
        create_setting(test_db, test_user.user_id, "anthropic")
        create_setting(test_db, test_user.user_id, "openai")
        create_setting(test_db, test_user.user_id, "google")

        settings = get_user_settings(test_db, test_user.user_id)

        assert len(settings) == 3
        company_names = {s.company_name for s in settings}
        assert company_names == {"anthropic", "openai", "google"}

    def test_get_setting_by_id(self, test_db, test_user):
        """Get setting by ID."""
        created = create_setting(test_db, test_user.user_id, "meta")

        found = get_setting_by_id(test_db, created.id)

        assert found is not None
        assert found.id == created.id
        assert found.company_name == "meta"

    def test_get_setting_by_id_not_found(self, test_db):
        """Get non-existent setting returns None."""
        found = get_setting_by_id(test_db, 999999)
        assert found is None

    def test_get_setting_by_company(self, test_db, test_user):
        """Get setting by user+company combination."""
        create_setting(test_db, test_user.user_id, "tiktok")

        found = get_setting_by_company(test_db, test_user.user_id, "tiktok")

        assert found is not None
        assert found.company_name == "tiktok"

    def test_get_setting_by_company_not_found(self, test_db, test_user):
        """Get non-existent user+company returns None."""
        found = get_setting_by_company(test_db, test_user.user_id, "nonexistent")
        assert found is None


class TestUpdateSetting:
    """
    Test setting updates.

    Run: pytest db/__tests__/test_ingestion_service.py::TestUpdateSetting -v
    """

    def test_update_filters(self, test_db, test_user):
        """Update title filters."""
        setting = create_setting(
            test_db, test_user.user_id, "anthropic",
            title_filters={"include": ["old"]}
        )
        original_updated = setting.updated_at

        time.sleep(0.01)  # Ensure different timestamp

        updated = update_setting(
            test_db, setting.id,
            title_filters={"include": ["new"], "exclude": ["intern"]}
        )

        assert updated.title_filters == {"include": ["new"], "exclude": ["intern"]}
        assert updated.updated_at > original_updated

    def test_update_enabled_state(self, test_db, test_user):
        """Toggle enabled state."""
        setting = create_setting(test_db, test_user.user_id, "openai", is_enabled=True)

        updated = update_setting(test_db, setting.id, is_enabled=False)

        assert updated.is_enabled is False

    def test_update_nonexistent(self, test_db):
        """Update non-existent setting returns None."""
        result = update_setting(test_db, 999999, title_filters={})
        assert result is None


class TestUpsertSetting:
    """
    Test upsert (create or update) operations.

    Run: pytest db/__tests__/test_ingestion_service.py::TestUpsertSetting -v
    """

    def test_upsert_creates_new(self, test_db, test_user):
        """Upsert creates when setting doesn't exist."""
        setting = upsert_setting(
            test_db, test_user.user_id, "anthropic",
            title_filters={"include": ["engineer"]}
        )

        assert setting.id is not None
        assert setting.company_name == "anthropic"
        assert setting.title_filters == {"include": ["engineer"], "exclude": []}

    def test_upsert_updates_existing(self, test_db, test_user):
        """Upsert updates when setting exists."""
        # Create initial
        original = create_setting(
            test_db, test_user.user_id, "openai",
            title_filters={"include": ["original"]}
        )
        original_id = original.id

        # Upsert should update
        updated = upsert_setting(
            test_db, test_user.user_id, "openai",
            title_filters={"include": ["updated"]},
            is_enabled=False
        )

        assert updated.id == original_id  # Same record
        assert updated.title_filters == {"include": ["updated"], "exclude": []}
        assert updated.is_enabled is False


class TestDeleteSetting:
    """
    Test setting deletion.

    Run: pytest db/__tests__/test_ingestion_service.py::TestDeleteSetting -v
    """

    def test_delete_own_setting(self, test_db, test_user):
        """Delete own setting succeeds."""
        setting = create_setting(test_db, test_user.user_id, "google")

        result = delete_setting(test_db, setting.id, test_user.user_id)

        assert result is True
        assert get_setting_by_id(test_db, setting.id) is None

    def test_delete_nonexistent(self, test_db, test_user):
        """Delete non-existent setting returns False."""
        result = delete_setting(test_db, 999999, test_user.user_id)
        assert result is False

    def test_delete_other_user_setting(self, test_db, test_user):
        """Cannot delete another user's setting."""
        setting = create_setting(test_db, test_user.user_id, "meta")

        # Try to delete with wrong user_id
        result = delete_setting(test_db, setting.id, user_id=999999)

        assert result is False
        assert get_setting_by_id(test_db, setting.id) is not None  # Still exists


class TestGetEnabledSettings:
    """
    Test filtered retrieval of enabled settings.

    Run: pytest db/__tests__/test_ingestion_service.py::TestGetEnabledSettings -v
    """

    def test_get_enabled_only(self, test_db, test_user):
        """Get only enabled settings."""
        create_setting(test_db, test_user.user_id, "anthropic", is_enabled=True)
        create_setting(test_db, test_user.user_id, "openai", is_enabled=False)
        create_setting(test_db, test_user.user_id, "google", is_enabled=True)

        enabled = get_enabled_settings(test_db, test_user.user_id)

        assert len(enabled) == 2
        company_names = {s.company_name for s in enabled}
        assert company_names == {"anthropic", "google"}


class TestCascadeDelete:
    """
    Test cascade behavior when user is deleted.

    Run: pytest db/__tests__/test_ingestion_service.py::TestCascadeDelete -v
    """

    def test_settings_deleted_with_user(self, test_db):
        """Settings are deleted when user is deleted (CASCADE)."""
        # Create user and settings
        email = unique_email("cascade_test")
        user = create_user(test_db, email, "Cascade Test")
        create_setting(test_db, user.user_id, "anthropic")
        create_setting(test_db, user.user_id, "openai")

        # Verify settings exist
        settings = get_user_settings(test_db, user.user_id)
        assert len(settings) == 2

        # Delete user
        test_db.delete(user)
        test_db.commit()

        # Settings should be gone (CASCADE)
        settings = get_user_settings(test_db, user.user_id)
        assert len(settings) == 0


class TestTitleFiltersValidation:
    """
    Test TitleFilters.from_dict validation.

    Run: pytest db/__tests__/test_company_settings_service.py::TestTitleFiltersValidation -v
    """

    def test_from_dict_none(self):
        """None returns default TitleFilters."""
        result = TitleFilters.from_dict(None)
        assert result.include is None
        assert result.exclude == []

    def test_from_dict_empty(self):
        """Empty dict returns default TitleFilters."""
        result = TitleFilters.from_dict({})
        assert result.include is None
        assert result.exclude == []

    def test_from_dict_include_only(self):
        """Valid include list."""
        result = TitleFilters.from_dict({"include": ["engineer", "developer"]})
        assert result.include == ["engineer", "developer"]
        assert result.exclude == []

    def test_from_dict_exclude_only(self):
        """Valid exclude list."""
        result = TitleFilters.from_dict({"exclude": ["senior", "intern"]})
        assert result.include is None
        assert result.exclude == ["senior", "intern"]

    def test_from_dict_both(self):
        """Valid include and exclude."""
        result = TitleFilters.from_dict({
            "include": ["engineer"],
            "exclude": ["senior", "intern"]
        })
        assert result.include == ["engineer"]
        assert result.exclude == ["senior", "intern"]

    def test_from_dict_include_null(self):
        """Explicit null include is valid."""
        result = TitleFilters.from_dict({"include": None, "exclude": ["intern"]})
        assert result.include is None
        assert result.exclude == ["intern"]

    def test_to_dict_roundtrip(self):
        """to_dict produces valid dict structure."""
        original = TitleFilters(include=["engineer"], exclude=["intern"])
        as_dict = original.to_dict()
        restored = TitleFilters.from_dict(as_dict)
        assert restored.include == original.include
        assert restored.exclude == original.exclude

    def test_from_dict_invalid_not_dict(self):
        """Non-dict raises ValueError."""
        with pytest.raises(ValueError, match="must be a dict"):
            TitleFilters.from_dict("invalid")

    def test_from_dict_invalid_include_not_list(self):
        """Non-list include raises ValueError."""
        with pytest.raises(ValueError, match="include must be a list"):
            TitleFilters.from_dict({"include": "engineer"})

    def test_from_dict_invalid_include_items(self):
        """Non-string include items raise ValueError."""
        with pytest.raises(ValueError, match="include items must be strings"):
            TitleFilters.from_dict({"include": [123, "engineer"]})

    def test_from_dict_invalid_exclude_not_list(self):
        """Non-list exclude raises ValueError."""
        with pytest.raises(ValueError, match="exclude must be a list"):
            TitleFilters.from_dict({"exclude": "senior"})

    def test_from_dict_invalid_exclude_items(self):
        """Non-string exclude items raise ValueError."""
        with pytest.raises(ValueError, match="exclude items must be strings"):
            TitleFilters.from_dict({"exclude": [None, "intern"]})

    def test_create_with_invalid_filters_raises(self, test_db, test_user):
        """create_setting raises ValueError for invalid filters."""
        with pytest.raises(ValueError):
            create_setting(
                test_db, test_user.user_id, "anthropic",
                title_filters={"include": "not-a-list"}
            )
