# pytest Quick Reference

**Date:** 2024-12-17
**Topic:** Common pytest commands for running tests

---

## Running All Tests

### All tests in project
```bash
cd /Users/duan/coding/jh/backend
pytest -v
```

### All tests in specific file
```bash
pytest tests/test_user_service.py -v
```

---

## Running Specific Tests

### Run specific test class
```bash
pytest tests/test_user_service.py::TestCreateUser -v
```

### Run specific test function
```bash
pytest tests/test_user_service.py::TestCreateUser::test_create_user_minimal -v
```

---

## Useful Flags

### Verbose output (show test names)
```bash
pytest -v
```

### Show print statements
```bash
pytest -v -s
```

### Run tests matching keyword
```bash
pytest -k "create" -v  # Runs all tests with "create" in name
pytest -k "TestCreateUser" -v  # Runs all TestCreateUser tests
```

### Stop at first failure
```bash
pytest -x
```

### Show local variables on failure
```bash
pytest -l
```

### Run last failed tests only
```bash
pytest --lf
```

### Run in parallel (faster)
```bash
pip install pytest-xdist
pytest -n 4  # Run with 4 workers
```

---

## Common Combinations

### Verbose with print output
```bash
pytest tests/test_user_service.py -v -s
```

### Run specific test with output
```bash
pytest tests/test_user_service.py::TestManualInspection::test_create_inspection_users -v -s
```

### Run all tests, stop at first failure, show variables
```bash
pytest -x -l -v
```

---

## Test File Structure

```
tests/test_user_service.py
├── TestCreateUser                    # Class
│   ├── test_create_user_minimal      # Test function
│   ├── test_create_user_with_picture
│   └── test_create_duplicate_email_fails
├── TestGetUser
│   ├── test_get_user_by_email_exists
│   ├── test_get_user_by_email_not_exists
│   ├── test_get_user_by_id_exists
│   └── test_get_user_by_id_not_exists
├── TestUpdateUser
│   ├── test_update_user_profile
│   └── test_update_nonexistent_user
├── TestGetOrCreateUser
│   ├── test_get_or_create_new_user
│   ├── test_get_or_create_existing_user
│   └── test_get_or_create_updates_last_login
└── TestManualInspection
    ├── test_create_inspection_users
    └── test_auth_flow_simulation
```

---

## Examples

### Example 1: Run all tests
```bash
cd backend
pytest -v

# Output:
# tests/test_user_service.py::TestCreateUser::test_create_user_minimal PASSED [  7%]
# tests/test_user_service.py::TestCreateUser::test_create_user_with_picture PASSED [ 14%]
# ...
# ======================== 14 passed in 2.78s =========================
```

### Example 2: Run one class
```bash
pytest tests/test_user_service.py::TestCreateUser -v

# Output:
# tests/test_user_service.py::TestCreateUser::test_create_user_minimal PASSED [ 33%]
# tests/test_user_service.py::TestCreateUser::test_create_user_with_picture PASSED [ 66%]
# tests/test_user_service.py::TestCreateUser::test_create_duplicate_email_fails PASSED [100%]
# ======================== 3 passed in 1.52s =========================
```

### Example 3: Run one test
```bash
pytest tests/test_user_service.py::TestCreateUser::test_create_user_minimal -v

# Output:
# tests/test_user_service.py::TestCreateUser::test_create_user_minimal PASSED [100%]
# ======================== 1 passed in 1.82s =========================
```

### Example 4: Run inspection tests with output
```bash
pytest tests/test_user_service.py::TestManualInspection -v -s

# Output:
# tests/test_user_service.py::TestManualInspection::test_create_inspection_users
# ✓ Created persistent user 1: ID=14, email=inspect_persistent1_1765937403650@example.com
# ✓ Created persistent user 2: ID=15, email=inspect_persistent2_1765937403650@example.com
# PASSED
# ...
```

---

## Debugging Failed Tests

### 1. Run failed test with verbose output
```bash
pytest tests/test_user_service.py::TestCreateUser::test_create_user_minimal -v -l
```

### 2. Add print statements to test
```python
def test_create_user_minimal(self, test_db):
    email = unique_email("minimal")
    print(f"Testing with email: {email}")  # Will show with -s flag

    user = create_user(test_db, email, "Test User")
    print(f"Created user: {user.user_id}")

    assert user.user_id is not None
```

### 3. Run with output flag
```bash
pytest tests/test_user_service.py::TestCreateUser::test_create_user_minimal -v -s
```

---

## Common Patterns

### Run all creation tests
```bash
pytest -k "create" -v
```

### Run all get tests
```bash
pytest -k "get" -v
```

### Run all update tests
```bash
pytest -k "update" -v
```

### Run everything except manual inspection
```bash
pytest -k "not inspection" -v
```

---

## Tips

1. **Always use `-v` flag** - Shows test names and progress
2. **Use `-s` for debugging** - Shows print statements
3. **Use `-k` for filtering** - Run subset of tests by name
4. **Run specific tests during development** - Faster feedback loop
5. **Run all tests before committing** - Ensure nothing broke

---

## Quick Copy-Paste Commands

```bash
# Most common: Run all tests with verbose output
pytest -v

# Debug a specific test
pytest tests/test_user_service.py::TestCreateUser::test_create_user_minimal -v -s

# Run all tests in a class
pytest tests/test_user_service.py::TestCreateUser -v

# Run all tests matching keyword
pytest -k "create" -v

# Stop at first failure
pytest -x -v
```

---

## Summary

✅ **All tests**: `pytest -v`
✅ **Specific file**: `pytest tests/test_user_service.py -v`
✅ **Specific class**: `pytest tests/test_user_service.py::TestCreateUser -v`
✅ **Specific test**: `pytest tests/test_user_service.py::TestCreateUser::test_create_user_minimal -v`
✅ **With output**: Add `-s` flag
✅ **Match keyword**: `pytest -k "keyword" -v`

All commands are now documented in the test file docstrings!

---

## Fixtures

Fixtures provide reusable test dependencies. Pytest injects them automatically by matching parameter names.

### Defining Fixtures

```python
@pytest.fixture
def mock_user():
    """Fixture providing a test user."""
    return {"user_id": 1, "email": "test@example.com"}

@pytest.fixture
def authenticated_client():
    """Fixture providing an authenticated test client."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client  # yield allows cleanup after test
    app.dependency_overrides.clear()  # cleanup runs after test
```

### Using Fixtures

```python
# Single fixture - matched by parameter name
def test_something(mock_user):
    assert mock_user["email"] == "test@example.com"

# Multiple fixtures - all injected automatically
def test_with_multiple_fixtures(authenticated_client, mock_user, test_db):
    # All three fixtures are available
    response = authenticated_client.get("/api/user")
    assert response.status_code == 200
```

### Fixture Scopes

```python
@pytest.fixture(scope="function")  # Default: new instance per test
@pytest.fixture(scope="class")     # Shared within test class
@pytest.fixture(scope="module")    # Shared within test file
@pytest.fixture(scope="session")   # Shared across entire test run
```

---

## Mocking with @patch

`@patch` temporarily replaces objects with mocks during tests.

### Basic Usage

```python
from unittest.mock import patch, MagicMock, AsyncMock

@patch("api.ingestion_routes.get_enabled_settings")
def test_example(mock_get_settings):
    mock_get_settings.return_value = [{"company": "google"}]
    # Now get_enabled_settings() returns the mock data
```

### How @patch Works

The string path `"api.ingestion_routes.get_enabled_settings"` means:
- In the `api.ingestion_routes` module
- Replace `get_enabled_settings` with a mock

### Multiple Patches

Decorators stack **bottom-up** - the closest patch becomes the first mock parameter:

```python
@patch("module.function_a")      # → mock_a (second param)
@patch("module.function_b")      # → mock_b (first param after self)
def test_example(self, mock_b, mock_a, my_fixture):
    pass
```

**Parameter order:**
| Position | Source | Description |
|----------|--------|-------------|
| 1 | `self` | Class instance (if class method) |
| 2 | Bottom `@patch` | First mock (closest to function) |
| 3 | Top `@patch` | Second mock |
| 4+ | Fixtures | Pytest fixtures (any order) |

### Mocking Return Values

```python
@patch("module.some_function")
def test_example(mock_fn):
    # Simple return value
    mock_fn.return_value = {"status": "success"}

    # Different returns per call
    mock_fn.side_effect = [result1, result2, result3]

    # Raise exception
    mock_fn.side_effect = ValueError("error message")
```

### Mocking Async Functions

Use `AsyncMock` for async functions:

```python
from unittest.mock import AsyncMock

@patch("module.async_function")
def test_async(mock_fn):
    mock_fn.return_value = AsyncMock(return_value={"data": "value"})

    # Or directly
    mock_extractor = MagicMock()
    mock_extractor.fetch_data = AsyncMock(return_value=result)
```

### Dynamic Side Effects

```python
def get_extractor_side_effect(company_name, config=None):
    """Return different mocks based on input."""
    mock = MagicMock()
    if company_name == "google":
        mock.fetch.return_value = google_data
    elif company_name == "amazon":
        mock.fetch.side_effect = TimeoutError()
    return mock

mock_get_extractor.side_effect = get_extractor_side_effect
```

---

## FastAPI Dependency Override

For FastAPI endpoints, use `dependency_overrides` instead of `@patch`:

```python
from main import app
from auth.dependencies import get_current_user

# Define override function
async def override_get_current_user():
    return {"user_id": 1, "email": "test@example.com"}

# Apply override
app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)

# Clean up after test
app.dependency_overrides.clear()
```

**Why use this over @patch?**
- FastAPI dependencies use its own injection system
- `@patch` on the dependency function doesn't work with `Depends()`
- `dependency_overrides` is the official FastAPI testing pattern

---

## Complete Example

```python
"""Integration test with fixtures and mocks."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from main import app
from auth.dependencies import get_current_user

MOCK_USER = {"user_id": 1, "email": "test@example.com"}

async def override_get_current_user():
    return MOCK_USER

@pytest.fixture
def authenticated_client():
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def mock_settings():
    setting = MagicMock()
    setting.company_name = "google"
    setting.title_filters = {}
    return [setting]

class TestDryRun:
    @patch("api.ingestion_routes.get_enabled_settings")
    @patch("api.ingestion_routes.get_extractor")
    def test_success(
        self,
        mock_get_extractor,      # from @patch (bottom)
        mock_get_settings,       # from @patch (top)
        authenticated_client,    # pytest fixture
        mock_settings,           # pytest fixture
    ):
        # Configure mocks
        mock_get_settings.return_value = mock_settings

        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(return_value={"count": 10})
        mock_get_extractor.return_value = mock_extractor

        # Make request
        response = authenticated_client.post("/api/dry-run")

        # Assert
        assert response.status_code == 200
        assert response.json()["google"]["count"] == 10
```

---

## When to Use What

| Scenario | Approach |
|----------|----------|
| FastAPI auth dependency | `app.dependency_overrides` |
| Database session | Fixture with `yield` for cleanup |
| External API calls | `@patch` with `AsyncMock` |
| Service layer functions | `@patch` on the import path |
| Reusable test data | Fixtures |
| One-off mock data | Inline in test |
