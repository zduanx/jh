# Architecture Decision Records (ADR)

This document tracks all major architecture and technology decisions made during the project.

---

## ADR-001: Use FastAPI instead of Django

**Date:** 2024-12-13
**Status:** Accepted

### Context
Need to choose a Python backend framework for building a job tracking application with React frontend.

### Decision
Use **FastAPI** as the backend framework.

### Alternatives Considered
- Django (full-featured web framework)
- Flask (lightweight framework)

### Reasoning
1. API-first design - perfect for React frontend
2. Performance - async support, 10x faster than Django
3. Auto-generated API docs (Swagger UI)
4. Modern Python with type hints
5. Learning value - trendy, interview-friendly

### Consequences
✅ Faster API development, better performance, modern stack
❌ Need to choose ORM separately, implement auth manually

---

## ADR-002: Use Google OAuth with Manual Implementation

**Date:** 2024-12-13
**Status:** Accepted

### Decision
Use Google OAuth 2.0 with manual token validation (google-auth library).

### Alternatives Considered
- Auth0 (3rd party service)
- AWS Cognito
- Custom username/password auth

### Reasoning
1. Learning value - understand OAuth deeply
2. No vendor lock-in
3. Free forever
4. Better interview talking points

### Consequences
✅ Deep OAuth understanding, full control, no costs
❌ More code to write vs Auth0

---

## ADR-003: Use JWT Tokens Instead of Sessions

**Date:** 2024-12-13
**Status:** Accepted

### Decision
Exchange Google OAuth token for our own JWT.

### Alternatives Considered
- Pass Google token directly
- Session-based auth with Redis

### Reasoning
1. Performance - no database lookup per request
2. Stateless - easier horizontal scaling
3. Industry standard for modern APIs
4. Control over expiration times

### Consequences
✅ Fast, scalable, standard for React+API
❌ Cannot revoke before expiration (mitigate with short TTL)

---

## ADR-004: Deploy Backend to AWS Lambda + API Gateway

**Date:** 2024-12-13
**Status:** Accepted
**Updated:** 2024-12-13 (Changed from EC2 to Lambda)

### Decision
Use **AWS Lambda + API Gateway** for backend deployment (serverless).

### Alternatives Considered
- AWS EC2 (traditional server)
- Elastic Beanstalk
- AWS Lightsail

### Reasoning
1. **Free forever** - 1M requests/month permanent free tier (vs EC2's 12-month limit)
2. **Auto-scaling** - Handles traffic spikes automatically
3. **Pay per use** - Only pay when API is called (vs EC2 running 24/7)
4. **Modern architecture** - Serverless is industry trend
5. **No server management** - AWS handles everything
6. **FastAPI compatibility** - Works with Mangum adapter
7. **Combined with frontend** - Can serve React + API from Lambda (single deployment)

### Consequences

**Positive:**
- ✅ Truly free for POC (stays free after 12 months)
- ✅ No risk of forgetting to stop EC2 and getting charged
- ✅ Auto-scales (no manual configuration)
- ✅ Modern serverless architecture (great for resume)
- ✅ Can serve both frontend (React) and backend (API) from Lambda
- ✅ API Gateway provides HTTPS automatically

**Negative:**
- ❌ 15-minute timeout (need workaround for long scraping jobs)
- ❌ Cold start latency (~1-2 seconds for first request)
- ❌ More complex debugging (no SSH access)

**Mitigations:**
- For scraping: Use separate solution (EC2 spot instances, ECS, or async queue)
- Cold starts: Acceptable for POC, can add Lambda warming later
- Debugging: Use CloudWatch logs, local testing with SAM

### Implementation Notes
- Use **Mangum** to adapt FastAPI for Lambda
- Use **Lambda Function URLs** or API Gateway for HTTP endpoint
- Serve React build files from Lambda (static files in deployment package)
- Phase 2: Separate long-running scrapers to EC2/ECS

---

## ADR-005: Deploy Frontend to Vercel (Separate from Backend)

**Date:** 2024-12-13
**Status:** Accepted

### Decision
Deploy React frontend to **Vercel**, separate from Lambda backend.

### Alternatives Considered
- Serve from Lambda (combined deployment)
- AWS S3 + CloudFront
- AWS Amplify
- Netlify

### Reasoning
1. **Learn modern deployment** - Experience with popular frontend platform
2. **Separation of concerns** - Frontend and backend scale independently
3. **Zero config** - Connect GitHub, auto-deploy on push
4. **Free forever** - Generous free tier with no time limit
5. **Auto HTTPS** - SSL certificates included
6. **Global CDN** - Fast delivery worldwide
7. **Preview deployments** - Every PR gets a preview URL
8. **Better for learning** - Try different platforms (Vercel + AWS)

### Consequences

**Positive:**
- ✅ Modern frontend deployment workflow
- ✅ Automatic deployments from GitHub
- ✅ Global CDN for fast loading
- ✅ Separation of concerns (frontend/backend independent)
- ✅ Learn both Vercel and AWS
- ✅ Free tier is permanent

**Negative:**
- ❌ Need CORS configuration (backend must allow Vercel domain)
- ❌ Two separate deployments to manage
- ❌ Not "all AWS" (but shows versatility)

**Mitigations:**
- CORS is simple to configure in FastAPI
- Two deployments is standard for modern SPAs
- Shows knowledge of multiple platforms

### Implementation Notes
- Frontend: Push to GitHub → Vercel auto-deploys
- Backend: Deploy Lambda separately
- CORS: Configure `ALLOWED_ORIGINS` in Lambda to include Vercel URL
- Environment variables: Set `REACT_APP_API_URL` to Lambda/API Gateway URL

---

## ADR-006: Use REST API (Not GraphQL) for Phase 1

**Date:** 2024-12-13
**Status:** Accepted

### Decision
Use REST API initially, potentially add GraphQL in Phase 2.

### Reasoning
1. Faster to implement for POC
2. Simple data model doesn't need GraphQL flexibility
3. Can add GraphQL later as enhancement (shows migration skills)

### Consequences
✅ Ship faster, standard caching
❌ Less flexible querying (acceptable for Phase 1)

---

## ADR-008: Lambda Deployment Strategy for Phase 2

**Date:** 2024-12-15
**Status:** Accepted

### Context
Need to decide whether to extend the existing Lambda (main.py) with new HTTP endpoints or create separate Lambda functions for each service.

### Decision
Use a **hybrid approach**:
1. **Extend existing SourceURLLambda** for all HTTP endpoints (auth, sourcing, settings, companies, queue status)
2. **Create separate Lambdas** for SQS-triggered workers (JobCrawlerLambda, JobParserLambda)

### Alternatives Considered
1. **Single monolithic Lambda** - Everything in one function
2. **Full microservices** - Separate Lambda for each endpoint/service

### Reasoning

**For HTTP endpoints (extend SourceURLLambda):**
1. Share authentication logic (JWT validation)
2. Share dependencies and code (extractors, models)
3. Simpler deployment (one SAM template for HTTP)
4. Lower cost (fewer Lambda cold starts)
5. All HTTP endpoints are lightweight API calls

**For SQS workers (separate Lambdas):**
1. Different resource requirements (crawling/parsing is CPU/memory intensive)
2. Independent scaling (workers scale based on queue depth)
3. Isolated failures (worker crash doesn't affect API)
4. Different timeout needs (workers may need longer execution time)
5. Different dependencies (may need headless browser, parsing libraries)

### Consequences

**Positive:**
- ✅ Best of both worlds: simplicity for APIs, separation for workers
- ✅ Easier to deploy and maintain HTTP endpoints
- ✅ Workers can scale independently based on queue load
- ✅ Clear separation of concerns: API vs background processing
- ✅ Can optimize each Lambda separately (memory, timeout, dependencies)

**Negative:**
- ❌ Need to manage shared code between Lambdas (extractors used by both API and workers)
- ❌ More complex than single Lambda (but simpler than full microservices)

### Implementation Notes

**SourceURLLambda (backend/main.py):**
- GET /health
- POST /auth/google
- GET /api/user
- POST /api/sourcing (Phase 2A ✅)
- POST /api/settings (Phase 2B)
- GET /api/settings/:user_id (Phase 2B)
- GET /api/companies (Phase 2B)
- GET /api/queue/status (Phase 2B)

**JobCrawlerLambda (backend/crawler/main.py):**
- Triggered by SQS Queue A
- Uses extractors from backend/extractors/
- Saves HTML to S3, metadata to DB

**JobParserLambda (backend/parser/main.py):**
- Triggered by SQS Queue B
- Uses extractors from backend/extractors/
- Reads HTML from S3, parses, updates DB

**Shared code strategy:**
- Package backend/extractors/ in all Lambda deployment packages
- Consider Lambda Layers for shared dependencies later if needed

---

## ADR-009: Create User Record on First Login (Not on First Settings Change)

**Date:** 2024-12-16
**Status:** Accepted

### Context
Need to decide when to create a user record in the database: immediately after first successful authentication, or lazily when the user first modifies their settings.

### Decision
Create user record **on first login** (during auth callback).

### Alternatives Considered
1. **Create on first login** (chosen)
2. **Create on first settings change** (lazy creation)

### Reasoning

**Why create on first login:**
1. **Simpler downstream logic** - All API endpoints can assume the user exists after authentication
2. **Default settings** - Can provide sane defaults (e.g., crawl all companies, no title filters) without requiring explicit configuration
3. **Future-proof** - Will need user records for crawl history, saved jobs, notifications, etc.
4. **User lifecycle tracking** - Can track `created_at`, `last_login`, and other analytics
5. **Consistent state** - User always exists if they have a valid JWT
6. **Profile freshness** - Update user profile data (name, picture_url) on every login to keep it reasonably fresh

**Why NOT lazy creation:**
- ❌ Need "create if not exists" logic in multiple endpoints
- ❌ Can't track when users first joined vs when they first configured
- ❌ Can't associate future features (crawl history, saved jobs) with unconfigured users
- ❌ More complex error handling ("user not found" scenarios)

**Why update profile on every login:**
- ✅ Keeps cached profile data (name, picture_url) reasonably fresh without extra API calls
- ✅ Already updating `last_login` anyway, minimal extra cost
- ✅ Auto-corrects if user changes name/picture on Google (within days, not real-time)
- ✅ Better UX than showing stale profile pictures for weeks/months

### Consequences

**Positive:**
- ✅ Every authenticated request can assume user exists
- ✅ Can provide default settings immediately
- ✅ Simpler API logic (no "create if not exists" checks)
- ✅ Better analytics and user tracking
- ✅ Easier to add future user-related features

**Negative:**
- ❌ Creates records for users who login once but never use the app
- ❌ Slightly more complex login flow (database write during auth)

**Mitigations:**
- Storage cost is negligible (empty user records are tiny)
- Can add cleanup job later to remove inactive users if needed

### Implementation Notes

**Auth callback flow:**
```python
async def handle_google_callback(token: str):
    # 1. Verify Google token
    user_info = verify_google_token(token)

    # 2. Create or update user record
    user = await db.get_user_by_email(user_info.email)
    if not user:
        # First time login - create user with defaults
        user = await db.create_user(
            email=user_info.email,
            name=user_info.name,
            settings={
                "enabled_companies": ["ALL"],  # or list all company names
                "title_filters": []  # empty = include all
            }
        )
    else:
        # Returning user - update profile data and last_login
        await db.update_user(user.id, name=user_info.name, picture_url=user_info.picture, last_login=now())

    # 3. Generate JWT with user_id
    jwt_token = create_jwt(user.id)
    return jwt_token
```

**Default settings strategy:**
- `enabled_companies`: All companies enabled by default (or explicit list)
- `title_filters`: Empty array = no filtering (include all jobs)
- User can modify these via POST /api/settings

---

## ADR-010: Use BIGSERIAL for User IDs

**Date:** 2024-12-16
**Status:** Accepted

### Context
Need to decide on the primary key strategy for the users table. Options include auto-increment integers (BIGSERIAL), UUIDs (128-bit random), or custom 64-bit random IDs (like Snowflake).

### Decision
Use **BIGSERIAL** (PostgreSQL's 64-bit auto-increment integer) for `user_id`.

### Alternatives Considered
1. **BIGSERIAL** (auto-increment 64-bit) - chosen
2. **UUID** (128-bit random, non-sequential)
3. **Random BIGINT** (64-bit random)
4. **Snowflake ID** (64-bit time-sortable, distributed generation)

### Reasoning

**Why BIGSERIAL:**
1. **Simplest implementation** - Native PostgreSQL feature, no custom logic needed
2. **Best performance** - Smallest size (8 bytes), fastest joins, best index performance
3. **Zero collision risk** - Guaranteed unique by database
4. **Sequential doesn't matter** - User IDs are hidden inside JWT tokens, never exposed in URLs
5. **Single database** - Don't need distributed ID generation
6. **Industry standard** - Used by GitHub, Stack Overflow, Reddit for single-database systems

**Why NOT UUID (128-bit):**
- ❌ 2x storage size (16 bytes vs 8 bytes)
- ❌ Slower joins (string comparison vs integer)
- ❌ Overkill for single-database system
- ✅ Would be useful for distributed databases (not our case)

**Why NOT Random BIGINT:**
- ❌ Tiny collision risk (requires collision handling)
- ❌ More complex code (manual ID generation)
- ✅ Non-sequential (but we don't need this - IDs are in JWT)

**Why NOT Snowflake ID:**
- ❌ Requires custom implementation or library
- ❌ Designed for distributed systems (Twitter-scale)
- ✅ Time-sortable (nice feature, but not critical)
- ✅ Would be useful at massive scale (not our case)

### Security Consideration: Sequential ID Enumeration

**Common concern:** "Sequential IDs allow enumeration attacks (iterate user_id=1,2,3...)"

**Why this doesn't apply to us:**
- ✅ User IDs are **inside JWT tokens**, not in URLs
- ✅ API endpoints use JWT authentication, not user_id in path
- ✅ Users cannot query other users' data (JWT contains their own user_id)
- ✅ No public endpoints expose user_id

**Example secure API design:**
```
GET /api/user
Authorization: Bearer <JWT with user_id inside>

Not:
GET /api/users/123  ← This would be vulnerable to enumeration
```

### Consequences

**Positive:**
- ✅ Simplest possible implementation
- ✅ Best performance (storage, joins, indexes)
- ✅ Zero collision risk
- ✅ Industry-proven approach
- ✅ Easy to understand and maintain

**Negative:**
- ❌ Sequential IDs (but this is not a security risk in our design)
- ❌ Single-database only (can't generate IDs across multiple databases)

**Mitigations:**
- Sequential IDs are hidden in JWT, never exposed
- If we scale to distributed databases later, can migrate to UUIDs or Snowflake IDs

### Implementation

**Database schema:**
```sql
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,  -- Auto-increment 64-bit integer
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,

    INDEX idx_users_email (email)  -- For login lookup
);
```

**Auth flow:**
```python
# Login: Email → user_id lookup (once per login)
user = await db.get_user_by_email(email)  # SELECT user_id FROM users WHERE email = ?

# Create JWT with user_id
jwt = create_jwt({"user_id": user.user_id, "email": user.email})

# Future API requests: Extract user_id from JWT (no DB lookup)
user_id = decode_jwt(token)["user_id"]
```

**ID range:**
- BIGSERIAL range: 1 to 9,223,372,036,854,775,807 (9.2 quintillion)
- More than sufficient for any realistic user base

---

## ADR-011: Use PostgreSQL (SQL) Over NoSQL

**Date:** 2024-12-16
**Status:** Accepted

### Context
Need to choose between SQL (relational) and NoSQL (document/key-value) database for storing user data, settings, and job application tracking.

### Decision
Use **PostgreSQL** (relational SQL database).

### Alternatives Considered
1. **PostgreSQL** (SQL) - chosen
2. **DynamoDB** (NoSQL key-value)
3. **MongoDB** (NoSQL document store)

### Reasoning

**Why PostgreSQL (SQL):**

1. **Data is inherently relational** - Users have settings and job applications (one-to-many relationships with clear foreign keys)
2. **Need complex queries with JOINs** - "Get all interview-stage jobs for user X", "Which users enabled company Y?"
3. **ACID guarantees** - Data consistency is critical for job tracking (e.g., atomically update job status + timestamp)
4. **Structured, predictable schema** - User settings and job applications have fixed fields, schema changes are infrequent
5. **Mature ecosystem** - SQLAlchemy ORM, Alembic migrations, rich tooling
6. **Query flexibility** - Analytics and reporting ("average time from 'applied' to 'interview'", "success rate per company")

**Why NOT DynamoDB (NoSQL):**
- ❌ No JOINs - Would need multiple queries and application-level joins
- ❌ Limited query flexibility - Must design all access patterns upfront
- ❌ Eventually consistent by default - Need strong consistency for job tracking

**Why NOT MongoDB (NoSQL):**
- ❌ Document model doesn't fit - Our data is relational, not hierarchical
- ❌ JOIN support is limited - $lookup is slower than SQL JOINs

### Consequences

**Positive:**
- ✅ Simple, natural data modeling with normalized tables
- ✅ Powerful query capabilities (JOINs, aggregations, complex filters)
- ✅ ACID guarantees for data consistency
- ✅ Mature tooling (ORMs, migrations, admin UIs)
- ✅ Great for analytics and reporting

**Negative:**
- ❌ Requires connection pooling (more setup than DynamoDB)
- ❌ Need to manage schema migrations
- ❌ Vertical scaling limits (but sufficient for our scale)

**Mitigations:**
- Connection pooling is standard practice with SQLAlchemy
- PostgreSQL scales to millions of rows easily (well beyond our needs)

### Related Decisions
- See ADR-012 for PostgreSQL hosting choice (Neon)
- See ADR-013 for ORM and migration strategy (SQLAlchemy + Alembic)
- See ADR-010 for primary key strategy (BIGSERIAL)

---

## ADR-012: Use Neon for PostgreSQL Hosting

**Date:** 2024-12-16
**Status:** Accepted

### Context
After deciding to use PostgreSQL (ADR-011), need to choose a hosting solution for production. Options include managed AWS services (RDS, Aurora) or serverless PostgreSQL providers.

### Decision
Use **Neon** (serverless PostgreSQL) for hosting.

### Alternatives Considered
1. **Neon** (serverless Postgres) - chosen
2. **AWS RDS PostgreSQL** (traditional managed database)
3. **AWS Aurora Serverless** (AWS serverless SQL)

### Reasoning

**Why Neon:**

1. **Easy setup** - 5-minute setup, no VPC configuration, no subnet groups, no parameter groups
2. **Free tier forever** - 0.5 GB storage, 3 GB data transfer/month with no time limit (vs AWS 12-month free trial)
3. **Serverless scaling** - Auto-scales compute and storage, no manual capacity planning
4. **Built for modern apps** - Branch databases for dev/staging, instant point-in-time recovery
5. **PostgreSQL-compatible** - Full PostgreSQL features (extensions, full-text search, pg_trgm)
6. **No upfront cost** - Start free, pay only when you scale beyond free tier

**Why NOT AWS RDS:**
- ❌ Minimum cost ~$15-20/month for production instance
- ❌ Complex setup (VPC, security groups, subnet groups, parameter groups)
- ❌ Manual scaling (must change instance type)
- ❌ Free tier limited to 12 months

**Why NOT Aurora Serverless:**
- ❌ More expensive than RDS for small workloads
- ❌ Complexity of AWS networking (VPC, private subnets)
- ❌ Cold start issues for low-traffic apps
- ✅ Better for high-scale AWS-native architectures (not needed yet)

### Consequences

**Positive:**
- ✅ Start building immediately with no infrastructure setup
- ✅ Free tier sufficient for POC and early users
- ✅ No VPC configuration needed (public endpoint with TLS)
- ✅ Serverless = no capacity planning or instance sizing
- ✅ Great developer experience (branching, instant backups)
- ✅ Can migrate to RDS/Aurora later if needed

**Negative:**
- ❌ Less mature than AWS RDS (Neon is newer)
- ❌ Not AWS-native (connection from Lambda crosses internet, but over TLS)
- ❌ Limited control over infrastructure details

**Mitigations:**
- Use connection pooling (pgbouncer built into Neon)
- Monitor performance and migrate to AWS if needed at scale
- Database migration is straightforward (PostgreSQL → PostgreSQL)

### Related Decisions
- See ADR-011 for SQL vs NoSQL decision
- See ADR-013 for database access strategy (SQLAlchemy + Alembic)

---

## ADR-013: Use SQLAlchemy + Alembic for Database Access

**Date:** 2024-12-16
**Status:** Accepted

### Context
After choosing PostgreSQL and Neon (ADR-011, ADR-012), need to decide how to access the database from Python backend. Options include raw SQL, ORMs, or query builders.

### Decision
Use **SQLAlchemy** (ORM) + **Alembic** (migration tool).

### Alternatives Considered
1. **SQLAlchemy + Alembic** (ORM + migrations) - chosen
2. **Raw SQL with psycopg3** (no ORM)
3. **Django ORM** (requires Django framework)

### Reasoning

**Why SQLAlchemy (ORM):**

1. **Type safety** - Python objects instead of raw SQL strings, catch errors at development time
2. **Pythonic code** - Write `user = User(email="foo@bar.com")` instead of `INSERT INTO users...`
3. **Automatic query generation** - No manual SQL for common CRUD operations
4. **Relationship handling** - Easy to traverse foreign keys (`user.settings`, `user.applications`)
5. **Database portability** - Same Python code works with PostgreSQL, MySQL, SQLite
6. **Mature ecosystem** - Industry standard for Python, well-documented, widely used

**Why Alembic (Migrations):**

1. **Version control for schema** - Track database schema changes in git
2. **Repeatable deployments** - Apply same migrations across dev/staging/prod
3. **Team collaboration** - Multiple developers can safely evolve schema
4. **Rollback support** - Downgrade migrations if needed
5. **Autogeneration** - Can detect model changes and generate migrations automatically
6. **Works with SQLAlchemy** - Designed specifically for SQLAlchemy models

**Why NOT raw SQL:**
- ❌ No type safety - SQL injection risks, typos not caught until runtime
- ❌ More boilerplate - Manual connection handling, result parsing
- ❌ No migration tracking - Schema changes must be managed manually
- ✅ Better performance (but negligible for our scale)

**Why NOT Django ORM:**
- ❌ Requires Django framework (we use FastAPI)
- ❌ More opinionated, less flexible than SQLAlchemy

### Consequences

**Positive:**
- ✅ Type-safe database operations with Python classes
- ✅ Version-controlled schema migrations
- ✅ Less boilerplate code compared to raw SQL
- ✅ Easy to test (can use in-memory SQLite for unit tests)
- ✅ Strong relationship handling (foreign keys, joins)
- ✅ Repeatable deployments across environments

**Negative:**
- ❌ Learning curve (ORM concepts, Alembic workflow)
- ❌ Slight performance overhead vs raw SQL (negligible at our scale)
- ❌ Complex queries may require raw SQL fallback

**Mitigations:**
- SQLAlchemy is well-documented with many examples
- Can always use raw SQL for complex queries (`session.execute()`)
- Performance is sufficient for thousands of users

### Workflow

**Define models:**
```python
class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
```

**Generate migration:**
```bash
alembic revision --autogenerate -m "Add users table"
```

**Apply migration:**
```bash
alembic upgrade head
```

**Use in code:**
```python
user = session.query(User).filter_by(email="foo@bar.com").first()
```

### Related Decisions
- See ADR-011 for PostgreSQL decision
- See ADR-012 for Neon hosting decision

---

## ADR-014: Use Hybrid Text Search (PostgreSQL Full-Text + Fuzzy)

**Date:** 2024-12-16
**Status:** Accepted

### Context
Need to search job descriptions for keywords with typo tolerance. User should be able to type "grapql" and find jobs mentioning "graphql".

### Decision
Use **hybrid search** combining PostgreSQL's full-text search (tsvector) with fuzzy matching (pg_trgm extension).

### Alternatives Considered
1. **Hybrid (tsvector + pg_trgm)** - chosen
2. **Full-text search only** (no typo tolerance)
3. **Fuzzy search only** (pg_trgm trigrams)
4. **Elasticsearch** (dedicated search engine)

### Reasoning

**Why Hybrid (Full-Text + Fuzzy):**

1. **Full-text for semantic matching** - Handles stemming ("running" matches "run"), stop words ("the", "a")
2. **Fuzzy for typo tolerance** - Handles misspellings ("grapql" matches "graphql"), transpositions, missing letters
3. **Native PostgreSQL** - No additional infrastructure (vs Elasticsearch)
4. **Low storage overhead** - ~4 MB full-text + ~12 MB fuzzy per text column for 1,000 jobs (16 MB total)
5. **Fast query performance** - GIN indexes make searches fast even at scale
6. **Cost-effective** - Included in Neon free tier, no separate search service

**Why NOT full-text only:**
- ❌ No typo tolerance - "grapql" won't match "graphql"
- ✅ Good for exact keyword matching and stemming

**Why NOT fuzzy only:**
- ❌ No stemming - "running" won't match "run"
- ❌ Slower for large text blocks (trigrams are expensive)

**Why NOT Elasticsearch:**
- ❌ Additional infrastructure to manage and pay for
- ❌ Overkill for thousands of jobs (not millions)
- ❌ More complex deployment (another service to maintain)
- ✅ Better for massive scale, advanced features (not needed yet)

### Consequences

**Positive:**
- ✅ Typo-tolerant search out of the box
- ✅ No additional infrastructure (uses PostgreSQL)
- ✅ Low storage cost (~16 MB for 1,000 jobs)
- ✅ Fast query performance with GIN indexes
- ✅ Can migrate to Elasticsearch later if needed

**Negative:**
- ❌ Requires two GIN indexes (full-text + trigram)
- ❌ More storage than full-text alone (but still small)
- ❌ Slightly more complex queries (combine two search methods)

**Mitigations:**
- Storage overhead is minimal (16 MB for 1,000 jobs, ~160 MB for 10,000 jobs)
- Query complexity is handled in application layer (users don't see it)

### Implementation

**Database schema:**
```sql
CREATE TABLE jobs (
    job_id BIGSERIAL PRIMARY KEY,
    description TEXT,
    description_tsvector TSVECTOR,  -- Full-text search
    CONSTRAINT ...
);

CREATE INDEX idx_jobs_description_fts ON jobs USING GIN(description_tsvector);
CREATE INDEX idx_jobs_description_fuzzy ON jobs USING GIN(description gin_trgm_ops);
```

**Search query:**
```sql
-- Hybrid search: full-text OR fuzzy match
SELECT * FROM jobs
WHERE description_tsvector @@ to_tsquery('graphql')  -- Full-text
   OR description % 'grapql';  -- Fuzzy (% is similarity operator)
```

**Storage estimation:**
- 1,000 jobs × 5 KB text = 5 MB
- Full-text index: ~4 MB
- Fuzzy index: ~12 MB
- Total: ~21 MB (very affordable)

### Related Decisions
- See ADR-011 for PostgreSQL decision
- See ADR-012 for Neon hosting (includes pg_trgm extension)

---

## ADR-015: Use httpx with asyncio for HTTP Requests

**Date:** 2024-12-22
**Status:** Accepted

### Context
The extractors were using the synchronous `requests` library with `ThreadPoolExecutor` for parallel HTTP requests. Need to decide whether to:
1. Keep `requests` with threading
2. Migrate to `httpx` with native asyncio support

### Decision
Migrate from `requests` to **httpx with async/await** throughout the extractor codebase.

### Alternatives Considered
1. **requests + ThreadPoolExecutor** (previous approach)
2. **httpx async + asyncio.gather** (chosen)
3. **aiohttp** (another async HTTP library)

### Reasoning

**Why httpx async:**

1. **Native asyncio integration** - Works naturally with FastAPI's async handlers
2. **Modern Python patterns** - async/await is more readable than thread callbacks
3. **Single event loop** - All async operations share one loop (no thread overhead)
4. **Better resource efficiency** - No thread pool management, no GIL context switching
5. **API compatibility** - httpx API is similar to requests (easy migration)
6. **Industry standard** - httpx is the recommended async HTTP library for modern Python

**Why NOT keep requests + ThreadPoolExecutor:**
- ❌ Threads add overhead (context switching, memory per thread)
- ❌ GIL limits true parallelism (though I/O-bound work still benefits)
- ❌ Mixing sync requests with async FastAPI creates complexity
- ✅ Was working (but not optimal)

**Why NOT aiohttp:**
- ❌ Different API from requests (steeper learning curve)
- ❌ httpx is more modern and better maintained
- ✅ Also a valid async option

### Technical Details

**Python's GIL (Global Interpreter Lock):**
- Only one thread executes Python bytecode at a time
- Threads release GIL during I/O wait (network, disk)
- For I/O-bound work (HTTP requests), threads still provide parallelism
- For CPU-bound work, need ProcessPoolExecutor to bypass GIL

**ThreadPoolExecutor vs asyncio:**
| Aspect | ThreadPoolExecutor | asyncio |
|--------|-------------------|---------|
| Memory | ~8KB per thread | Shared event loop |
| Switching | OS context switch | Cooperative at await |
| Best for | Sync I/O libraries | Async-native code |
| Complexity | Futures, callbacks | async/await syntax |

### Consequences

**Positive:**
- ✅ Cleaner async code throughout (no thread management)
- ✅ Better fit with FastAPI's async model
- ✅ More efficient resource usage
- ✅ Easier to reason about (single-threaded async)
- ✅ Modern Python best practice

**Negative:**
- ❌ Async propagates upward (all callers must be async)
- ❌ Migration effort (convert all extractors and endpoints)
- ❌ Slightly different error types to handle

**Mitigations:**
- Error type mapping: `requests.Timeout` → `httpx.TimeoutException`
- Response API is nearly identical: `.json()`, `.text`, `.status_code`

### Implementation

**Before (ThreadPoolExecutor):**
```python
def _run_extractor(company_name, filters):
    result = extractor.extract_source_urls_metadata()
    return result

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(_run_extractor, ...): ...}
    for future in as_completed(futures):
        results[company] = future.result()
```

**After (asyncio.gather):**
```python
async def _run_extractor(company_name, filters):
    result = await extractor.extract_source_urls_metadata()
    return result

tasks = [_run_extractor(name, filters) for ...]
results_list = await asyncio.gather(*tasks)
```

### Files Modified
- `backend/extractors/base_extractor.py` - Core async methods
- `backend/extractors/*.py` - All 6 extractors converted
- `backend/api/ingestion_routes.py` - Async dry-run endpoint
- `backend/requirements.txt` - Removed `requests`

### Related
- See [python-fastapi.md](../learning/python-fastapi.md) for GIL and concurrency documentation

---

## ADR-016: Use SSE for Real-Time Progress Updates

**Date:** 2025-12-29
**Status:** Accepted

### Context
Need real-time progress updates during Stage 3 (Sync & Ingest) of the ingestion pipeline.

### Decision
Use **Server-Sent Events (SSE)** as the unified real-time infrastructure for all progress updates.

### Alternatives Considered

| Method | Direction | Complexity | Auto-Reconnect | Infrastructure |
|--------|-----------|------------|----------------|----------------|
| **SSE** | Server → Client | Medium | Built-in | None extra |
| WebSocket | Bi-directional | High | Manual | Connection table in DB |
| Polling | Client → Server | Low | N/A | None extra |

### Reasoning

**Why SSE (chosen):**
1. **One-way is sufficient** - Progress updates only flow server→client
2. **Built-in auto-reconnect** - Browser handles Lambda's 29s API Gateway timeout
3. **No extra infrastructure** - No connection table needed (unlike WebSocket)
4. **Native browser support** - `EventSource` API, no library needed
5. **Industry standard** - Used by Vercel, GitHub, Heroku for similar features

**Why NOT WebSocket:**
- ❌ Bi-directional not needed (client doesn't send during progress)
- ❌ Requires connection table in DB to track active connections
- ❌ Manual reconnect logic required
- ❌ More complex infrastructure (API Gateway WebSocket + DynamoDB/PostgreSQL)
- ✅ Would be useful for: chat, multiplayer, collaborative editing

**Why NOT Polling:**
- ❌ Higher latency (0-3s delay between updates)
- ❌ More Lambda invocations (cost at scale)
- ✅ Simpler, but SSE isn't much harder

### AWS Lambda Constraints

| Component | Timeout |
|-----------|---------|
| API Gateway | 29-30s (hard limit) |
| Lambda execution | Up to 15 min |

**Key insight:** API Gateway cuts the *connection* at 30s, but Lambda can keep *running* in background.

### Architecture

```
┌──────────┐  POST /ingest/start  ┌─────────────┐  Invoke async  ┌────────────────┐
│ Frontend │─────────────────────▶│ API Lambda  │───────────────▶│ Worker Lambda  │
└──────────┘                      │ returns id  │                │ (up to 15 min) │
     │                            └─────────────┘                └───────┬────────┘
     │                                                                   │
     │  SSE /ingest/{id}/stream                                          │
     │  (reconnects every 29s)                                           │
     │                                                                   │
     │                            ┌─────────────┐                        │
     └───────────────────────────▶│  Streamer   │                        │
                                  │  Lambda     │◀───────────────────────┘
                                  └──────┬──────┘     writes progress
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │ PostgreSQL  │
                                  └─────────────┘
```

**Flow:**
1. `POST /ingest/start` → returns `run_id` immediately
2. Worker Lambda runs async, writes progress to DB
3. Frontend connects SSE, reads progress from DB
4. SSE auto-reconnects every 29s (browser handles this)
5. On reconnect, server resumes from `Last-Event-ID`

### SSE Auto-Reconnect Implementation

```python
# Server sends event with ID
yield f"id: {progress['processed']}\n"
yield f"data: {json.dumps(progress)}\n\n"
```

```javascript
// Browser auto-reconnects, sends Last-Event-ID header
const source = new EventSource(`/api/ingest/${runId}/stream`);
source.onmessage = (e) => setProgress(JSON.parse(e.data));
```

### Progress Table Schema

```sql
CREATE TABLE ingestion_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    total INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Consequences

**Positive:**
- ✅ SSE simpler than WebSocket (no connection table)
- ✅ Works with Lambda (auto-reconnect handles 29s timeout)
- ✅ Built-in browser support (`EventSource` API)
- ✅ Free tier compatible (no additional infrastructure)
- ✅ Industry-standard approach (Vercel, GitHub, Heroku)

**Negative:**
- ❌ Brief gap (~1-3s) every 29s during reconnect
- ❌ Need separate worker Lambda for long jobs
- ❌ Progress state must be stored in DB

**Mitigations:**
- Reconnect gap is acceptable for progress updates
- Worker Lambda pattern is standard for async jobs
- DB storage enables resume if user refreshes page

### Related
- See [realtime-progress.md](../learning/realtime-progress.md) for detailed comparison
- Resolves PDR-007

---

## ADR-017: Use SimHash for Raw Content Deduplication

**Date:** 2025-12-29
**Status:** Accepted

### Context
During the ingestion pipeline, we need to skip extraction for pages that haven't meaningfully changed. Extraction is expensive (~100-500ms per page), so detecting unchanged content at the raw crawl stage saves significant resources.

**Challenge:** Job pages contain dynamic noise that changes on every request:
- "Posted 3 days ago" → "Posted 4 days ago"
- "150 applicants" → "180 applicants"
- Timestamps, session IDs, CSRF tokens

Traditional MD5/SHA hashing fails because any byte change produces a completely different hash.

### Decision
Use **SimHash** with a Hamming distance threshold of ≤3 for raw content deduplication.

### Alternatives Considered

| Method | Accuracy | Maintenance | Coverage |
|--------|----------|-------------|----------|
| **SimHash** | High (fuzzy) | None | Universal |
| MD5 + pattern stripping | Medium | High (ongoing) | Limited to known patterns |
| ETag/Last-Modified | Variable | None | ~30% of sites support |
| Extract-then-compare | Perfect | None | Too expensive |

### How SimHash Works

SimHash produces a 64-bit fingerprint where **similar content produces similar hashes**:

```
Traditional Hash:
  "Hello World" → a1b2c3d4
  "Hello World!" → 9f8e7d6c  ← completely different

SimHash:
  "Hello World" → 1010110101...
  "Hello World!" → 1010110100...  ← only 1-2 bits different
```

**Algorithm:**
1. Tokenize text into 3-word shingles
2. Hash each shingle to 64 bits
3. Weight each bit position (+1 or -1)
4. Final hash: bit=1 if sum>0, else bit=0

**Comparison:** Count differing bits (Hamming distance)

### Implementation

```python
from simhash import Simhash
from bs4 import BeautifulSoup

SIMHASH_THRESHOLD = 3  # Industry standard

def compute_simhash(html: str) -> int:
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup.select('script, style, nav, footer, header'):
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True).lower()
    words = text.split()

    if len(words) < 3:
        return 0

    features = [' '.join(words[i:i+3]) for i in range(len(words) - 2)]
    return Simhash(features).value

def hamming_distance(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count('1')

def is_unchanged(old_hash: int, new_hash: int) -> bool:
    return hamming_distance(old_hash, new_hash) <= SIMHASH_THRESHOLD
```

### Threshold Reference (64-bit hash)

| Distance | Similarity | Action |
|----------|------------|--------|
| 0-3 | ~95-99% | Skip extraction (unchanged) |
| 4-7 | ~90-95% | Minor edits, consider skipping |
| 8-15 | ~75-90% | Moderate changes, extract |
| 16+ | <75% | Significant changes, extract |

### Schema Update

```sql
ALTER TABLE ingestion_url_status ADD COLUMN simhash BIGINT;
```

### Reasoning

**Why SimHash (chosen):**
1. **No pattern maintenance** - Works on any site without site-specific rules
2. **Handles unknown noise** - New dynamic content types auto-handled
3. **Industry proven** - Used by Google, search engines for near-duplicate detection
4. **Tunable threshold** - Can adjust sensitivity if needed
5. **Fast** - ~15ms per page (vs ~100-500ms extraction)

**Why NOT MD5 + pattern stripping:**
- ❌ Impossible to cover all sites' noise patterns
- ❌ Ongoing maintenance as sites change
- ❌ False confidence - you miss edge cases
- ❌ Brittle - site redesigns break patterns

**Why NOT ETag only:**
- ❌ Only ~30% of job boards support it
- ✅ Use as optimization when available, but need fallback

### Consequences

**Positive:**
- ✅ Universal coverage across all job sites
- ✅ Zero maintenance for noise patterns
- ✅ Saves ~80% extraction cost on repeat crawls
- ✅ Simple threshold-based decision (≤3 = unchanged)
- ✅ 8-byte storage per URL (BIGINT)

**Negative:**
- ❌ ~15ms CPU per page (vs ~5ms for MD5)
- ❌ External dependency (`pip install simhash`)
- ❌ Small risk of false negatives (real changes within 3 bits)

**Mitigations:**
- 15ms is negligible at 500 URLs scale
- `simhash` library is stable and well-maintained
- Threshold of 3 is conservative; can lower to 2 if seeing false negatives

### Pipeline Integration

```
GET page
    ↓
Compute SimHash (~15ms)
    ↓
Compare with stored SimHash
    ↓
Distance ≤ 3? → Skip extraction, mark unchanged
    ↓ no
Save to S3 → Queue for extraction
```

### Related
- Used by: Google (web dedup), Common Crawl, Scrapy
- See also: MinHash (for set similarity), LSH (for efficient lookup)

---

## ADR-018: SSE Update Strategy - Full State on Connect, Diffs During Session

**Date:** 2025-01-01
**Status:** Accepted

### Context
The SSE progress endpoint needs to stream job-level status updates during ingestion. With ~500 jobs per run, we need to decide how to handle:
1. Initial data load when client connects
2. Ongoing updates during the session
3. Reconnection after API Gateway's 29s timeout

### Decision
Use **full state on connect, diffs during session**:
- On every connect/reconnect: emit `all_jobs` event with complete job status map
- During session: emit `update` events with only changed jobs
- On terminal status: emit `status` event and close

### Alternatives Considered

| Strategy | Bandwidth | Complexity | Reconnect Handling |
|----------|-----------|------------|-------------------|
| **Full + Diffs** (chosen) | ~30KB connect + ~0.5KB/update | Medium | Simple (always send all_jobs) |
| Full state every poll | ~25KB × 10/min = 250KB/min | Low | N/A (always full) |
| Diffs only + client state sync | Minimal | High | Complex (version tracking) |
| Client sends last state on reconnect | Minimal | High | URL length limits (2KB) |

### Event Format

Uses SSE native `event:` field (not JSON type). Data structures are consistent nested objects.

**Unique key**: `company` + `external_id`

```
// Run status (pending/initializing/terminal)
event: status
data: pending

// Full job state on connect/reconnect (when status = ingesting)
event: all_jobs
data: {
  "google": [
    {"external_id": "123", "title": "Software Engineer", "status": "pending"},
    {"external_id": "456", "title": "ML Engineer", "status": "ready"}
  ],
  "amazon": [...]
}

// Status changes only (grouped by company, multiple jobs per update)
event: update
data: {"google": {"123": "crawling", "456": "ready"}, "amazon": {"789": "error"}}

// Terminal
event: status
data: finished
```

**Data structures**:
- `all_jobs`: `{company: [{external_id, title, status}, ...]}`
- `update`: `{company: {external_id: status, ...}}`

### Reasoning

**Why full state on connect:**
1. **Simple reconnect logic** - No version tracking, no client state sync
2. **25KB is small** - Single fetch, comparable to loading a small image
3. **Infrequent** - Only on initial connect + every 29s reconnect
4. **Robust** - Client always has correct state after any disconnect

**Why diffs during session:**
1. **Efficient** - ~500 bytes vs 25KB per update
2. **10 updates/min** - Saves ~240KB/min bandwidth
3. **SSE maintains local state** - Simple dict comparison in generator
4. **Frontend just applies patches** - No complex merge logic

**Why NOT client-sends-state on reconnect:**
- URL length limit (~2KB) exceeded with 500 jobs
- Would need POST for reconnect (breaks EventSource simplicity)
- Added complexity for minimal bandwidth savings

**Why NOT version-based diffs:**
- Server needs to track versions per run
- Client needs to track and send last version
- Complex edge cases (missed versions, gaps)
- Overkill for 29s reconnect interval

### Bandwidth Analysis

```
Per minute (ingesting phase):
- Full state: 25KB on connect
- Updates: ~0.5KB × 20 = 10KB
- Total: ~35KB first minute, ~10KB subsequent

Per 29s reconnect cycle:
- Reconnect overhead: 25KB
- Updates: ~0.5KB × 10 = 5KB
- Total: ~30KB per cycle

Comparison with "always full state":
- Always full: 25KB × 20/min = 500KB/min
- Our approach: ~35KB first min, ~10KB after
- Savings: ~90% bandwidth reduction
```

### Implementation

**SSE Generator (simplified):**
```python
async def _progress_generator(run_id: int, user_id: int):
    previous_statuses = {}  # Track for diff computation
    sent_all_jobs = False

    while True:
        run = db.query(IngestionRun).filter_by(id=run_id).first()

        if run.status in ["pending", "initializing"]:
            yield sse_event("status", run.status)

        elif run.status == "ingesting":
            current_statuses = get_job_statuses(run_id)  # {company:id: status}

            if not sent_all_jobs:
                yield sse_event("all_jobs", group_by_company(current_statuses))
                sent_all_jobs = True
                previous_statuses = current_statuses
            else:
                diff = compute_diff(previous_statuses, current_statuses)
                if diff:
                    yield sse_event("update", diff)
                previous_statuses = current_statuses

        elif run.status in RunStatus.TERMINAL:
            yield sse_event("status", run.status)
            break

        await asyncio.sleep(3)
```

### Consequences

**Positive:**
- ✅ Simple reconnect (always works, no state sync)
- ✅ Efficient bandwidth (~90% reduction vs always-full)
- ✅ Frontend logic is straightforward (replace on all_jobs, patch on update)
- ✅ No version tracking infrastructure
- ✅ Works with EventSource auto-reconnect

**Negative:**
- ❌ 25KB overhead on each reconnect (acceptable)
- ❌ SSE generator maintains state (memory per connection)
- ❌ Slight complexity in diff computation

**Mitigations:**
- 25KB is small (typical image is larger)
- State is just a dict, cleared when connection closes
- Diff is simple dict comparison

### Related
- See ADR-016 for SSE architecture decision
- Resolves SSE update strategy for Phase 2G

---

## ADR-019: Configurable CloudWatch Log Groups for Multi-Worker Logging

**Date:** 2025-01-08
**Status:** Accepted

### Context
Phase 2J introduces multiple Lambda workers (Crawler, Extractor) in addition to the existing Ingestion worker. Each Lambda automatically gets its own CloudWatch log group. The existing `/ingestion/{run_id}/logs` endpoint hardcodes a single log group, but we need to query logs from multiple workers.

### Decision
Make log groups **frontend-configurable** via query parameter, with backend mapping short names to full log group paths.

### Alternatives Considered

| Approach | Flexibility | Frontend Complexity | Backend Complexity |
|----------|-------------|---------------------|-------------------|
| **Query param with backend mapping** (chosen) | High | Low | Low |
| Hardcode all groups in backend | Low | None | Low (but coupled) |
| Frontend sends full log group paths | High | High (knows AWS internals) | None |
| Separate endpoint per worker | Low | High (multiple polls) | High |

### API Design

```
GET /ingestion/{run_id}/logs?groups=ingestion,crawler,extractor
```

**Backend mapping:**
```python
LOG_GROUP_MAP = {
    "ingestion": "/aws/lambda/jh-IngestionWorkerFunction",
    "crawler": "/aws/lambda/jh-CrawlerWorkerFunction",
    "extractor": "/aws/lambda/jh-ExtractorWorkerFunction",
}
```

**Behavior:**
- No `groups` param → query all groups (default)
- `groups=ingestion` → just ingestion logs
- `groups=crawler,extractor` → both crawler and extractor

### Reasoning

**Why configurable groups:**
1. **Frontend controls scope** - Can show all logs or filter to specific worker
2. **Backend stays generic** - Adding new worker = add to map, no API change
3. **Single request** - Frontend makes one poll, backend merges results
4. **Debugging flexibility** - Easy to isolate logs from specific worker

**Why backend mapping (not raw paths):**
1. **Security** - Frontend can't query arbitrary log groups
2. **Abstraction** - Frontend doesn't need to know AWS naming conventions
3. **Consistency** - Short names are stable even if log group paths change

**Why NOT hardcode all groups:**
- ❌ Every new worker requires backend code change
- ❌ Can't filter to specific worker type
- ✅ Simpler initially, but doesn't scale

**Why NOT separate endpoints:**
- ❌ Multiple polling loops in frontend
- ❌ Complex to merge/sort logs client-side
- ❌ More API Gateway invocations

### Implementation

**Backend (query multiple groups, merge results):**
```python
@router.get("/{run_id}/logs")
async def get_logs(run_id: int, groups: str = None):
    # Default to all groups if not specified
    group_keys = groups.split(",") if groups else LOG_GROUP_MAP.keys()

    all_logs = []
    for key in group_keys:
        if key in LOG_GROUP_MAP:
            logs = query_cloudwatch(LOG_GROUP_MAP[key], run_id)
            for log in logs:
                log["source"] = key  # Tag source for frontend
            all_logs.extend(logs)

    # Sort by timestamp across all sources
    all_logs.sort(key=lambda x: x["timestamp"])
    return {"logs": all_logs}
```

**Response format:**
```json
{
  "logs": [
    {"timestamp": 1704700000, "message": "Starting crawl", "source": "crawler"},
    {"timestamp": 1704700001, "message": "Extracting job 123", "source": "extractor"},
    {"timestamp": 1704700002, "message": "Saving to DB", "source": "ingestion"}
  ]
}
```

### Consequences

**Positive:**
- ✅ Single API call returns merged, sorted logs from all workers
- ✅ Frontend can filter by source if needed (color-coding, tabs)
- ✅ Adding new workers only requires updating LOG_GROUP_MAP
- ✅ Secure (can't query arbitrary log groups)
- ✅ Clean abstraction (frontend uses short names)

**Negative:**
- ❌ Backend makes N CloudWatch API calls (one per group)
- ❌ Slight latency increase for multi-group queries

**Mitigations:**
- CloudWatch queries are fast (~50-100ms each)
- Can parallelize queries with asyncio.gather if needed
- 3 groups × 100ms = 300ms (acceptable)

### Related
- See ADR-016 for SSE progress updates
- Extends existing `/ingestion/{run_id}/logs` endpoint

---

## ADR-020: SQS FIFO with MessageGroupId for Crawler Rate Limiting

**Date:** 2025-01-09
**Status:** Accepted

### Context
Phase 2J Crawler Lambda needs to space requests per company (e.g., 2s between Google requests) to avoid detection. With multiple concurrent workers, we need distributed rate limiting.

### Decision
Use **SQS FIFO queue with MessageGroupId per company** + **sleep before message deletion**.

### Alternatives Considered

| Approach | Coordination | Complexity | Rate Limiting |
|----------|--------------|------------|---------------|
| **FIFO + MessageGroupId + sleep** (chosen) | None | Low | Exact |
| Standard SQS + DelaySeconds | None | Low | Approximate (max 900s, bursts if slow) |
| Standard SQS + DynamoDB lock | DynamoDB | High | Exact (but lock contention) |
| Multiple queues (one per company) | None | Medium | Exact (but 6 queues to manage) |

### How It Works

```
FIFO Queue Behavior:
- MessageGroupId = company name ("google", "amazon", etc.)
- Only ONE message per group in-flight at a time
- Other messages in same group blocked until current deleted

Rate Limiting Timeline (google group):
T=0s   Lambda receives msg1, crawls
T=1s   Crawl complete
T=2s   sleep(1) done, Lambda returns → msg1 deleted
T=2s   msg2 becomes available → 2+ second gap enforced
```

### Why FIFO + MessageGroupId

1. **Zero contention** - 6 companies = max 6 Lambdas active, no lock competition
2. **Exactly-once** - 5-min deduplication via `MessageDeduplicationId`
3. **No external state** - No DynamoDB/Redis, rate limiting in queue semantics
4. **Built-in retry** - Failed messages reappear after VisibilityTimeout

### Key Configuration

| Setting | Value | Reason |
|---------|-------|--------|
| Lambda Timeout | 60s | Enough for HTTP + S3 save |
| VisibilityTimeout | 120s | > Lambda timeout + buffer |
| Sleep before return | 1s | Rate limit gap |
| BatchSize | 1 | One message at a time |
| Internal retry | 3 attempts, 1s backoff | Before marking job ERROR |
| Circuit breaker | 5 failures per company | Skip remaining jobs for that company |

### Failure Handling

| Scenario | Behavior |
|----------|----------|
| Crawl fails (3 internal retries) | Increment `run_metadata[{company}_failures]`, mark job ERROR |
| S3/SimHash error | Same as crawl fail |
| Circuit breaker (5 failures) | Skip remaining jobs for company, mark as ERROR |
| Run aborted | Check run.status before processing, skip if ABORTED |
| Lambda timeout/crash | Message reappears after VisibilityTimeout (SQS retry) |

### Consequences

**Positive:**
- No external coordination, exact rate limiting per company
- Scales naturally (more companies = more parallel workers)
- Circuit breaker prevents wasting time on broken company APIs

**Negative:**
- FIFO 300 msg/s limit (fine for ~3 msg/s crawling)
- No DLQ means failed messages eventually succeed or hit circuit breaker

### Related
- [ADR-017](./DECISIONS.md#adr-017-use-simhash-for-raw-content-deduplication): SimHash deduplication
- [ADR-019](./DECISIONS.md#adr-019-configurable-cloudwatch-log-groups-for-multi-worker-logging): CloudWatch log groups
- Phase 2J: Crawler infrastructure
- Phase 2K: Extractor infrastructure (separate queue)