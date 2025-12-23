"""
Integration tests for dry-run endpoint.

Tests the endpoint logic with mocked dependencies:
- get_current_user: overridden via FastAPI dependency injection
- get_enabled_settings: mocked to return test company settings
- extract_source_urls_metadata: mocked to return test job data

This validates:
- Parallel execution with asyncio.gather
- Per-company error isolation
- Response structure and status codes
- Error mapping for various exception types

Run: python3 -m pytest api/__tests__/test_dry_run.py -v
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import httpx

from main import app
from auth.dependencies import get_current_user


# Mock user for authenticated requests
MOCK_USER = {"user_id": 1, "email": "test@example.com", "name": "Test User"}


async def override_get_current_user():
    """Override dependency to return mock user."""
    return MOCK_USER


@pytest.fixture
def authenticated_client():
    """Create test client with auth dependency overridden."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    """Create test client without auth override."""
    app.dependency_overrides.clear()
    return TestClient(app)


def make_mock_setting(company_name: str, title_filters: dict = None):
    """Create a mock company setting object."""
    setting = MagicMock()
    setting.company_name = company_name
    setting.title_filters = title_filters or {}
    return setting


def make_mock_extractor_result(
    total_count: int = 10,
    filtered_count: int = 2,
    urls_count: int = 8,
    included_jobs: list = None,
    excluded_jobs: list = None,
):
    """Create a mock extractor result."""
    return {
        "total_count": total_count,
        "filtered_count": filtered_count,
        "urls_count": urls_count,
        "included_jobs": included_jobs or [
            {"id": "1", "title": "Software Engineer", "location": "NYC", "url": "https://example.com/1"},
            {"id": "2", "title": "Senior Engineer", "location": "SF", "url": "https://example.com/2"},
        ],
        "excluded_jobs": excluded_jobs or [
            {"id": "3", "title": "Intern", "location": "Remote", "url": "https://example.com/3"},
        ],
    }


class TestDryRunEndpoint:
    """Tests for POST /api/ingestion/dry-run endpoint."""

    def test_dry_run_no_auth_returns_401(self, unauthenticated_client):
        """Request without auth token should return 401."""
        response = unauthenticated_client.post("/api/ingestion/dry-run")
        assert response.status_code == 401

    @patch("api.ingestion_routes.get_enabled_settings")
    def test_dry_run_no_enabled_companies_returns_400(
        self, mock_get_settings, authenticated_client
    ):
        """Should return 400 when no companies are enabled."""
        mock_get_settings.return_value = []

        response = authenticated_client.post("/api/ingestion/dry-run")

        assert response.status_code == 400
        assert "No enabled companies" in response.json()["detail"]

    @patch("api.ingestion_routes.get_enabled_settings")
    @patch("api.ingestion_routes.get_extractor")
    def test_dry_run_single_company_success(
        self, mock_get_extractor, mock_get_settings, authenticated_client
    ):
        """Should return success result for a single company."""
        mock_get_settings.return_value = [make_mock_setting("google")]

        # Mock extractor
        mock_extractor = MagicMock()
        mock_extractor.extract_source_urls_metadata = AsyncMock(
            return_value=make_mock_extractor_result()
        )
        mock_get_extractor.return_value = mock_extractor

        response = authenticated_client.post("/api/ingestion/dry-run")

        assert response.status_code == 200
        data = response.json()

        assert "google" in data
        assert data["google"]["status"] == "success"
        assert data["google"]["total_count"] == 10
        assert data["google"]["filtered_count"] == 2
        assert data["google"]["urls_count"] == 8
        assert len(data["google"]["included_jobs"]) == 2
        assert len(data["google"]["excluded_jobs"]) == 1

    @patch("api.ingestion_routes.get_enabled_settings")
    @patch("api.ingestion_routes.get_extractor")
    def test_dry_run_multiple_companies_parallel(
        self, mock_get_extractor, mock_get_settings, authenticated_client
    ):
        """Should run multiple companies in parallel and return all results."""
        mock_get_settings.return_value = [
            make_mock_setting("google"),
            make_mock_setting("amazon"),
            make_mock_setting("anthropic"),
        ]

        # Each company gets different result
        results = {
            "google": make_mock_extractor_result(total_count=100, urls_count=95),
            "amazon": make_mock_extractor_result(total_count=50, urls_count=48),
            "anthropic": make_mock_extractor_result(total_count=20, urls_count=18),
        }

        def get_extractor_side_effect(company_name, config=None):
            mock_extractor = MagicMock()
            mock_extractor.extract_source_urls_metadata = AsyncMock(
                return_value=results[company_name]
            )
            return mock_extractor

        mock_get_extractor.side_effect = get_extractor_side_effect

        response = authenticated_client.post("/api/ingestion/dry-run")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        assert data["google"]["urls_count"] == 95
        assert data["amazon"]["urls_count"] == 48
        assert data["anthropic"]["urls_count"] == 18

    @patch("api.ingestion_routes.get_enabled_settings")
    @patch("api.ingestion_routes.get_extractor")
    def test_dry_run_partial_failure(
        self, mock_get_extractor, mock_get_settings, authenticated_client
    ):
        """One company failing should not block others."""
        mock_get_settings.return_value = [
            make_mock_setting("google"),
            make_mock_setting("amazon"),  # This one will fail
        ]

        def get_extractor_side_effect(company_name, config=None):
            mock_extractor = MagicMock()
            if company_name == "amazon":
                mock_extractor.extract_source_urls_metadata = AsyncMock(
                    side_effect=httpx.TimeoutException("Connection timed out")
                )
            else:
                mock_extractor.extract_source_urls_metadata = AsyncMock(
                    return_value=make_mock_extractor_result()
                )
            return mock_extractor

        mock_get_extractor.side_effect = get_extractor_side_effect

        response = authenticated_client.post("/api/ingestion/dry-run")

        assert response.status_code == 200
        data = response.json()

        # Google should succeed
        assert data["google"]["status"] == "success"
        assert data["google"]["urls_count"] == 8

        # Amazon should fail gracefully
        assert data["amazon"]["status"] == "error"
        assert "timed out" in data["amazon"]["error_message"]
        assert data["amazon"]["urls_count"] == 0


class TestErrorMapping:
    """Tests for _map_extractor_error function."""

    @patch("api.ingestion_routes.get_enabled_settings")
    @patch("api.ingestion_routes.get_extractor")
    def test_timeout_error_message(
        self, mock_get_extractor, mock_get_settings, authenticated_client
    ):
        """TimeoutException should map to timeout message."""
        mock_get_settings.return_value = [make_mock_setting("google")]

        mock_extractor = MagicMock()
        mock_extractor.extract_source_urls_metadata = AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )
        mock_get_extractor.return_value = mock_extractor

        response = authenticated_client.post("/api/ingestion/dry-run")
        data = response.json()

        assert "timed out" in data["google"]["error_message"]

    @patch("api.ingestion_routes.get_enabled_settings")
    @patch("api.ingestion_routes.get_extractor")
    def test_connect_error_message(
        self, mock_get_extractor, mock_get_settings, authenticated_client
    ):
        """ConnectError should map to connection message."""
        mock_get_settings.return_value = [make_mock_setting("google")]

        mock_extractor = MagicMock()
        mock_extractor.extract_source_urls_metadata = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_get_extractor.return_value = mock_extractor

        response = authenticated_client.post("/api/ingestion/dry-run")
        data = response.json()

        assert "Could not connect" in data["google"]["error_message"]

    @patch("api.ingestion_routes.get_enabled_settings")
    @patch("api.ingestion_routes.get_extractor")
    def test_rate_limit_error_message(
        self, mock_get_extractor, mock_get_settings, authenticated_client
    ):
        """429 status should map to rate limit message."""
        mock_get_settings.return_value = [make_mock_setting("google")]

        # Create mock response for HTTPStatusError
        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_extractor = MagicMock()
        mock_extractor.extract_source_urls_metadata = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "rate limited",
                request=MagicMock(),
                response=mock_response,
            )
        )
        mock_get_extractor.return_value = mock_extractor

        response = authenticated_client.post("/api/ingestion/dry-run")
        data = response.json()

        assert "Rate limited" in data["google"]["error_message"]

    @patch("api.ingestion_routes.get_enabled_settings")
    @patch("api.ingestion_routes.get_extractor")
    def test_key_error_maps_to_format_error(
        self, mock_get_extractor, mock_get_settings, authenticated_client
    ):
        """KeyError should map to unexpected format message."""
        mock_get_settings.return_value = [make_mock_setting("google")]

        mock_extractor = MagicMock()
        mock_extractor.extract_source_urls_metadata = AsyncMock(
            side_effect=KeyError("missing_field")
        )
        mock_get_extractor.return_value = mock_extractor

        response = authenticated_client.post("/api/ingestion/dry-run")
        data = response.json()

        assert "Unexpected response format" in data["google"]["error_message"]
