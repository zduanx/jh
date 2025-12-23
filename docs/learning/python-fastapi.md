# Python Generators, Concurrency, and FastAPI

**Date:** 2024-12-16 (updated 2024-12-22)
**Topics:** Generators, yield vs return, FastAPI dependency injection, resource management, ThreadPoolExecutor vs asyncio, GIL

---

## Table of Contents

1. [Understanding Generators](#understanding-generators)
2. [yield vs return](#yield-vs-return)
3. [Generator Type Annotations](#generator-type-annotations)
4. [FastAPI Dependency Injection](#fastapi-dependency-injection)
5. [Complete Dependency Lifecycle](#complete-dependency-lifecycle)
6. [When to Use yield vs return](#when-to-use-yield-vs-return)
7. [Sync vs Async Dependencies](#sync-vs-async-dependencies)
8. [Python's GIL (Global Interpreter Lock)](#pythons-gil-global-interpreter-lock)
9. [ThreadPoolExecutor vs asyncio](#threadpoolexecutor-vs-asyncio)

---

## Understanding Generators

### What is a Generator?

A generator is a function that can **pause** and **resume** its execution, unlike regular functions that run to completion.

**Regular Function:**
```python
def get_value():
    value = compute_value()
    return value  # Returns immediately, function exits
    print("This never runs")  # ❌ Unreachable code
```

**Generator Function:**
```python
def get_value():
    value = compute_value()
    yield value  # ⏸️ Pauses here, gives value to caller
    print("This DOES run!")  # ✅ Runs when resumed
```

### How Generators Execute

```python
def my_generator():
    print("1. Start")
    yield "first"
    print("3. Resumed")
    yield "second"
    print("5. Resumed again")

# Create generator
gen = my_generator()

# First next() - runs until first yield
value1 = next(gen)
# Output: "1. Start"
# Returns: "first"

# Second next() - resumes from first yield, runs until second yield
value2 = next(gen)
# Output: "3. Resumed"
# Returns: "second"

# Third next() - resumes from second yield, reaches end
try:
    next(gen)
    # Output: "5. Resumed again"
except StopIteration:
    # Generator exhausted
    print("Generator finished")
```

**Complete output:**
```
1. Start
3. Resumed
5. Resumed again
Generator finished
```

### Key Insight: Suspendable Execution

Generators can:
1. **Pause** at `yield` and save their state
2. **Return** a value to the caller
3. **Resume** from where they paused when `next()` is called again
4. **Continue** executing code after the `yield`

This is perfect for the **open-use-close** pattern!

---

## yield vs return

### Execution Differences

#### With `return` (one-way trip)

```python
def regular_function():
    resource = open_resource()
    return resource  # ← Returns immediately
    resource.close()  # ❌ Never runs!
```

**Flow:**
```
Call function
    ↓
open_resource()
    ↓
return resource  ← Function EXITS here
    ↓
(No way to run cleanup)
```

#### With `yield` (round trip)

```python
def generator_function():
    resource = open_resource()
    try:
        yield resource  # ← Pauses here
        # Execution resumes here after caller is done
    finally:
        resource.close()  # ✅ Always runs!
```

**Flow:**
```
Call function
    ↓
open_resource()
    ↓
yield resource  ← PAUSES here, gives resource to caller
    ↓
(Caller uses resource...)
    ↓
next() called again to resume
    ↓
Resumes from yield
    ↓
finally block runs
    ↓
resource.close()  ✅
```

### The Power of `finally`

The `finally` block **always runs**, even if an error occurs:

```python
def safe_resource():
    resource = open_resource()
    try:
        yield resource
    finally:
        resource.close()  # ✅ Runs even if caller raises exception!

# Even if this crashes...
gen = safe_resource()
res = next(gen)
raise Exception("Something broke!")  # 💥

# ...the finally block still runs and closes the resource!
```

---

## Generator Type Annotations

### The Problem

This type annotation is technically **wrong**:

```python
from sqlalchemy.orm import Session

def get_db() -> Session:  # ❌ Says "returns Session"
    yield SessionLocal()   # But actually returns Generator!
```

**Why it works anyway:** FastAPI doesn't check type annotations at runtime, it checks `inspect.isgenerator()`.

### The Correct Type Annotation

```python
from typing import Generator
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    yield SessionLocal()
```

### Understanding `Generator[YieldType, SendType, ReturnType]`

```python
def get_db() -> Generator[Session, None, None]:
    #                      ^^^^^^^  ^^^^  ^^^^
    #                         |      |     |
    #                         |      |     +-- ReturnType: None
    #                         |      |         (doesn't return a value after yields)
    #                         |      |
    #                         |      +-------- SendType: None
    #                         |                (we don't use .send() method)
    #                         |
    #                         +--------------- YieldType: Session
    #                                          (what yield produces)
    db = SessionLocal()
    try:
        yield db  # ← This yields a Session object
    finally:
        db.close()
```

### Breakdown of Each Type Parameter

**YieldType - What the generator produces:**
```python
def count() -> Generator[int, None, None]:
    yield 1  # Yields int
    yield 2  # Yields int
    yield 3  # Yields int
```

**SendType - What you can send() to the generator:**
```python
def echo() -> Generator[str, str, None]:
    received = yield "ready"  # Can receive str via .send()
    yield f"You sent: {received}"

gen = echo()
next(gen)  # "ready"
gen.send("hello")  # Sends "hello" to generator
```

We use `None` because we don't use `.send()`:
```python
def get_db() -> Generator[Session, None, None]:
    #                              ^^^^
    #                              We don't use .send(), so None
    db = SessionLocal()
    try:
        yield db  # Just yield, don't receive anything
    finally:
        db.close()
```

**ReturnType - What the generator returns when exhausted:**
```python
def example() -> Generator[int, None, str]:
    yield 1
    yield 2
    return "done"  # Returns str when exhausted

gen = example()
next(gen)  # 1
next(gen)  # 2
try:
    next(gen)
except StopIteration as e:
    print(e.value)  # "done"
```

We use `None` because we don't return a value:
```python
def get_db() -> Generator[Session, None, None]:
    #                                    ^^^^
    #                                    No return value, so None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # No return statement
```

### Type Checking Comparison

**Without proper typing (works at runtime, fails mypy):**
```python
def get_db() -> Session:
    yield SessionLocal()

# Runtime: ✅ Works fine
# mypy: ❌ error: Generator function's return type should be Generator[...]
```

**With proper typing (works at runtime AND mypy):**
```python
def get_db() -> Generator[Session, None, None]:
    yield SessionLocal()

# Runtime: ✅ Works fine
# mypy: ✅ Success
```

---

## FastAPI Dependency Injection

### The Problem: Resource Management in Web Endpoints

**Without dependency injection (messy):**
```python
@app.get("/users")
def get_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return users
    finally:
        db.close()
    # Every endpoint needs try/finally! 😫
```

**With dependency injection (clean):**
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users")
def get_users(db = Depends(get_db)):
    users = db.query(User).all()
    return users
    # Cleanup happens automatically! 🎉
```

### How `Depends()` Works

FastAPI's `Depends()` is smart - it detects whether a dependency is a generator or regular function:

```python
import inspect

# Pseudocode of FastAPI's dependency resolution
def resolve_dependency(dependency_func):
    result = dependency_func()

    # Check if it's a generator
    if inspect.isgenerator(result):
        # It's a generator! Use generator protocol
        value = next(result)  # Extract yielded value
        cleanup_generators.append(result)  # Save for cleanup later
        return value
    else:
        # Regular function, use return value directly
        return result
```

**Key point:** `Depends()` checks `inspect.isgenerator()` at **runtime**, not the type annotation!

### Detection Examples

**Generator dependency (has yield):**
```python
def get_db():
    yield SessionLocal()

result = get_db()
inspect.isgenerator(result)  # True ✅
# Depends() will call next(result) and save for cleanup
```

**Regular dependency (has return):**
```python
async def get_current_user():
    return {"user_id": 1}

result = await get_current_user()
inspect.isgenerator(result)  # False ✅
# Depends() will use result directly, no cleanup needed
```

---

## Complete Dependency Lifecycle

Let's trace the complete lifecycle of a dependency with cleanup:

### The Setup

```python
def get_db() -> Generator[Session, None, None]:
    print("1. get_db: Creating session")
    db = SessionLocal()
    try:
        print("2. get_db: About to yield")
        yield db  # ⏸️ PAUSE
        print("6. get_db: Resumed after yield")
    finally:
        print("7. get_db: Cleaning up")
        db.close()
        print("8. get_db: Done")

@router.post("/google")
async def google_auth(db: Session = Depends(get_db)):
    print("3. google_auth: Got db, starting work")
    user = get_or_create_user(db, ...)
    print("4. google_auth: Work done")
    return TokenResponse(...)
```

### Execution Flow

```
Request arrives
    ↓
FastAPI: "This endpoint needs db = Depends(get_db)"
    ↓
[FastAPI calls get_db()]
    1. get_db: Creating session
    2. get_db: About to yield
    ↓ ⏸️ PAUSED AT YIELD ↓

[FastAPI extracts yielded value]
    db_value = next(get_db_generator)

[FastAPI saves generator for cleanup]
    cleanup_queue.append(get_db_generator)
    ↓

[FastAPI calls endpoint with dependency]
    3. google_auth: Got db, starting work
    user = get_or_create_user(db, ...)
    4. google_auth: Work done
    return TokenResponse(...)
    ↓

[Endpoint finishes]
    ↓
[FastAPI runs cleanup]
    for gen in cleanup_queue:
        next(gen)  # ⏯️ RESUME
    ↓

[get_db resumes from yield]
    6. get_db: Resumed after yield
    ↓ Falls into finally ↓
    7. get_db: Cleaning up
    db.close()
    8. get_db: Done
    ↓ Raises StopIteration ↓

Response sent to client
```

### Cleanup Even on Errors

The `finally` block runs even if the endpoint raises an exception:

```python
@router.post("/test")
async def test(db: Session = Depends(get_db)):
    user = get_or_create_user(db, ...)
    raise Exception("Something broke!")  # 💥 Exception!
    # Endpoint crashes...

# FastAPI's cleanup still happens:
# - Catches exception
# - Calls next(get_db_generator) to resume
# - finally block runs
# - db.close() executes ✅
# - Returns error response to client
```

---

## When to Use yield vs return

### Use `yield` When You Need Cleanup

**Database connections:**
```python
def get_db():
    db = SessionLocal()  # Open connection
    try:
        yield db
    finally:
        db.close()  # Close connection ✅
```

**File handles:**
```python
def get_file():
    f = open("data.txt")  # Open file
    try:
        yield f
    finally:
        f.close()  # Close file ✅
```

**External connections:**
```python
def get_redis():
    conn = redis.Redis()  # Connect to Redis
    try:
        yield conn
    finally:
        conn.close()  # Disconnect ✅
```

### Use `return` When You Don't Need Cleanup

**Data transformation:**
```python
async def get_current_user(token: str):
    payload = decode_token(token)
    return payload  # Just return data ✅
```

**Validation:**
```python
def validate_api_key(api_key: str = Header(...)):
    if not is_valid(api_key):
        raise HTTPException(401)
    return api_key  # Just return validated value ✅
```

**Configuration:**
```python
def get_settings():
    return Settings()  # Just return settings object ✅
```

### Decision Tree

```
Does your dependency open a resource?
    ↓
    Yes → Use `yield` with try/finally
    |         def get_resource():
    |             resource = open_resource()
    |             try:
    |                 yield resource
    |             finally:
    |                 resource.close()
    |
    No → Use `return`
            def get_value():
                return compute_value()
```

---

## Sync vs Async Dependencies

### Should Dependencies Be `async`?

**It depends on what's inside:**

#### Use Sync (`def`) When Operations Are Blocking

```python
# ✅ CORRECT - Sync function for blocking operations
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()  # Blocking operation
    try:
        yield db
    finally:
        db.close()  # Blocking operation
```

**Why sync?**
- SQLAlchemy (with psycopg2-binary) is **synchronous** - all operations block
- `SessionLocal()` blocks until connection is established
- `db.close()` blocks until connection is closed
- FastAPI automatically runs sync dependencies in a **thread pool**, so they don't block the event loop

#### Use Async (`async def`) Only for Async Operations

```python
# ✅ CORRECT - Async function for async operations
async def get_current_user(token: str):
    payload = await decode_token_async(token)  # Awaitable
    user = await fetch_user_async(payload.user_id)  # Awaitable
    return user
```

**Why async?**
- All operations inside are **awaitable** (non-blocking)
- Can be called with `await`
- Doesn't block the event loop

### Common Mistake: Async with Blocking Code

```python
# ❌ WRONG - Misleading!
async def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()  # This is STILL blocking! Can't await it
    try:
        yield db
    finally:
        db.close()  # This is STILL blocking! Can't await it
```

**Problem:**
- `async` keyword suggests "non-blocking"
- But `SessionLocal()` and `db.close()` are blocking operations
- You can't `await` them because they're not coroutines
- Misleading to future developers

### With Async SQLAlchemy

If you were using async SQLAlchemy (different setup entirely):

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# ✅ NOW async makes sense
async def get_db():
    async with async_session_maker() as session:
        yield session
        await session.commit()  # ✅ Awaitable operation
```

But we're using regular (synchronous) SQLAlchemy, so use sync `def`.

---

## Real-World Example: Our Auth Flow

### Complete Implementation

```python
# 1. Define dependency with cleanup
from typing import Generator
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    """Database session dependency with automatic cleanup"""
    db = SessionLocal()  # Create session
    try:
        yield db  # Pause and give to endpoint
    finally:
        db.close()  # Always cleanup

# 2. Use in endpoint
@router.post("/google")
async def google_auth(
    request: GoogleTokenRequest,
    db: Session = Depends(get_db)  # FastAPI injects session
):
    # 3. Use session for database operations
    user, is_new = get_or_create_user(
        db=db,  # Session is already open
        email=user_email,
        name=user_info["name"],
        picture_url=user_info.get("picture")
    )

    # 4. Create JWT with user_id
    access_token = create_access_token(
        data={"user_id": user.user_id, ...}
    )

    # 5. Return response
    return TokenResponse(access_token=token, ...)

    # 6. FastAPI automatically:
    #    - Resumes get_db() generator
    #    - Runs finally block
    #    - Closes database session
```

### Why This Pattern is Powerful

✅ **No resource leaks** - Database connection always closed
✅ **Exception safe** - Cleanup happens even if endpoint crashes
✅ **Clean code** - No try/finally clutter in endpoints
✅ **Reusable** - Same pattern works for any resource (files, Redis, etc.)
✅ **Type safe** - Proper `Generator` annotation for mypy
✅ **Testable** - Can override dependency in tests

---

## Summary

### Key Concepts

1. **Generators pause and resume** using `yield`
2. **`yield` enables cleanup** via code after the yield
3. **`finally` always runs**, even on errors
4. **FastAPI detects generators** with `inspect.isgenerator()`
5. **Type as `Generator[YieldType, SendType, ReturnType]`** for correctness
6. **Use sync `def` for blocking operations** (like SQLAlchemy)
7. **Use `yield` for resources**, `return` for simple data

### Quick Reference

```python
# Generator with cleanup
def get_resource() -> Generator[Resource, None, None]:
    resource = open_resource()
    try:
        yield resource  # Pause here
    finally:
        resource.close()  # Always runs

# Regular dependency
def get_value() -> Value:
    return compute_value()

# Using in endpoint
@app.get("/data")
def get_data(
    resource = Depends(get_resource),  # Cleanup automatic
    value = Depends(get_value)          # No cleanup needed
):
    return process(resource, value)
```

---

## Python's GIL (Global Interpreter Lock)

### What is the GIL?

The GIL is a mutex (lock) in CPython that allows only **one thread to execute Python bytecode at a time**, even on multi-core machines.

```
┌─────────────────────────────────────────────────────────┐
│                    Python Process                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │                       GIL                            ││
│  │  Only ONE thread can hold this lock at a time       ││
│  └─────────────────────────────────────────────────────┘│
│                                                          │
│  Thread 1: [waiting...] → [RUN] → [waiting...] → [RUN]  │
│  Thread 2: [RUN] → [waiting...] → [RUN] → [waiting...]  │
│  Thread 3: [waiting...] → [waiting...] → [RUN] → ...    │
│                                                          │
│  Threads take turns holding the GIL                      │
└─────────────────────────────────────────────────────────┘
```

### Why Does the GIL Exist?

1. **Memory safety** - CPython uses reference counting for garbage collection. Without GIL, multiple threads could corrupt reference counts.
2. **Simplicity** - Makes C extension development easier (no need for fine-grained locking)
3. **Historical** - Designed when single-core CPUs were the norm

### GIL Impact by Workload Type

| Workload Type | GIL Impact | Example |
|---------------|------------|---------|
| **I/O-bound** | Minimal | HTTP requests, file reads, DB queries |
| **CPU-bound** | Severe | Math computation, image processing, parsing |

**Key insight:** The GIL is **released** during I/O operations!

```python
# During I/O wait, GIL is released - other threads can run
response = requests.get(url)  # GIL released while waiting for network
#          ^^^^^^^^^^^^^^^^
#          Thread gives up GIL here, other threads can execute

# During CPU work, GIL is held - blocks other threads
result = heavy_computation(data)  # GIL held entire time
#        ^^^^^^^^^^^^^^^^^^^^^^^
#        No other Python thread can run until this finishes
```

### GIL and Parallelism

**Threads (threading, ThreadPoolExecutor):**
- Share memory, share GIL
- Good for I/O-bound: threads release GIL during I/O wait
- Bad for CPU-bound: only one thread computes at a time

**Processes (multiprocessing, ProcessPoolExecutor):**
- Separate memory, separate GIL per process
- Good for CPU-bound: true parallelism across cores
- More overhead: data must be serialized between processes

```
Threads (shared GIL):          Processes (separate GILs):
┌────────────────────┐         ┌──────────┐  ┌──────────┐
│  Process           │         │ Process 1│  │ Process 2│
│  ┌──────┐          │         │ ┌──────┐ │  │ ┌──────┐ │
│  │ GIL  │          │         │ │ GIL  │ │  │ │ GIL  │ │
│  └──────┘          │         │ └──────┘ │  │ └──────┘ │
│  T1  T2  T3        │         │   T1     │  │   T1     │
│  (take turns)      │         │ (runs)   │  │ (runs)   │
└────────────────────┘         └──────────┘  └──────────┘
                                True parallel execution!
```

---

## ThreadPoolExecutor vs asyncio

### Decision Matrix

| Situation | Use | Why |
|-----------|-----|-----|
| I/O with **sync libraries** (requests, psycopg2) | `ThreadPoolExecutor` | Libraries block; threads let them run in parallel |
| I/O with **async libraries** (aiohttp, asyncpg) | `asyncio` | Native async, more efficient, no thread overhead |
| **CPU-bound** work | `ProcessPoolExecutor` | Bypass GIL with separate processes |

### How Each Works

**ThreadPoolExecutor (threads):**
```python
from concurrent.futures import ThreadPoolExecutor

def fetch_url(url):
    return requests.get(url)  # Blocking call, but releases GIL during I/O wait

# Threads run in parallel during I/O waits
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(fetch_url, url) for url in urls]
    results = [f.result() for f in futures]
```

```
Timeline:
Thread 1: [request]----[waiting for response]----[process]
Thread 2:    [request]----[waiting for response]----[process]
Thread 3:       [request]----[waiting for response]----[process]
                ↑
                GIL released during "waiting" - all threads progress
```

**asyncio (event loop):**
```python
import asyncio
import aiohttp

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()  # Non-blocking, yields control

# Single thread, but concurrent via event loop
async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
```

```
Timeline (single thread):
[req1]→[req2]→[req3]→[wait]→[resp1]→[resp2]→[resp3]→[process all]
       ↑
       Event loop switches between tasks at await points
```

### When `async def` is Misleading

```python
# ❌ BAD - says async but uses blocking library
async def fetch_data():
    return requests.get(url)  # BLOCKS the event loop!

# ✅ GOOD - honest sync function
def fetch_data():
    return requests.get(url)  # Caller knows it blocks

# ✅ GOOD - truly async
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()  # Non-blocking
```

### Real Example: Dry Run Endpoint

Our extractors use `requests` (synchronous). Options:

**Option 1: Sync function + ThreadPoolExecutor (what we use)**
```python
@router.post("/dry-run")
def dry_run(db: Session = Depends(get_db)):  # Note: `def`, not `async def`
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_run_extractor, s.company_name, s.title_filters): s.company_name
            for s in settings
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results
```

- Honest: function is sync, uses threads for parallelism
- FastAPI runs sync endpoints in thread pool automatically

**Option 2: Async function + run_in_executor**
```python
@router.post("/dry-run")
async def dry_run(db: Session = Depends(get_db)):
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(executor, _run_extractor, s.company_name, s.title_filters)
        for s in settings
    ]
    results = await asyncio.gather(*tasks)
    return results
```

- More complex, same performance
- Use if rest of codebase is async

**Option 3: True async (would require rewriting extractors)**
```python
# Would need to rewrite extractors to use aiohttp
async def _run_extractor_async(company_name, filters):
    async with aiohttp.ClientSession() as session:
        # ... async HTTP calls

@router.post("/dry-run")
async def dry_run(db: Session = Depends(get_db)):
    tasks = [_run_extractor_async(s.company_name, s.title_filters) for s in settings]
    results = await asyncio.gather(*tasks)
    return results
```

- Most efficient, but requires rewriting all extractors
- Not worth it for our use case (extractors are already written with requests)

### Summary: Choosing the Right Tool

```
Is the library async-native (aiohttp, asyncpg)?
    │
    ├── Yes → Use asyncio
    │         async def foo():
    │             results = await asyncio.gather(*tasks)
    │
    └── No (uses requests, psycopg2, etc.)
            │
            ├── I/O-bound → Use ThreadPoolExecutor
            │               with ThreadPoolExecutor() as executor:
            │                   futures = [executor.submit(fn, arg) for arg in args]
            │
            └── CPU-bound → Use ProcessPoolExecutor
                            with ProcessPoolExecutor() as executor:
                                futures = [executor.submit(fn, arg) for arg in args]
```

---

## References

- [PEP 255 - Simple Generators](https://peps.python.org/pep-0255/)
- [FastAPI Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
- [Python Generators Tutorial](https://realpython.com/introduction-to-python-generators/)
- [typing.Generator Documentation](https://docs.python.org/3/library/typing.html#typing.Generator)
- [Python GIL Explained](https://realpython.com/python-gil/)
- [concurrent.futures Documentation](https://docs.python.org/3/library/concurrent.futures.html)
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
