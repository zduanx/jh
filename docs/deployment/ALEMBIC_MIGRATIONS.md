# Alembic Database Migration Guide

Quick reference for database schema migrations using Alembic.

---

## 🚀 Quick Migration (Most Common)

**Apply pending migrations:**

```bash
cd /Users/duan/coding/jh/backend
alembic upgrade head
```

**Verify migration applied:**

```bash
alembic current
```

Should show the latest migration ID (e.g., `fa5132bfbf71 (head)`).

---

## 🔄 Common Workflows

### Create a New Migration

**After modifying models in `backend/models/`:**

```bash
cd /Users/duan/coding/jh/backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add jobs table"

# Review the generated migration file in backend/alembic/versions/
# Then apply it
alembic upgrade head
```

### Rollback a Migration

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade fa5132bfbf71

# Rollback all migrations
alembic downgrade base
```

### View Migration History

```bash
# Current version
alembic current

# Migration history
alembic history

# Pending migrations
alembic history --verbose
```

---

## 🔍 Verify Database Schema

### Option 1: Check Alembic Version

```bash
cd /Users/duan/coding/jh/backend
alembic current
```

If migration applied successfully, you'll see:
```
fa5132bfbf71 (head)
```

### Option 2: Connect to Neon with psql

**Connect to database:**

```bash
# Use the DATABASE_URL from backend/.env
psql '<your-database-url-from-.env>'
```

**Useful SQL commands:**

```sql
-- List all tables
\dt

-- Describe users table structure
\d users

-- View data (should be empty initially)
SELECT * FROM users;

-- Check Alembic version tracking
SELECT * FROM alembic_version;

-- Exit psql
\q
```

### Option 3: Python Verification Script

Create `backend/verify_db.py`:

```python
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    # Check tables
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """))
    print("Tables:", [row[0] for row in result])

    # Check users table columns
    result = conn.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'users'
        ORDER BY ordinal_position
    """))
    print("\nUsers table schema:")
    for row in result:
        print(f"  {row[0]}: {row[1]} (nullable: {row[2]})")

    # Check Alembic version
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    version = result.scalar()
    print(f"\nAlembic version: {version}")
```

Run it:

```bash
cd /Users/duan/coding/jh/backend
python3 verify_db.py
```

---

## 🆕 First-Time Setup

### 1. Install Dependencies

```bash
cd /Users/duan/coding/jh/backend
pip3 install -r requirements.txt
```

### 2. Ensure DATABASE_URL is Set

Check `backend/.env`:

```bash
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-your-endpoint-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### 3. Apply All Migrations

```bash
alembic upgrade head
```

### 4. Verify

```bash
alembic current
```

---

## 📝 Creating Migrations

### Workflow

1. **Modify models** in `backend/models/user.py` (or create new model files)
2. **Import new models** in `backend/models/__init__.py`
3. **Generate migration**: `alembic revision --autogenerate -m "Description"`
4. **Review migration** in `backend/alembic/versions/`
5. **Apply migration**: `alembic upgrade head`
6. **Verify**: `alembic current`

### Example: Adding a New Column

**1. Update model:**

```python
# backend/models/user.py
class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # NEW COLUMN
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
```

**2. Generate migration:**

```bash
alembic revision --autogenerate -m "Add is_active column to users"
```

**3. Review generated file** in `backend/alembic/versions/xxx_add_is_active_column_to_users.py`

**4. Apply:**

```bash
alembic upgrade head
```

---

## 🐛 Troubleshooting

### Migration Fails with "relation already exists"

The table already exists. Either:
- Skip this migration: `alembic stamp head` (marks as applied without running)
- Drop the table manually and re-run migration

### "Can't locate revision identified by 'xxx'"

Alembic version mismatch. Check:

```bash
# What Alembic thinks is current
alembic current

# What's in the database
psql <connection-string> -c "SELECT * FROM alembic_version"

# Sync them
alembic stamp <version>
```

### Migration Generates Empty Changes

Alembic didn't detect model changes. Ensure:
- Model is imported in `backend/models/__init__.py`
- `target_metadata = Base.metadata` is set in `backend/alembic/env.py`

### Connection Error

Check DATABASE_URL is correct:

```bash
# Test connection - use the DATABASE_URL from backend/.env
psql '<your-database-url-from-.env>'
```

---

## 🔐 Production Deployment

### Before Deploying to Lambda

1. **Apply migrations locally first**:
   ```bash
   alembic upgrade head
   ```

2. **Verify on Neon** (production database):
   ```bash
   # Use DATABASE_URL from backend/.env
   psql '<your-database-url>'
   \dt  # Verify tables exist
   ```

3. **Deploy Lambda code** (doesn't need Alembic, just SQLAlchemy models)

### AWS Lambda Considerations

- **Lambda does NOT run migrations** - Apply migrations manually before deploying
- Lambda only needs `sqlalchemy` and `psycopg2-binary` (not `alembic`)
- Run migrations from your local machine or CI/CD pipeline

---

## 📖 File Structure

```
backend/
├── alembic/                    # Alembic configuration
│   ├── versions/               # Migration files
│   │   └── fa5132bfbf71_create_users_table.py
│   ├── env.py                  # Alembic runtime config (loads .env)
│   └── script.py.mako          # Migration template
├── alembic.ini                 # Alembic settings
├── models/                     # SQLAlchemy models
│   ├── __init__.py             # Exports Base and all models
│   └── user.py                 # User model
├── .env                        # DATABASE_URL
└── requirements.txt            # Includes alembic, sqlalchemy
```

---

## 🔗 Useful Links

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Neon Console](https://console.neon.tech/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
