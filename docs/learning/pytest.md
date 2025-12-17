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
