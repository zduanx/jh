# Backend Development

Backend frameworks, architecture patterns, and system design concepts.

---

## Table of Contents

1. [FastAPI vs Django](#fastapi-vs-django)
2. [FastAPI Dependency Injection](#fastapi-dependency-injection)
3. [REST vs GraphQL](#rest-vs-graphql)
4. [Stateless vs Stateful](#stateless-vs-stateful)
5. [Single vs Multiple Servers](#single-vs-multiple-servers)
6. [Message Queues](#message-queues)
7. [WebSocket](#websocket)
8. [Passport.js](#passportjs)

---

## FastAPI vs Django

### Core Difference

**Django** = Full-featured web framework (batteries included)
- Complete framework with ORM, admin panel, auth, templates, forms
- Best for: Traditional web apps with server-side rendering

**FastAPI** = Modern API framework (lightweight, focused)
- Focused on building APIs only (no built-in frontend)
- Best for: REST APIs, microservices, backend for SPAs

### Comparison Table

| Feature | Django | FastAPI |
|---------|--------|---------|
| **Primary use** | Full web apps | APIs only |
| **Built-in admin** | ✅ Yes | ❌ No |
| **ORM** | ✅ Django ORM | ❌ Use SQLAlchemy |
| **Templates** | ✅ Built-in | ❌ No (API-focused) |
| **Authentication** | ✅ Built-in | ❌ DIY |
| **Performance** | Slower (sync) | ⚡ **Much faster** (async) |
| **Async support** | Partial | ✅ Full native async |
| **API docs** | ❌ Manual | ✅ **Auto-generated** |
| **Type hints** | Optional | ✅ **Required** |
| **Learning curve** | Steeper | Gentle |
| **Maturity** | 2005 (very mature) | 2018 (newer) |

### Code Comparison

**Django (with Django REST Framework):**
```python
# models.py
class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=100)

# serializers.py
class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['title', 'company']

# views.py
class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

# urls.py
router = routers.DefaultRouter()
router.register(r'jobs', JobViewSet)

# Files needed: 4+
```

**FastAPI:**
```python
# main.py (everything in one file!)
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Job(BaseModel):
    title: str
    company: str

@app.get("/jobs")
def get_jobs():
    return [{"title": "Engineer", "company": "Google"}]

@app.post("/jobs")
def create_job(job: Job):
    return job

# Files needed: 1
```

### Performance Benchmarks

- **Django:** ~1,000 req/s
- **Django + DRF:** ~800 req/s
- **FastAPI:** ~10,000-25,000 req/s ⚡

### When to Use Each

**Use Django when:**
- Building traditional web app (server-side rendered)
- Need built-in admin panel (huge time saver)
- Want everything out-of-the-box
- Building CMS, blog, e-commerce site

**Use FastAPI when:**
- Building REST APIs for React/Vue/mobile
- Need high performance
- Want auto-generated API docs
- Building microservices
- Love type safety

### Our Decision: FastAPI

**Why:**
1. Perfect for React frontend architecture
2. Auto-generated API docs (great for testing)
3. Modern, async, fast
4. Great for interviews (shows modern tech skills)
5. Lightweight for AWS Lambda deployment

---

## FastAPI Dependency Injection

### What is Dependency Injection?

**Dependency Injection (DI)** is a core FastAPI feature where you declare dependencies in function parameters, and FastAPI automatically calls them and passes the results to your function.

### The Pattern

Instead of manually extracting and validating data inside route handlers, you use `Depends()`:

```python
# ❌ Manual approach (NOT recommended)
@app.get("/user")
async def get_user():
    # Extract token from headers
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401)

    token = auth_header.replace("Bearer ", "")
    payload = decode_token(token)

    # ... more validation logic
    return {"email": payload["email"]}

# ✅ FastAPI Dependency Injection (RECOMMENDED)
@app.get("/user")
async def get_user(current_user: dict = Depends(get_current_user)):
    return {"email": current_user["email"]}
```

### Why It Looks Weird

You might wonder: **"Why is `current_user` a parameter when the API has no parameters?"**

**Answer:** The client doesn't send `current_user` as a parameter! FastAPI:
1. Sees `Depends(get_current_user)` in the signature
2. Calls `get_current_user()` BEFORE executing the route handler
3. Extracts data from the request (headers, cookies, body, etc.)
4. Passes the result as `current_user` to your function

### Real Example from Our Code

**Dependency definition:** `backend/auth/dependencies.py`
```python
from fastapi.security import HTTPBearer

security = HTTPBearer()  # Extracts "Bearer <token>" from Authorization header

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Extract and validate JWT token from Authorization header
    """
    token = credentials.credentials  # The actual token
    payload = decode_access_token(token)  # Decode and validate

    if not payload.get("email"):
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "email": payload["email"],
        "name": payload["name"],
        "picture": payload["picture"]
    }
```

**Using the dependency:** `backend/api/routes.py`
```python
@router.get("/user", response_model=UserInfo)
async def get_user(current_user: dict = Depends(get_current_user)):
    """
    Get current user info (requires authentication)

    FastAPI automatically:
    1. Extracts "Authorization: Bearer <token>" from headers (via HTTPBearer)
    2. Calls get_current_user() to validate the token
    3. Passes the result as current_user to this function
    4. If any step fails, returns 401/403 without calling this function
    """
    return UserInfo(**current_user)
```

### How Dependencies Work Internally

**Nested Dependencies:**
```python
# Level 1: HTTPBearer extracts token from Authorization header
security = HTTPBearer()

# Level 2: get_current_user validates the token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # credentials.credentials = the actual JWT token
    return decode_and_validate(credentials.credentials)

# Level 3: Your route handler uses the validated user
@app.get("/api/user")
async def get_user(current_user: dict = Depends(get_current_user)):
    return current_user
```

**Execution flow:**
```
1. Client sends: GET /api/user
                 Authorization: Bearer eyJhbGc...

2. FastAPI sees Depends(get_current_user) in route signature

3. FastAPI sees get_current_user has Depends(security)

4. FastAPI calls security (HTTPBearer):
   - Extracts "Bearer eyJhbGc..." from Authorization header
   - Returns HTTPAuthorizationCredentials(credentials="eyJhbGc...")

5. FastAPI calls get_current_user(credentials=...):
   - Decodes and validates JWT
   - Returns {"email": "user@example.com", "name": "User", ...}

6. FastAPI calls get_user(current_user={"email": ...}):
   - Your route handler executes with validated user data

7. Response: {"email": "user@example.com", "name": "User", ...}
```

### Key Benefits

**1. Code Reuse**
```python
# Write authentication logic once
async def get_current_user(...):
    ...

# Use it everywhere
@app.get("/user")
async def get_user(current_user: dict = Depends(get_current_user)):
    ...

@app.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    ...

@app.post("/jobs")
async def create_job(
    job: Job,
    current_user: dict = Depends(get_current_user)
):
    ...
```

**2. Clean Separation of Concerns**
- Route handler = business logic
- Dependency = cross-cutting concerns (auth, validation, DB connections)

**3. Automatic Documentation**
- FastAPI knows this endpoint requires auth
- Shows it in Swagger UI automatically
- Adds "Authorize" button to test with tokens

**4. Easy Testing**
```python
# In tests, override dependencies
from fastapi.testclient import TestClient

def mock_user():
    return {"email": "test@example.com"}

app.dependency_overrides[get_current_user] = mock_user

# Now all routes using get_current_user will use mock_user instead
client = TestClient(app)
response = client.get("/api/user")  # No need for actual auth!
```

**5. Type Safety**
```python
async def get_current_user(...) -> dict:  # Return type is checked
    ...

@app.get("/user")
async def get_user(current_user: dict = Depends(get_current_user)):
    # current_user is guaranteed to be a dict
    # IDE gives autocomplete and type checking
```

### Common Dependency Patterns

**Optional Authentication:**
```python
from typing import Optional

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    if credentials is None:
        return None
    return decode_token(credentials.credentials)

@app.get("/jobs")
async def get_jobs(current_user: Optional[dict] = Depends(get_current_user_optional)):
    if current_user:
        # Show personalized results
    else:
        # Show public results
```

**Database Connection:**
```python
async def get_db():
    db = Database()
    try:
        yield db
    finally:
        await db.close()

@app.get("/jobs")
async def get_jobs(db: Database = Depends(get_db)):
    return await db.query("SELECT * FROM jobs")
```

**Role-Based Access:**
```python
async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user

@app.delete("/jobs/{id}")
async def delete_job(id: int, admin: dict = Depends(require_admin)):
    # Only admins can reach this code
    ...
```

### Summary

- **Dependency Injection** = FastAPI's way of handling cross-cutting concerns
- **It's not a parameter from the API** = Data comes from request headers/body/cookies
- **It's the standard FastAPI pattern** = Not weird, it's THE way to do it
- **Benefits:** Code reuse, clean separation, auto docs, easy testing, type safety

This pattern is inspired by frameworks like Angular and NestJS, and is one of FastAPI's most powerful features!

---

## REST vs GraphQL

### REST (Representational State Transfer)

**= Standard HTTP endpoints**

```python
GET /jobs           # Get all jobs
GET /jobs/123       # Get job 123
POST /jobs          # Create job
PUT /jobs/123       # Update job
DELETE /jobs/123    # Delete job
```

### GraphQL

**= Query language for APIs**

```graphql
# Single endpoint: POST /graphql
query {
  job(id: "123") {
    title
    company {
      name
      logo
    }
    applications {
      status
    }
  }
}
# Get exactly what you ask for, in one request!
```

### Comparison

| Aspect | REST | GraphQL |
|--------|------|---------|
| **Endpoints** | Multiple (one per resource) | Single (/graphql) |
| **Data fetching** | Fixed structure per endpoint | Request exactly what you need |
| **Multiple resources** | Multiple requests | Single request |
| **Over-fetching** | ❌ Get all fields | ✅ Get only requested fields |
| **Under-fetching** | ❌ Need multiple calls | ✅ Get all data at once |
| **Caching** | ✅ Easy (HTTP caching) | ⚠️ Harder (POST requests) |
| **Learning curve** | ⭐ Easy | ⭐⭐ Medium |
| **Setup time** | ⭐ Fast | ⭐⭐ Slower |
| **Best for** | Simple CRUD, standard APIs | Complex nested data |

### Our Decision: REST (Phase 1)

**Why:**
- Faster to implement for POC
- Simple data model doesn't need GraphQL
- Can add GraphQL in Phase 2 as enhancement

**Interview value:** "Started with REST for speed, can migrate to GraphQL when data relationships become complex"

---

## Stateless vs Stateful

### Stateless Architecture (JWT)

**= Backend stores NO session data**

```
Request 1: Frontend sends JWT → Backend validates → Response
Request 2: Frontend sends JWT → Backend validates → Response
(Backend doesn't remember Request 1)
```

**Pros:**
- ✅ Fast (no database lookup)
- ✅ Scales horizontally easily
- ✅ No shared state between servers

**Cons:**
- ❌ Can't revoke tokens before expiration

### Stateful Architecture (Sessions)

**= Backend stores session data**

```
Request 1: Frontend sends session ID → Backend looks up in DB → Response
Request 2: Frontend sends session ID → Backend looks up in DB → Response
(Backend stores session data)
```

**Pros:**
- ✅ Can revoke immediately
- ✅ Track active sessions

**Cons:**
- ❌ Database lookup on every request
- ❌ Need shared session store (Redis)

### Our Choice: Stateless (JWT)

Better for React + API architecture, easier to scale.

---

## Single vs Multiple Servers

### Can One Server Handle Multiple Endpoints?

**YES!** One backend server can handle unlimited endpoints:

```python
# Single FastAPI server handles ALL endpoints
@app.get("/health")
@app.post("/auth/google")
@app.get("/jobs")
@app.post("/jobs/search")
@app.get("/applications")
# ... hundreds more endpoints
```

### When to Use Multiple Servers?

**Microservices architecture:**

```
API Gateway
    ↓
├─→ Auth Service (handles /auth/*)
├─→ Job Service (handles /jobs/*)
└─→ Scraper Service (handles /scrape/*)
```

**Use when:**
- ✅ Different teams work on different services
- ✅ Services need to scale independently
- ✅ Want to deploy services separately

**For your POC:** Single server is perfect!

---

## Message Queues

### What is a Message Queue?

**= Asynchronous task system**

```
API Server → Queue (tasks waiting) → Workers (process tasks)
```

### Why Use a Queue?

**Without queue:**
```
User: "Scrape 10 companies"
API: Starts scraping... (takes 5 minutes)
User: Waiting... waiting... ⏰
```

**With queue:**
```
User: "Scrape 10 companies"
API: "Job queued! Track progress at /status/123" (instant response)
Workers: Process tasks in background
User: Can do other things, check progress anytime ✅
```

### Benefits

1. **Async processing** - Don't block user
2. **Parallel processing** - Multiple workers
3. **Retry logic** - Failed tasks retry automatically
4. **Rate limiting** - Control scraping speed
5. **Prioritization** - Important jobs first

### Popular Queues

- **AWS SQS** (managed, AWS-native)
- **Redis Queue** (simple, fast)
- **RabbitMQ** (feature-rich)
- **Celery** (Python-specific)

### Our Plan (Phase 3)

```
API: POST /scrape/start
    ↓
Queue: [Company1, Company2, ..., Company10]
    ↓
Workers: 3 workers scrape in parallel
    ↓
Progress updates via WebSocket
```

---

## WebSocket

### What is WebSocket?

**= Two-way real-time communication**

**HTTP (normal):**
```
Client asks → Server responds → Connection closes
(One-way, request-response)
```

**WebSocket:**
```
Client connects → Bidirectional channel stays open
Client ←→ Server (both can send messages anytime)
```

### Use Cases

- ✅ Chat applications
- ✅ Live notifications
- ✅ Real-time dashboards
- ✅ Multiplayer games
- ✅ **Live scraping progress** (our use case!)

### Our Plan (Phase 3)

```javascript
// Frontend connects to WebSocket
const ws = new WebSocket('wss://api.example.com/scrape/live');

ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  // {company: 'Google', progress: 45%, status: 'scraping'}
  updateProgressBar(progress);
};
```

```python
# Backend sends updates
@app.websocket("/scrape/live")
async def scrape_live(websocket: WebSocket):
    await websocket.accept()
    while scraping:
        progress = get_scraping_progress()
        await websocket.send_json(progress)
        await asyncio.sleep(1)
```

---

## Passport.js

### What is Passport.js?

**= Authentication library for Node.js**

**Note:** Only works with Node.js/Express, **NOT Python!**

### Python Equivalent

For Python/FastAPI, use:
- **Authlib** (OAuth library)
- **google-auth** (Google OAuth specifically)
- **python-jose** (JWT handling)

### When You'd Use Passport.js

If you were using **Node.js + Express** backend:

```javascript
const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20');

passport.use(new GoogleStrategy({
  clientID: GOOGLE_CLIENT_ID,
  clientSecret: GOOGLE_CLIENT_SECRET,
  callbackURL: "/auth/google/callback"
}, (accessToken, refreshToken, profile, done) => {
  // Handle user
  return done(null, profile);
}));
```

### Our Stack

We're using **Python + FastAPI**, so we use **google-auth** library instead.

---

**Next:** See [frontend.md](./frontend.md) for React and frontend concepts.
