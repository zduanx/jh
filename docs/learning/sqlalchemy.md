# SQLAlchemy ORM Basics

**Date:** 2024-12-16
**Topics:** SQLAlchemy session management, query patterns, ORM operations

---

## Table of Contents

1. [Session Management](#session-management)
2. [SessionLocal - The Session Factory](#sessionlocal---the-session-factory)
3. [Query Patterns](#query-patterns)
4. [ORM Loading Strategies](#orm-loading-strategies)
5. [Update Patterns](#update-patterns)
6. [Session Lifecycle Best Practices](#session-lifecycle-best-practices)

---

## Session Management

### What is a Session?

A **Session** is SQLAlchemy's way of talking to the database. Think of it as:
- A **connection** to the database
- A **workspace** for your database operations
- A **transaction** manager (tracks changes until you commit)

```python
from sqlalchemy.orm import Session

# Session provides:
session.query(User)      # Query the database
session.add(user)        # Track new objects
session.commit()         # Save changes to database
session.rollback()       # Discard changes
session.close()          # Close connection
```

### Session is Like a Shopping Cart

```
Query           →  Browse products (SELECT)
Add/modify      →  Put items in cart (not saved yet)
Commit          →  Checkout (save to database)
Rollback        →  Empty cart (discard changes)
Close           →  Leave store (release connection)
```

---

## SessionLocal - The Session Factory

### What is SessionLocal?

`SessionLocal` is **not a session** - it's a **factory that creates sessions**.

```python
from sqlalchemy.orm import sessionmaker

# This is NOT a session, it's a FACTORY
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Each call creates a NEW independent session
session1 = SessionLocal()  # Fresh session #1
session2 = SessionLocal()  # Fresh session #2 (completely separate)
```

**Analogy:** `SessionLocal` is like a vending machine - each time you "call" it, you get a fresh product (session).

### Why Not Share One Session?

**Bad: Sharing one session across requests**
```python
# ❌ DON'T DO THIS
db = SessionLocal()  # Created once

@app.get("/user1")
def get_user1():
    return db.query(User).first()  # Uses shared session

@app.get("/user2")
def get_user2():
    return db.query(User).first()  # Uses SAME shared session
```

**Problems:**
- ❌ **Not thread-safe** - Concurrent requests interfere with each other
- ❌ **Stale data** - Session caches previous queries
- ❌ **Connection leaks** - Never closed, exhausts connection pool
- ❌ **Transaction conflicts** - Changes from one request affect another

**Good: Each request gets fresh session**
```python
# ✅ DO THIS
def get_db():
    db = SessionLocal()  # Fresh session per request
    try:
        yield db
    finally:
        db.close()  # Always closed

@app.get("/user1")
def get_user1(db = Depends(get_db)):
    return db.query(User).first()  # Uses its own session

@app.get("/user2")
def get_user2(db = Depends(get_db)):
    return db.query(User).first()  # Uses its own session
```

**Benefits:**
- ✅ **Thread-safe** - Each request has isolated session
- ✅ **Fresh data** - No stale cache
- ✅ **No leaks** - Sessions always closed
- ✅ **Clean transactions** - No cross-request pollution

### SessionLocal Configuration

```python
SessionLocal = sessionmaker(
    autocommit=False,  # Manual commit (we control when to save)
    autoflush=False,   # Manual flush (we control when to sync)
    bind=engine        # Connect to this database
)
```

**Parameters explained:**

**`autocommit=False`** - We manually call `commit()`:
```python
session = SessionLocal()
user = User(email="foo@example.com")
session.add(user)
# Changes NOT saved yet
session.commit()  # ✅ NOW saved to database
```

**`autoflush=False`** - We control when to sync pending changes:
```python
session = SessionLocal()
user = User(email="foo@example.com")
session.add(user)
# user not in database yet
session.flush()  # Sync to database (but not committed)
# Now can query for user in same transaction
```

**`bind=engine`** - Which database to connect to:
```python
engine = create_engine("postgresql://...")
SessionLocal = sessionmaker(bind=engine)
```

---

## Query Patterns

### What You Query Determines What You Get

#### Pattern 1: Query Entire Model → Get Model Object

```python
user = db.query(User).filter_by(email="foo@example.com").first()
```

**Returns:** `User` object with ALL fields loaded

```python
print(type(user))  # <class 'models.user.User'>
print(user.user_id)      # 1
print(user.email)        # "foo@example.com"
print(user.name)         # "John Doe"
print(user.picture_url)  # "https://..."
print(user.created_at)   # datetime(...)
print(user.last_login)   # datetime(...)
```

**SQL Generated:**
```sql
SELECT *
FROM users
WHERE email = 'foo@example.com'
LIMIT 1
```

#### Pattern 2: Query Specific Columns → Get Tuple

```python
result = db.query(User.user_id, User.name).filter_by(email="foo@example.com").first()
```

**Returns:** `tuple`, NOT a User object!

```python
print(type(result))  # <class 'tuple'>
print(result)        # (1, "John Doe")
print(result[0])     # 1 (user_id)
print(result[1])     # "John Doe" (name)

# ❌ This FAILS - it's a tuple, not a User object
print(result.name)   # AttributeError: 'tuple' object has no attribute 'name'
```

**SQL Generated:**
```sql
SELECT user_id, name
FROM users
WHERE email = 'foo@example.com'
LIMIT 1
```

#### Pattern 3: Query Single Column → Get Tuple with One Element

```python
result = db.query(User.user_id).filter_by(email="foo@example.com").first()
```

**Returns:** Tuple with one element

```python
print(type(result))  # <class 'tuple'>
print(result)        # (1,)  ← Note the comma, it's a tuple!
print(result[0])     # 1

# ❌ Common mistake
if result == 1:      # False! result is (1,), not 1
    pass

# ✅ Correct
if result[0] == 1:   # True!
    pass
```

**SQL Generated:**
```sql
SELECT user_id
FROM users
WHERE email = 'foo@example.com'
LIMIT 1
```

#### Pattern 4: Query Single Column with `.scalar()` → Get Value

```python
user_id = db.query(User.user_id).filter_by(email="foo@example.com").scalar()
```

**Returns:** The actual value (unwrapped from tuple)

```python
print(type(user_id))  # <class 'int'>
print(user_id)        # 1 (not (1,))

# ✅ Can use directly
if user_id == 1:      # True!
    pass
```

**SQL Generated:**
```sql
SELECT user_id
FROM users
WHERE email = 'foo@example.com'
LIMIT 1
```

### Query Method Comparison

| Method | Returns | Example | Use When |
|--------|---------|---------|----------|
| `query(User).first()` | User object or None | `user = db.query(User).first()` | Need full object |
| `query(User.id, User.name).first()` | Tuple or None | `(1, "John")` | Need specific columns |
| `query(User.id).first()` | Tuple or None | `(1,)` | Need one column (with tuple) |
| `query(User.id).scalar()` | Value or None | `1` | Need one value (unwrapped) |
| `query(User).all()` | List of User objects | `[user1, user2]` | Need all rows as objects |
| `query(User.id).all()` | List of tuples | `[(1,), (2,)]` | Need all values |

### Common Mistakes

**Mistake 1: Expecting object from column query**
```python
# ❌ WRONG
result = db.query(User.name).filter_by(email="foo@example.com").first()
print(result.name)  # AttributeError! result is tuple, not User

# ✅ CORRECT
print(result[0])    # Access tuple element
```

**Mistake 2: Expecting value from `.first()`**
```python
# ❌ WRONG
user_id = db.query(User.user_id).filter_by(email="foo@example.com").first()
if user_id == 1:    # Always False! user_id is (1,), not 1

# ✅ CORRECT - Use .scalar()
user_id = db.query(User.user_id).filter_by(email="foo@example.com").scalar()
if user_id == 1:    # Now works!
```

**Mistake 3: Accessing wrong index**
```python
# ❌ WRONG
result = db.query(User.name).first()
print(result[1])    # IndexError: tuple index out of range

# ✅ CORRECT
print(result[0])    # Tuples are 0-indexed
```

---

## ORM Loading Strategies

### Lazy Loading (Default)

**What it is:** Related objects are loaded only when accessed.

```python
# Query user (doesn't load related posts yet)
user = db.query(User).first()

# First access to posts triggers SELECT
for post in user.posts:  # ← SELECT posts happens here
    print(post.title)
```

**SQL:**
```sql
-- First query
SELECT * FROM users LIMIT 1

-- Second query (triggered by user.posts access)
SELECT * FROM posts WHERE user_id = 1
```

**Pros:**
- Don't load data you don't need
- Initial query is fast

**Cons:**
- Can cause N+1 query problem
- Slower if you know you need the data

### Eager Loading (Explicit)

**What it is:** Load related objects immediately with JOIN.

```python
from sqlalchemy.orm import joinedload

# Load user AND posts in one query
user = db.query(User).options(joinedload(User.posts)).first()

# Accessing posts doesn't trigger SELECT
for post in user.posts:  # No additional query!
    print(post.title)
```

**SQL:**
```sql
-- Single query with JOIN
SELECT users.*, posts.*
FROM users
LEFT OUTER JOIN posts ON users.id = posts.user_id
WHERE users.id = 1
```

**Pros:**
- Avoids N+1 query problem
- Faster if you need the data

**Cons:**
- Loads more data than you might need
- Initial query is slower

### Partial Column Loading

**What it is:** Load only specific columns for performance.

```python
# If User has a huge "resume_text" column you don't need:
users = db.query(User.user_id, User.email).all()
# Returns: List of tuples [(1, "a@ex.com"), (2, "b@ex.com")]

# Much faster than loading entire User objects with resume_text!
```

**When to use:**
- Large text/blob columns you don't need
- Performance optimization
- Listing/searching where you only need a few fields

**When NOT to use:**
- Small tables (like our User table) - just load the whole object for simplicity
- When you need the full object anyway

---

## Update Patterns

### Pattern 1: Load, Modify, Commit

```python
# 1. Load object
user = db.query(User).filter_by(email="foo@example.com").first()

# 2. Modify
user.name = "Updated Name"
user.last_login = datetime.now(timezone.utc)

# 3. Commit
db.commit()
```

**SQL:**
```sql
-- Load
SELECT * FROM users WHERE email = 'foo@example.com' LIMIT 1

-- Update
UPDATE users
SET name = 'Updated Name', last_login = '2024-12-16 10:00:00'
WHERE user_id = 1
```

**Pros:**
- See current values
- Can apply business logic
- Automatic optimistic locking

**Cons:**
- Requires loading full object (2 queries)

### Pattern 2: Update Without Loading

```python
db.query(User).filter_by(email="foo@example.com").update({
    "name": "Updated Name",
    "last_login": datetime.now(timezone.utc)
})
db.commit()
```

**SQL:**
```sql
-- Single UPDATE, no SELECT
UPDATE users
SET name = 'Updated Name', last_login = '2024-12-16 10:00:00'
WHERE email = 'foo@example.com'
```

**Pros:**
- Single query (faster)
- Don't need to load object

**Cons:**
- Can't see current values
- Can't apply logic based on current state
- No optimistic locking

### Our Implementation: Load-Modify-Commit

In `get_or_create_user()`, we use load-modify-commit:

```python
def update_user_profile(db: Session, user_id: int, name: str, picture_url: str):
    # 1. Load
    user = db.query(User).filter_by(user_id=user_id).first()
    if not user:
        return None

    # 2. Modify
    user.name = name
    user.picture_url = picture_url
    user.last_login = datetime.now(timezone.utc)

    # 3. Commit
    db.commit()
    db.refresh(user)  # Reload from database
    return user
```

**Why this pattern:**
- ✅ We get the user object to return
- ✅ Can verify user exists before updating
- ✅ SQLAlchemy tracks changes automatically
- ✅ Only modified fields are updated

---

## Session Lifecycle Best Practices

### Pattern: Session Per Request

```python
# ✅ CORRECT - Each request gets its own session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(user_id=user_id).first()
    return user
    # Session automatically closed after response
```

**Lifecycle:**
```
Request arrives
    ↓
Create session
    ↓
Execute queries
    ↓
Commit (if needed)
    ↓
Close session
    ↓
Response sent
```

### Anti-Pattern: Long-Lived Sessions

```python
# ❌ WRONG - Session lives too long
class UserService:
    def __init__(self):
        self.db = SessionLocal()  # Created once

    def get_user(self, user_id):
        return self.db.query(User).filter_by(user_id=user_id).first()
        # Session never closed!
```

**Problems:**
- Connection pool exhaustion
- Stale data
- Memory leaks
- Transaction conflicts

### Transaction Management

**Auto-commit disabled (our setup):**
```python
SessionLocal = sessionmaker(autocommit=False)

db = SessionLocal()
user = User(email="foo@example.com")
db.add(user)
# Not saved yet!
db.commit()  # ✅ Now saved
```

**Rollback on error:**
```python
db = SessionLocal()
try:
    user = User(email="foo@example.com")
    db.add(user)
    db.commit()
except Exception:
    db.rollback()  # Discard changes
    raise
finally:
    db.close()
```

### Connection Pool Settings

```python
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # Verify connection before using
    pool_recycle=3600,    # Recycle connections after 1 hour
)
```

**`pool_pre_ping=True`:**
- Tests connection before using
- Handles stale connections (database restarted, network issue)
- Prevents "server has gone away" errors

**`pool_recycle=3600`:**
- Recycles connections after 1 hour
- Prevents timeout from database's max connection age
- Good practice for cloud databases

---

## Comparison to Other ORMs

### SQLAlchemy vs Entity Framework (C#)

**Similarities:**
- Both are full-featured ORMs
- Both track changes automatically
- Both support lazy/eager loading
- Both use Unit of Work pattern

**SQLAlchemy Session ≈ EF DbContext:**

```python
# SQLAlchemy
db = SessionLocal()
user = db.query(User).first()
user.name = "Updated"
db.commit()
```

```csharp
// Entity Framework
using (var db = new AppDbContext()) {
    var user = db.Users.FirstOrDefault();
    user.Name = "Updated";
    db.SaveChanges();
}
```

**Key Difference:**
- EF: `SaveChanges()` commits
- SQLAlchemy: `commit()` commits

---

## Summary

### Key Concepts

1. **SessionLocal is a factory**, not a session
2. **One session per request** for thread-safety
3. **What you query determines what you get** (object vs tuple)
4. **Use `.scalar()` for single values**
5. **Load full objects for simplicity** (unless performance issue)
6. **Commit explicitly** (autocommit=False)
7. **Always close sessions** (use try/finally or `yield`)

### Quick Reference

```python
# Create session
db = SessionLocal()

# Query full object
user = db.query(User).filter_by(email="...").first()

# Query specific columns (returns tuple)
result = db.query(User.id, User.name).first()

# Query single value (unwrapped)
user_id = db.query(User.id).scalar()

# Update
user.name = "Updated"
db.commit()

# Always close
db.close()

# Or use with FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## References

- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/tutorial.html)
- [SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [SQLAlchemy Query API](https://docs.sqlalchemy.org/en/20/orm/queryguide.html)
- [Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
