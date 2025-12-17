# Testing Guide

Complete guide for setting up and running tests with pytest and PostgreSQL.

---

## Quick Start (5 minutes)

### 1. Create Test Database in Neon

**Option A: Neon Console (Recommended)**
1. Go to [Neon Console](https://console.neon.tech)
2. Select your project
3. Go to **Databases** tab
4. Click **"New Database"**
5. Name: `neondb_test`
6. Copy connection string

**Option B: Use Development Branch**
If you already have a Neon development branch, you can use that instead of creating a separate test database.

### 2. Add to .env

Add to `/Users/duan/coding/jh/backend/.env`:

```bash
# Test Database Configuration
TEST_DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-your-endpoint-pooler.c-3.us-east-1.aws.neon.tech/neondb_test?sslmode=require
```

**Tip:** Change `/neondb` to `/neondb_test` in your existing `DATABASE_URL`.

### 3. Run Tests

```bash
cd /Users/duan/coding/jh/backend
pytest -v
```

**Expected output:**
```
✓ Connected to test database
✓ Running Alembic migrations...
✓ Test database schema is up to date

tests/test_user_service.py::TestCreateUser::test_create_user_minimal PASSED
...
======================== 14 passed in 2.78s =========================
```

---

## How It Works

### Test Database Architecture

```
Neon Project: Job Hunter
├── neondb (production)
│   └── Used by: Production FastAPI app
├── neondb (development)
│   └── Used by: Local development
└── neondb_test (testing)
    └── Used by: pytest test suite
```

**Key Point:** Same Alembic migrations applied to all databases.

### Automatic Schema Sync

**1. Test Startup (Once per pytest session)**
```python
# tests/conftest.py - test_engine fixture
test_db_url = os.getenv("TEST_DATABASE_URL")
engine = create_engine(test_db_url)

# Apply Alembic migrations
alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
command.upgrade(alembic_cfg, "head")
```

- Connects to test database
- Runs `alembic upgrade head`
- Ensures test schema matches latest migrations

**2. Each Test (Isolated transaction)**
```python
# tests/conftest.py - test_db fixture
connection = test_engine.connect()
transaction = connection.begin()
db = TestSessionLocal()

yield db  # Test runs here

transaction.rollback()  # Rollback all changes
```

- Test creates/modifies data in transaction
- After test finishes, rollback to clean state
- No data pollution between tests

**3. Manual Inspection (Optional)**
```python
def test_create_inspection_users(test_db_commit):
    user = create_user(test_db_commit, "inspect@example.com", "Inspect Me")
    test_db_commit.commit()  # Persists to database
```

- Use `test_db_commit` fixture to persist data
- Useful for debugging and manual inspection

---

## Migration Workflow

When you create a new migration:

```bash
# 1. Create migration
alembic revision --autogenerate -m "add jobs table"
# Creates: alembic/versions/002_add_jobs_table.py

# 2. Apply to production
alembic upgrade head
# Updates: neondb (production)

# 3. Run tests (automatic)
pytest
# Auto-applies migration to: neondb_test
```

**One migration file, applied to all databases automatically.**

---

## Running Tests

See [pytest.md](../learning/pytest.md) for detailed pytest commands.

### Common Commands

```bash
# All tests
pytest -v

# Specific file
pytest tests/test_user_service.py -v

# Specific class
pytest tests/test_user_service.py::TestCreateUser -v

# Specific test
pytest tests/test_user_service.py::TestCreateUser::test_create_user_minimal -v

# With print output
pytest -v -s

# Stop at first failure
pytest -x -v
```

---

## Database Inspection

### Connect to Test Database

```bash
# Get connection string from .env TEST_DATABASE_URL
psql 'postgresql://neondb_owner:YOUR_PASSWORD@ep-your-endpoint/neondb_test?sslmode=require'
```

### Useful SQL Commands

```sql
-- List all tables
\dt

-- Describe users table
\d users

-- See test data
SELECT * FROM users WHERE email LIKE 'inspect%';

-- Check migration version
SELECT * FROM alembic_version;

-- Count test users
SELECT COUNT(*) FROM users WHERE email LIKE '%@example.com';

-- Exit
\q
```

---

## Database Maintenance

### Why Data Persists

✅ **Benefits:**
- Debug failed tests by inspecting database state
- Understand what data tests created
- Verify constraints and triggers
- Learn SQL with real test data

⚠️ **Trade-off:**
- Database grows over time (very slowly)

### Growth Rate

```
15 tests × 2 users = 30 users per run
30 users × 1KB = ~30KB per test run

Daily dev: 10 runs = 300KB/day
Monthly: ~8MB/month
Yearly: ~96MB/year

Neon free tier: 3GB
Years until full: ~31 years
```

**Conclusion:** Growth is negligible. Clean up only when convenient.

### When to Clean Up

| Frequency | Trigger | Reason |
|-----------|---------|--------|
| Never | Default | Growth is minimal |
| Monthly | Optional | Keep database tidy |
| Quarterly | If >100MB | Prevent unnecessary growth |
| As needed | Before production deploy | Fresh slate |

### Cleanup Commands

**Option 1: Truncate All (Fastest)**
```sql
-- Removes all data, keeps schema, resets IDs
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

-- Verify
SELECT COUNT(*) FROM users;  -- Should be 0
```

**Option 2: Delete Old Data (Selective)**
```sql
-- Delete test users older than 30 days
DELETE FROM users
WHERE email LIKE '%@example.com'
  AND created_at < NOW() - INTERVAL '30 days';
```

**Option 3: Delete by Pattern**
```sql
-- Delete inspection test users
DELETE FROM users WHERE email LIKE 'inspect_%@example.com';

-- Delete auth flow test users
DELETE FROM users WHERE email LIKE 'authflow_%@example.com';
```

### Monitor Database Size

```sql
-- Database size
SELECT pg_size_pretty(pg_database_size('neondb_test'));

-- Table sizes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;

-- Row counts
SELECT COUNT(*) AS total_users FROM users;
SELECT COUNT(*) AS test_users FROM users WHERE email LIKE '%@example.com';
```

**Size Guidelines:**
- < 1,000 rows (~1MB): Normal
- 1,000 - 10,000 rows (1-10MB): Fine
- 10,000 - 100,000 rows (10-100MB): Consider cleanup
- > 100,000 rows (>100MB): Time to clean up

---

## Timestamp-Based Email Strategy

Tests use `unique_email()` to avoid collisions:

```python
def unique_email(prefix: str = "test") -> str:
    """Generate unique email using timestamp."""
    timestamp = int(time.time() * 1000)
    return f"{prefix}_{timestamp}@example.com"

# Examples:
# test_1702847123456@example.com
# inspect_1702847123789@example.com
# authflow_1702847124012@example.com
```

**Benefits:**
- Always unique (timestamp in milliseconds)
- No collisions even with persistent data
- Easy to identify test data by prefix
- Can query by time range
- Sortable by creation order

**Query recent test data:**
```sql
-- Latest 10 test users
SELECT * FROM users
WHERE email LIKE '%@example.com'
ORDER BY created_at DESC
LIMIT 10;

-- Last hour
SELECT * FROM users
WHERE email LIKE '%@example.com'
  AND created_at > NOW() - INTERVAL '1 hour';
```

---

## Best Practices

### 1. Use test_db for most tests (rollback)
```python
def test_create_user(test_db):
    user = create_user(test_db, "test@example.com", "Test")
    assert user.user_id is not None
    # Automatically rolled back
```

### 2. Use test_db_commit for inspection
```python
def test_complex_scenario(test_db_commit):
    user = create_user(test_db_commit, "inspect@example.com", "Inspect")
    test_db_commit.commit()  # Data persists for manual inspection
```

### 3. Use descriptive email prefixes
```python
# Good - easy to identify
email = unique_email("authflow")  # authflow_1702847123456@example.com
email = unique_email("inspect")   # inspect_1702847123456@example.com

# Avoid generic prefixes
email = unique_email("test")      # Hard to filter later
```

### 4. Clean up before major milestones
```bash
# Before production deploy
psql '...' -c "TRUNCATE TABLE users RESTART IDENTITY CASCADE;"
pytest -v  # Verify everything works
```

### 5. Never run tests against production
- ❌ Never set `TEST_DATABASE_URL = DATABASE_URL`
- ❌ Never modify conftest.py to use production DB
- ✅ Always use separate test database

---

## Troubleshooting

### TEST_DATABASE_URL not found
**Fix:** Add `TEST_DATABASE_URL=...` to `backend/.env`

### Failed to connect to test database
**Check:**
1. Verify `neondb_test` exists in Neon console
2. Copy connection string from Neon
3. Ensure database name is `neondb_test` not `neondb`

### Relation "users" does not exist
**Fix:** Migration didn't run
```bash
# Verify migration file exists
ls alembic/versions/
# Should see: *_initial_users_table.py
```

### Tests pass but data not visible
**Expected!** Most tests use `test_db` which rolls back.

**To persist:** Use `test_db_commit` fixture:
```python
def test_my_data(test_db_commit):
    user = create_user(test_db_commit, "persist@example.com", "Persist")
    test_db_commit.commit()
```

### Database growing too fast
**Check for runaway tests:**
```sql
SELECT
    SUBSTRING(email FROM '^[^_]+') AS prefix,
    COUNT(*) AS count
FROM users
WHERE email LIKE '%@example.com'
GROUP BY prefix
ORDER BY count DESC;
```

If one prefix has 1000s of rows, that test might be in a loop.

---

## Summary

✅ **Setup:** Separate test database with automatic Alembic migrations
✅ **Isolation:** Each test runs in rollback transaction
✅ **Inspection:** Optional data persistence with `test_db_commit`
✅ **Maintenance:** Growth is minimal (~96MB/year), clean up quarterly
✅ **Commands:** See [pytest.md](../learning/pytest.md)

Test infrastructure is production-ready!
