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

---

## ADR-021: Standard SQS with Reserved Concurrency for Extractor Rate Limiting

**Date:** 2026-01-10
**Status:** Accepted

### Context
Phase 2K ExtractorWorker needs to read HTML from S3, extract job descriptions/requirements, and save to Neon database. Unlike CrawlerWorker (which hits external career sites), ExtractorWorker only accesses our own infrastructure. However, we need to protect Neon from connection exhaustion and high QPS.

### Decision
Use **Standard SQS queue** with **ReservedConcurrentExecutions=5** and **BatchSize=1**.

### Alternatives Considered

| Approach | Concurrency Control | Retry Semantics | Complexity |
|----------|---------------------|-----------------|------------|
| **Standard SQS + Reserved Concurrency** (chosen) | Lambda limit | Simple (auto-retry) | Low |
| Standard SQS + BatchSize=10 | Fewer Lambdas | Complex (partial failure) | Medium |
| FIFO with single MessageGroupId | Sequential only | Simple | Low but slow |
| FIFO with MessageGroupId per company | 6 concurrent | Simple | Low |
| No queue (inline in CrawlerWorker) | Tied to crawler | N/A | Low but coupled |

### Why Standard SQS (not FIFO)

Unlike CrawlerWorker, ExtractorWorker has no external rate limiting requirements:
- Reads from our S3 bucket (no third-party throttling)
- Writes to our Neon database (we control the limits)
- No per-company ordering needed

FIFO overhead (300 msg/s limit, deduplication) provides no benefit here.

### Why BatchSize=1 (not 10)

| Factor | BatchSize=1 | BatchSize=10 |
|--------|-------------|--------------|
| Retry semantics | Simple - failed job retries alone | Complex - entire batch retries |
| Partial failure | N/A | Must manually delete successful messages |
| Error isolation | One bad job doesn't affect others | One stuck job delays batch |
| Code complexity | Simple loop | Batch result reporting, partial ack |
| Lambda cost | More invocations | Fewer invocations |

With SQS Lambda trigger, if Lambda throws, the **entire batch** goes back to queue. Handling partial success requires manually deleting successful messages, losing SQS's built-in retry/DLQ behavior:

```python
# Complex batch handling (avoided)
for msg in batch:
    try:
        process(msg)
        sqs.delete_message(msg.receipt_handle)  # Manual delete
    except:
        pass  # Leave in queue for retry
# Must return success even if some failed
```

The simplicity of BatchSize=1 outweighs batch efficiency gains for our low-volume use case.

### Why ReservedConcurrentExecutions=5

**Neon protection:**
- Each Lambda = 1 DB connection
- 5 Lambdas = 5 max connections (Neon free tier has 100)
- Prevents connection exhaustion during bursts

**QPS estimation:**
- Extraction: ~200-500ms per job (S3 read + parse + DB write)
- 5 Lambdas × 2-5 jobs/sec = 10-25 QPS
- Well within Neon capacity

**Comparison to CrawlerWorker:**
- CrawlerWorker: 6 concurrent (one per company via FIFO MessageGroupId)
- ExtractorWorker: 5 concurrent (via ReservedConcurrentExecutions)
- Similar concurrency, different mechanisms for different needs

### Configuration

| Setting | Value | Reason |
|---------|-------|--------|
| Queue Type | Standard | No rate limiting needed |
| BatchSize | 1 | Simple retry semantics |
| ReservedConcurrentExecutions | 5 | Limit DB connections |
| VisibilityTimeout | 60s | Longer than Lambda timeout |
| Lambda Timeout | 30s | Extraction is fast |

### Message Flow

```
CrawlerWorker (success, content changed)
    ↓
SendMessage to ExtractorQueue
    ↓
ExtractorWorker (max 5 concurrent)
    ├── Read HTML from S3
    ├── Call extract_raw_info() for company
    ├── Save description/requirements to jobs table
    └── Mark job status = 'ready'
```

### Skipped Jobs

When CrawlerWorker detects unchanged content (SimHash match), it:
- Marks job as `skipped` directly
- Does NOT send to ExtractorQueue
- Existing extracted data remains valid

### Run Finalization

After each job, ExtractorWorker checks if all jobs for the run are in terminal state (ready/skipped/error). If so, marks run as `finished`. Race condition is harmless - multiple workers may both see "0 remaining" and mark finished (idempotent).

### Consequences

**Positive:**
- Simple retry semantics with BatchSize=1
- Bounded DB connections (max 5)
- Higher throughput than FIFO (no ordering overhead)
- Decoupled from CrawlerWorker (independent retries)

**Negative:**
- More Lambda invocations than batching (slightly higher cost)
- No exactly-once semantics (at-least-once is fine for idempotent updates)

### Related
- [ADR-020](./DECISIONS.md#adr-020-sqs-fifo-with-messagegroupid-for-crawler-rate-limiting): CrawlerWorker FIFO queue
- [ADR-017](./DECISIONS.md#adr-017-use-simhash-for-raw-content-deduplication): SimHash skip logic
- [ADR-022](./DECISIONS.md#adr-022-distributed-run-finalization): Run finalization
- Phase 2K: Extractor infrastructure

---

## ADR-022: Distributed Run Finalization

**Date:** 2026-01-10
**Status:** Accepted

### Context
With distributed workers (CrawlerWorker and ExtractorWorker), we need a strategy to detect when all jobs for a run are complete and mark the run as `finished`. Multiple workers process jobs concurrently, so any worker could be the "last" one.

### Decision
**Each worker checks for run completion after processing a job.** If no pending jobs remain, the worker marks the run as `finished`.

### Job Status State Machine

```
pending → ready      (crawl + extraction success)
pending → skipped    (SimHash match, content unchanged)
pending → error      (crawl or extraction failed)
pending → expired    (job not in current extraction results)
```

**Terminal statuses:** `ready`, `skipped`, `error`, `expired`
**Non-terminal:** `pending`

### Who Sets What Status

| Worker | Status | Condition |
|--------|--------|-----------|
| IngestionWorker | `pending` | UPSERT all jobs at run start |
| IngestionWorker | `expired` | Job not in current extraction results |
| CrawlerWorker | `skipped` | SimHash match (content unchanged) |
| CrawlerWorker | `error` | Crawl failed after 3 retries |
| ExtractorWorker | `ready` | Extraction success |
| ExtractorWorker | `error` | Extraction failed |

### Finalization Logic

After setting a terminal status, worker executes:

```sql
-- Step 1: Check if any pending jobs remain
SELECT COUNT(*) FROM jobs
WHERE run_id = :run_id AND status = 'pending';

-- Step 2: If count = 0, finalize run
UPDATE ingestion_runs
SET status = 'finished',
    finished_at = NOW(),
    jobs_ready = (SELECT COUNT(*) FROM jobs WHERE run_id = :run_id AND status = 'ready'),
    jobs_skipped = (SELECT COUNT(*) FROM jobs WHERE run_id = :run_id AND status = 'skipped'),
    jobs_failed = (SELECT COUNT(*) FROM jobs WHERE run_id = :run_id AND status = 'error')
WHERE id = :run_id
  AND status = 'ingesting';
```

### Race Condition Handling

Two workers finish simultaneously:
```
Worker A: finishes job 99, sees 0 pending → marks run finished
Worker B: finishes job 100, sees 0 pending → tries to mark run finished
```

The `AND status = 'ingesting'` guard makes this idempotent:
- First UPDATE succeeds, changes status to `finished`
- Second UPDATE affects 0 rows (status no longer `ingesting`)

No locks needed. Both workers can safely attempt finalization.

### Which Workers Finalize

| Worker | Can Finalize? | When |
|--------|---------------|------|
| CrawlerWorker | ✅ | After setting `skipped` or `error` |
| ExtractorWorker | ✅ | After setting `ready` or `error` |

Both check because either could process the last job:
- If all jobs are SimHash matches → CrawlerWorker sets all to `skipped` → CrawlerWorker finalizes
- If all jobs need extraction → ExtractorWorker sets last to `ready` → ExtractorWorker finalizes
- Mixed scenario → whichever worker processes the last pending job finalizes

### Consistency Guarantees

Using single Neon primary with READ COMMITTED isolation:
- All writes go to same master
- Once a transaction commits, other transactions see it on next query
- No async replication lag (that's only for read replicas)

The finalization check (`SELECT COUNT(*)`) will see all committed job status updates.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Worker-based check** (chosen) | Simple, no extra infra | Every worker checks |
| Dedicated finalizer Lambda | Single responsibility | Extra Lambda, timing complexity |
| Frontend polling triggers | Offloads to client | Unreliable if user closes browser |
| SQS message counting | Event-driven | Complex state tracking |

### Consequences

**Positive:**
- No additional infrastructure
- Works with any number of concurrent workers
- Idempotent - safe with race conditions
- Immediate finalization when last job completes

**Negative:**
- Extra DB query per job (check pending count)
- Multiple workers may attempt finalization (but only one succeeds)

### Related
- [ADR-021](./DECISIONS.md#adr-021-standard-sqs-with-reserved-concurrency-for-extractor-rate-limiting): ExtractorWorker concurrency
- [ADR-020](./DECISIONS.md#adr-020-sqs-fifo-with-messagegroupid-for-crawler-rate-limiting): CrawlerWorker queue
- Phase 2K: Extractor infrastructure

---

## ADR-023: Separate Events Table vs JSONB for Job Tracking

**Date:** 2026-01-21
**Status:** Accepted
**Phase:** 4A

### Context

Phase 4 introduces job tracking where users can track jobs they're interested in and log events (phone screens, interviews, offers, etc.). We need to decide how to store these events.

A complete job tracking cycle involves multiple events per job:
- Phone screen: date, time, location, notes
- Technical interview: date, time, location, notes
- Onsite: date, time, location, notes
- Offer/rejection: date, notes

We also want a calendar view showing upcoming events across all tracked jobs.

### Decision

Use a **separate `tracking_events` table** instead of JSONB array in the tracking table.

### Alternatives Considered

**Option A: JSONB array in job_tracking table**
```python
events: Mapped[list] = mapped_column(JSONB, default=list)
# [{"type": "phone_screen", "date": "2026-01-15", "time": "14:00", "location": "Zoom", "note": "..."}]
```

**Option B: Separate tracking_events table** (chosen)
```sql
tracking_events:
- id (PK)
- tracking_id (FK job_tracking)
- event_type (varchar)
- event_date (date)
- event_time (time, nullable)
- location (text, nullable)
- note (text, nullable)
- created_at (timestamp)
```

### Reasoning

| Requirement | JSONB | Separate Table |
|-------------|-------|----------------|
| Calendar query: "all interviews this week" | Hard - scan all rows, parse JSON | Easy - `WHERE event_date BETWEEN ... AND type = 'interview'` |
| Sort events by date across jobs | App-side after fetching all | `ORDER BY event_date` |
| Index on event_date | Not possible | Yes |
| Add new event fields | Schema-less, flexible | Requires migration |
| Query complexity | Single table read | JOIN required |

The calendar view is the deciding factor. With JSONB, showing "all events this week" requires:
1. Fetching ALL tracked jobs for the user
2. Parsing JSON arrays in application code
3. Filtering and sorting in memory

With a separate table:
```sql
SELECT te.*, jt.job_id, j.title, j.company
FROM tracking_events te
JOIN job_tracking jt ON te.tracking_id = jt.id
JOIN jobs j ON jt.job_id = j.id
WHERE jt.user_id = :user_id
  AND te.event_date BETWEEN :start AND :end
ORDER BY te.event_date, te.event_time;
```

### Performance Considerations

JOINs are not a concern at this scale:
- Expected: ~50-100 tracked jobs per user, ~3-5 events per job = ~500 events max
- With indexes on `tracking_id` and `event_date`, query time is < 1ms
- PostgreSQL handles millions of rows with proper indexes

### Schema

**job_tracking table:**
```sql
CREATE TABLE job_tracking (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    stage VARCHAR(20) DEFAULT 'interested',
    notes TEXT,
    resume_s3_url TEXT,
    tracked_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, job_id)
);
```

**tracking_events table:**
```sql
CREATE TABLE tracking_events (
    id SERIAL PRIMARY KEY,
    tracking_id INTEGER REFERENCES job_tracking(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME,
    location TEXT,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tracking_events_tracking_id ON tracking_events(tracking_id);
CREATE INDEX idx_tracking_events_date ON tracking_events(event_date);
```

### Event Types

| Type | Description |
|------|-------------|
| `phone_screen` | Initial recruiter call |
| `technical` | Technical phone/video interview |
| `onsite` | On-site or virtual panel |
| `hiring_manager` | Hiring manager interview |
| `offer` | Offer received |
| `negotiation` | Salary/terms negotiation |
| `accepted` | Offer accepted |
| `rejected` | Application rejected |
| `withdrawn` | User withdrew application |
| `other` | Custom event type |

### Consequences

**Positive:**
- Efficient calendar queries with date range filtering
- Can index event_date for fast lookups
- Clean separation of concerns (tracking vs events)
- Standard relational design, easy to understand

**Negative:**
- Extra table and JOINs (negligible at this scale)
- Less flexible than schema-less JSONB
- Migration required to add new event fields

### Related
- Phase 4A: Job tracking database design
- Phase 4C: Calendar view implementation

---

## ADR-024: Presigned URLs for Resume Upload (Direct-to-S3)

**Date:** 2026-01-28
**Status:** Accepted
**Phase:** 4D

### Context

Phase 4D adds resume upload functionality for tracked jobs. We need to decide how files flow from the browser to S3 storage.

### Decision

Use **presigned URLs for direct-to-S3 upload** instead of proxying files through the backend.

### Alternatives Considered

**Option A: File through backend (multipart form)**
```
Frontend  →  Backend (FastAPI)  →  S3
   │              │                 │
   │   POST file  │                 │
   │─────────────→│   put_object    │
   │              │────────────────→│
   │   response   │                 │
   │←─────────────│←────────────────│
```

**Option B: Presigned URL (direct-to-S3)** (chosen)
```
Frontend  →  Backend     Frontend  →  S3
   │            │           │          │
   │ GET URL    │           │          │
   │───────────→│           │          │
   │ presigned  │           │          │
   │←───────────│           │          │
   │            │  PUT file directly   │
   │────────────────────────────────→  │
   │ POST confirm           │          │
   │───────────→│           │          │
```

### Reasoning

| Factor | File Through Backend | Presigned URL |
|--------|---------------------|---------------|
| Lambda memory usage | High (holds file in memory) | None (file bypasses Lambda) |
| Lambda timeout risk | Yes (30s limit, 15-min max) | No (upload doesn't involve Lambda) |
| Network hops | 2 (browser→Lambda→S3) | 1 (browser→S3) |
| Upload speed | Slower (extra hop) | Faster (direct) |
| API Gateway payload | Limited (10MB) | N/A (bypassed) |
| Code complexity | Lower (single endpoint) | Higher (3 endpoints) |

**Key constraints:**
1. **API Gateway payload limit**: 10MB max for synchronous requests
2. **Lambda memory**: Files held in memory during upload
3. **Lambda timeout**: 30s for API Gateway integration (15-min max for async)

Presigned URLs avoid all these constraints by having the browser upload directly to S3.

### Implementation

**Endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `GET /resume/upload-url` | Generate presigned PUT URL (5 min expiry) |
| `POST /resume/confirm` | Save S3 key + filename to database |
| `GET /resume/url` | Generate presigned GET URL for download/preview |

**Upload flow:**
```javascript
// 1. Get presigned URL from backend
const { upload_url, s3_key } = await fetch(`/api/tracked/${id}/resume/upload-url`);

// 2. Upload file directly to S3
await fetch(upload_url, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/pdf' },
  body: file,
});

// 3. Confirm upload with backend (saves to DB)
await fetch(`/api/tracked/${id}/resume/confirm`, {
  method: 'POST',
  body: JSON.stringify({ s3_key, filename: file.name }),
});
```

**S3 key structure:**
```
s3://jobhunt-resume-content-{account_id}/
  └── resumes/
      └── {user_id}/
          └── {tracking_id}.pdf
```

Simple key with no timestamp - re-uploading overwrites the existing file.

**Security:**
- Presigned URL expires in 5 minutes
- S3 key is validated against expected pattern (`resumes/{user_id}/{tracking_id}.pdf`)
- User can only upload to their own tracking records (verified by JWT)
- Presigned URL is scoped to specific bucket/key with `put_object` permission only

### Presigned URL Generation

```python
# No network call - SDK signs locally using AWS credentials
upload_url = s3_client.generate_presigned_url(
    "put_object",
    Params={
        "Bucket": RESUME_BUCKET,
        "Key": s3_key,
        "ContentType": "application/pdf",
    },
    ExpiresIn=300,  # 5 minutes
)
```

The presigned URL embeds:
- Bucket and key (where to upload)
- Expiration time
- AWS signature (proves backend authorized this upload)
- Content-Type restriction

### Download/Preview

Download and preview use the same endpoint with a query parameter:

```python
# Preview (inline in browser)
GET /resume/url

# Download (forces save dialog)
GET /resume/url?download=true
```

The `download=true` parameter adds `Content-Disposition: attachment` to the presigned URL, which tells the browser to download rather than display the file.

### Consequences

**Positive:**
- Bypasses Lambda memory and timeout constraints
- Bypasses API Gateway 10MB payload limit
- Faster uploads (single network hop)
- Scales to large files without infrastructure changes

**Negative:**
- Three endpoints instead of one
- Frontend must handle multi-step upload flow
- CORS configuration required on S3 bucket

**Mitigations:**
- Frontend upload logic is straightforward (3 fetch calls)
- S3 CORS is configured in CloudFormation template
- Error handling at each step with rollback (if S3 upload fails, don't call confirm)

### Related
- Phase 4D: Resume management
- [ADR-004](./DECISIONS.md#adr-004-deploy-backend-to-aws-lambda--api-gateway): Lambda deployment (timeout constraints)

---

## ADR-025: Chatbox Runtime — Lambda Function URL + Node.js (Streaming)

**Date:** 2026-06-05
**Status:** Accepted
**Phase:** 6 (Per-Job Chat Agent)

### Context

The chatbox needs to stream an LLM response (token-by-token) to the browser. An agent turn (LLM round-trips + tool calls) may take longer than a simple request — assume up to ~1 minute. We must decide where the chat backend runs and how it streams.

The existing app runs on **API Gateway (HTTP API) + Lambda + FastAPI/Mangum**. Investigation (curl + CloudWatch, see Evidence) proved this path **cannot stream in real time**: Mangum buffers the entire response and returns it at once, and API Gateway imposes a hard 30s integration cap. This is fine for buffered progress SSE but fatal for token-by-token chat.

A hard product constraint: keep the deployment **pure-serverless** — nothing to spin up or keep running before the app is usable (scale-to-zero, $0 idle).

### Decision

Run the chat backend on a **Lambda Function URL with Node.js and response streaming** (`RESPONSE_STREAM` invoke mode). Stream tokens to the browser SSE-style. Budget a turn at up to ~1 minute (well within the Function URL 15-min limit). The rest of the app stays on API Gateway + Lambda (a hybrid).

### Alternatives Considered

| Option | 30s cap | Streams? | Serverless / $0 idle | Notes |
|--------|---------|----------|----------------------|-------|
| API Gateway + FastAPI/Mangum | ❌ 30s | ❌ (Mangum buffers) | ✅ | Proven broken for streaming |
| **Lambda Function URL + Node.js** (chosen) | ✅ none | ✅ native (`streamifyResponse`) | ✅ | Node streaming is first-class |
| Lambda Function URL + Python/Mangum | ✅ none | ❌ (Mangum still buffers) | ✅ | Function URL removes API GW buffer but NOT Mangum |
| Long-running container (FastAPI) | ✅ none | ✅ native | ❌ always-on | **Industry norm**, rejected for always-on |
| Async worker + SSE reconnect + Redis Streams | worked-around | partial | ✅ | Over-engineered |

### Reasoning

- **Two buffers, not one.** Removing API Gateway (via Function URL) removes the API Gateway buffer, but **Mangum** (FastAPI's Lambda adapter) still buffers — it collects the full response before returning, because classic Lambda returns one complete response. So FastAPI/Python on a Function URL still does not stream.
- **Node escapes Mangum.** Lambda's response-streaming API (`awslambda.streamifyResponse`) is first-class in Node and writes chunks incrementally. Node is the runtime AWS built streaming for.
- **Explicit trade (the honest part):** a long-running **container is the industry-standard home for streaming chat** and would be simpler (one language, native `StreamingResponse`, in-process state). We **reject it deliberately** to preserve pure-serverless / nothing-to-spin-up, accepting the resulting seams: a second language (Node) and a second front door (Function URL alongside API Gateway). Stayed on AWS rather than pivoting to Vercel-edge/TS to keep a single cloud.

### Evidence

- A timestamped `curl -N` against the deployed ingestion SSE showed all events arriving in a single ~116ms burst at connection close (not spread over the ~25s the server produced them) — proving Mangum + API Gateway buffer and flush on generator end.
- CloudWatch logs confirmed the server-side generator polls/yields every 3s, but the client only receives the batch at close. (Separate overlapping-connection bug captured in `docs/backlog/`.)
- Source confirms it: comment in `ingestion_routes.py` — "API Gateway + Mangum buffers the entire StreamingResponse and returns it at once when the generator ends."

### Consequences

- (+) Real token streaming, serverless, no 30s cap, $0 idle.
- (−) Second language (Node) and second public entry point (Function URL) → own CORS + JWT verification in the Node handler.
- (−) Cross-language tool access (Node ↔ Python) — addressed in [ADR-030](#adr-030-single-standalone-python-mcp-server-multi-client).

### Related
- [ADR-004](./DECISIONS.md#adr-004-deploy-backend-to-aws-lambda--api-gateway): Lambda + API Gateway base
- [ADR-016](./DECISIONS.md#adr-016-use-sse-for-real-time-progress-updates): SSE for progress (buffered, different needs)
- [ADR-028](#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts): turn lifecycle on this runtime

---

## ADR-026: Chat Session Lifetime & Identity — Per-Tab Ephemeral

**Date:** 2026-06-05
**Status:** Accepted
**Phase:** 6 (Per-Job Chat Agent)

### Context

The chatbox lives in the lower-right of the Search page. We must decide how long a conversation persists and how it is identified.

### Decision

A chat conversation is **per-tab and ephemeral**. A frontend-generated **`sessionId`** identifies it, stored in `sessionStorage` (the **id only**, not the history). The chatbox can be minimized or closed; **closing → next open starts a new chat** (new `sessionId` + suffix). The `sessionId` is a cache/correlation key, **not** an auth boundary — the JWT still authenticates the user.

### Alternatives Considered

| Option | Survives refresh | Survives tab close | Cross-device | Verdict |
|--------|------------------|--------------------|--------------|---------|
| Per-message (no continuity) | n/a | n/a | n/a | ❌ no multi-turn |
| **Per-tab (sessionId, chosen)** | ✅ | ❌ (intended) | ❌ | ✅ matches ephemeral helper |
| Per-login (localStorage) | ✅ | ✅ | ❌ | ❌ stale context, cross-tab clobber, logout privacy |
| Backend DB persistence | ✅ | ✅ | ✅ | ❌ CRUD plumbing, no resume value |

### Reasoning

- This is a **contextual, in-the-moment assistant**, not a saved-thread product. Ephemeral matches the use case.
- A DB would add CRUD plumbing with little AI-engineering signal; explicitly out of scope.
- `crypto.randomUUID()` generates the `sessionId` on first load; `sessionStorage` is naturally per-tab and survives refresh, so the id (and thus conversation identity) is stable across reloads and dies with the tab.

### Consequences

- (+) Simple, no DB, ephemeral by construction.
- (−) No cross-device / cross-tab history (acceptable — single-user contextual helper).
- `sessionId` doubles as the Redis key and a log-correlation id ([ADR-027](#adr-027-chat-state-store--ephemeral-redis-upstash)).

### Related
- [ADR-027](#adr-027-chat-state-store--ephemeral-redis-upstash): where the session's state lives

---

## ADR-027: Chat State Store — Ephemeral Redis (Upstash)

**Date:** 2026-06-05
**Status:** Accepted
**Phase:** 6 (Per-Job Chat Agent)

### Context

Each chat turn is a separate, stateless request (one SSE request per question; the connection closes after each answer). On Lambda there is no reliable in-process memory across turns (instance churn). So conversation history and retrieved tool results must live somewhere that survives between turns. We must pick a **single source of truth** — having history in two places (e.g. sessionStorage AND a server store) makes the LLM input assembly ambiguous and is the classic two-source-of-truth anti-pattern.

### Decision

Use **Redis (Upstash — free tier, HTTP-accessible, no VPC) as the single, ephemeral source of truth** for a session, keyed by `sessionId` with a **TTL = session lifetime**. Redis holds **both** conversation history **and** the MCP/tool-result cache. The **frontend renders only** (it holds the `sessionId` and a transient in-flight copy for optimistic display). **The LLM input is assembled backend-side from Redis** — one clean assembly point.

### Alternatives Considered

| Option | Source of truth | New infra | Verdict |
|--------|-----------------|-----------|---------|
| **Redis (Upstash), ephemeral (chosen)** | Redis | Upstash (free, HTTP) | ✅ matches ephemeral data lifecycle |
| sessionStorage owns history | frontend | none | viable, but frontend re-sends full history; backend-as-truth is more production-shaped |
| History in BOTH sessionStorage + Redis | two ❌ | — | ❌ two sources of truth — ambiguous LLM input |
| In-process cache | per-instance | none | ❌ unreliable on Lambda (instance churn) |
| Backend DB (Postgres) | DB | migration | ❌ durable not needed; CRUD overhead |
| AWS ElastiCache | Redis | paid + VPC | ❌ cost + VPC friction from Lambda |

### Reasoning

- **Ephemeral data → TTL store.** The data is *meant* to expire. Redis-with-TTL is purpose-built for "hold this for a few hours then auto-delete" — the store's expiry **is** the session lifetime. This is matching the tool to the data's lifecycle, **not** "using a cache as a source of truth." (A persistent product would instead use Postgres as truth + Redis as cache.)
- **Industry note:** persistent chat records history in a **DB** (source of truth) with Redis as a cache/pub-sub. For a *short, ephemeral support chatbox*, skipping the DB and saving directly to Redis-with-TTL is a deliberate, appropriate workaround.
- **Single source of truth** keeps LLM-input assembly clean and avoids sync issues.
- **Upstash over ElastiCache:** free tier, HTTP/REST so a Lambda calls it **without VPC/NAT setup**; ElastiCache is paid and needs VPC wiring.

### Consequences

- (+) One ephemeral store for history + tool cache; clean backend-side context assembly; no DB, no VPC.
- (−) Redis can evict under memory pressure before TTL → a busy session could lose history early. **Acceptable** here: single-user + ephemeral by design.
- (−) Adds Upstash as a dependency (mitigated: free tier, no infra to manage).

### Related
- [ADR-026](#adr-026-chat-session-lifetime--identity--per-tab-ephemeral): sessionId keying
- [ADR-025](#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming): why Lambda → no in-process cache

---

## ADR-028: Chat Turn Lifecycle — Sequential Turns, Interruption Aborts

**Date:** 2026-06-05
**Status:** Accepted
**Phase:** 6 (Per-Job Chat Agent)

### Context

With one SSE request per turn and an agent loop that may run several seconds, we must define turn semantics: can turns overlap, and what happens when the user interrupts mid-response?

### Decision

- **Sequential turns:** input is locked while a response streams; no overlapping turns on one session.
- **Interruption** (close / refresh / navigate away / stop button) **aborts the in-flight Lambda Function URL invocation** — stops the agent loop and any in-progress LLM calls.
- **Partial-as-final:** whatever streamed before interruption is what's kept. **No resume** — the SSE connection and invocation are gone. Persist incrementally so the partial answer is recoverable on reload (optionally marked "interrupted").

### Reasoning

- Sequential turns prevent races on a single `sessionId`'s history/state.
- Refresh kills the SSE → kills the invocation → the turn cannot be continued anyway, so treating the partial as final is honest and correct.
- Resuming an interrupted stream would require durable, resumable turn-state (e.g. server-side checkpointing + Redis Streams replay) — overkill for an ephemeral support chatbox.

### Alternatives Considered

- **Concurrent turns:** rejected — races on session state, confusing UX.
- **Stream resume after interruption:** rejected — needs durable resumable turn-state; disproportionate to value.

### Consequences

- (+) Simple, race-free, matches "refresh kills SSE → partial OK."
- (−) An early-interrupted answer may be cut off mid-sentence (mitigated by an "interrupted" marker; user re-asks).

### Related
- [ADR-025](#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming): interruption = abort the Function URL invocation

---

## ADR-029: Build Agent Loop & MCP Client Directly (Reject LangChain & Vercel AI SDK)

**Date:** 2026-06-05
**Status:** Accepted
**Phase:** 6 (Per-Job Chat Agent)

### Context

The chat is an agent: LLM decides → calls tools → observes → repeats → final answer. Frameworks (LangChain, Vercel AI SDK) provide this loop, MCP client, and streaming out of the box. This is a **resume-driven** project whose goal is to demonstrate (and defend, cold, in interviews) understanding of agentic systems.

### Decision

**Hand-write** the agent loop (`stop_reason`-driven, bounded iterations), tool-call routing, MCP client, and streaming relay against the raw Anthropic API. **Reject both LangChain and the Vercel AI SDK** for this project.

### Reasoning

- **Defensibility is the goal.** The frameworks abstract away exactly the mechanics interviewers probe — the `stop_reason` loop, tool-schema passing, how tool results re-enter context, iteration bounding. "The framework handles that" sinks an interview the same way "Claude Code handles that" would.
- **Scale doesn't justify a framework.** ~200-line loop over ~4 tools. Writing it *is* the learning.
- **Vercel AI SDK specifically** (`createMCPClient` + `streamText` + `maxSteps`) would run the entire loop and MCP client internally — the same category of abstraction as LangChain. The same rejection reasoning applies to both.
- **Build-vs-buy is explicit:** for a ship-fast product (not demonstrating fundamentals), a framework would be a reasonable choice.

### Consequences

- (+) Full ownership of agent mechanics; strong, defensible interview signal; surveyed-the-landscape maturity (rejecting *two* popular frameworks deliberately).
- (−) Reimplements the ~200-line engine the SDK gives free (intentional — it's the educational point). Must keep it focused and articulate *why* it exists, knowing what the SDK provides (provider abstraction, integrations, hooks, hardening) that we deliberately skip.
- The **MCP server makes tools portable** — consumable by our own loop *and* off-the-shelf clients (Vercel AI SDK, Claude Desktop). This is the multi-client justification, and it is demonstrable.

### Related
- [ADR-030](#adr-030-single-standalone-python-mcp-server-multi-client): the MCP server the loop talks to

---

## ADR-030: Single Standalone Python MCP Server (Multi-Client)

**Date:** 2026-06-05 (updated 2026-06-06)
**Status:** Accepted (revised)
**Phase:** 6 → 7 (Per-Job Chat Agent / AI backend)

### Context

The chat backend is a **Node.js** Lambda ([ADR-025](#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming)), but the tools, DB access, and search logic are **Python** (existing service layer). We must define where the MCP server lives and how consumers reach it.

The original framing (6) considered only the chat agent as a consumer. Phase 7/8 adds **more consumers** (the admin extractor agent; possibly Claude Desktop / IDEs). That changes the right shape: tools should be built **once**, in **one place**, with any client connecting — the whole point of MCP being a protocol.

### Decision (revised)

Build **ONE standalone Python MCP server**, separate from any consumer, that exposes the tools (`search_jobs`, `search_jobs_semantic`, `get_job`, `get_resume`, `score_against_jd`, and later admin tools) as thin wrappers over the **existing Python logic** (in-process — no HTTP hop to reach the logic). Every consumer connects as an **MCP client**:

```
Python logic (search, score, pgvector, …)
      │ in-process
Python MCP server (ONE, standalone) — wraps logic as tools
      │ MCP protocol
 ┌────┴───────────────┬──────────────────┐
Node chat agent   Python admin agent   Claude Desktop / IDE
(MCP client, JS)  (MCP client, Py)     (MCP client)
```

- **Server language = Python** (where the logic lives → wraps it directly, no cross-language hop).
- **Clients can be any language** — the Node chat agent is the genuine cross-language MCP client (JS client ↔ Python server); the admin agent is a Python client; Claude Desktop is an off-the-shelf client.
- **Flat fan-out, no cascading** — tools call Python logic in-process; MCP servers do not call other MCP servers.

### Reasoning

- **Build once, consume many** — the defining value of MCP as a protocol. One tool surface; add a consumer (admin agent) → it connects to the *existing* server, no second MCP server, no duplicated logic.
- **Server in Python** wraps the logic with no network hop (vs. the earlier idea of a JS MCP server calling Python REST, which added a hop and split the logic).
- **MCP genuinely load-bearing** — multiple real clients (chat agent, admin agent, Claude Desktop) share one surface. Demonstrable (point Claude Desktop at it). Resolves the "ceremony for one client" critique.
- **Reuse, don't duplicate** — tools wrap the same Python functions the REST API uses (one source of truth).

### Alternatives Considered

- **MCP server in Node (per the chat consumer), calling Python REST** — *rejected*: consumer-coupled, adds an HTTP hop, and forces a 2nd MCP server when the admin agent needs tools.
- **One MCP server per consumer** — *rejected*: duplicates logic, defeats the protocol's purpose.
- **No MCP, Node calls Python REST directly** — *rejected*: thins the MCP story, forgoes portability/multi-client.

### Sub-Decisions (resolved in 7B)

- **Transport:** ✅ **HTTP (streamable-http)** for the deployed chat path (Node client + Python server = network boundary; persistent shared server, not subprocess-per-request). Also supports stdio (`MCP_TRANSPORT` env) for local/same-machine clients. (A same-process Python admin agent in Phase 8 can skip the protocol and call the tool functions directly — transport follows the consumer.)
- **Hosting:** ✅ **A new `McpServer` Lambda + Function URL inside `jh-backend-stack`** (NOT its own stack). The MCP server is Python and imports backend code (db/utils/models), so it reuses the backend build/deps/env; `jpushapi` deploys it. (Own-stack would duplicate the Python build for the same codebase; chat got its own stack only because it's Node.)
- **Auth:** ✅ service-to-service shared token — see [ADR-033](#adr-033-mcp-server-auth--service-to-service-token-not-cors).

### Consequences

- (+) One tool surface, many clients; one source of truth; strong, demonstrable MCP justification; no cross-language hop to the logic.
- (−) A new standalone Python MCP server to build + host (the Python MCP SDK).
- (−) Cross-language client (Node→Python over MCP) is slightly more than a REST call — but that's the point of MCP.

### Related
- [ADR-029](#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk): the hand-written MCP client (chat agent)
- [ADR-025](#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming): Node chat runtime (one MCP client)
- [ADR-032](#adr-032-embeddings--voyage-pre-trained-no-fine-tuning): embeddings used by the search tools

---

## ADR-031: Conversation Storage in Redis — Per-Message Entries in a Single JSON Blob

**Date:** 2026-06-05
**Status:** Accepted
**Phase:** 6B (Chat Redis + Session State)

### Context

The chat session needs to store conversation state in Redis ([ADR-027](#adr-027-chat-state-store--ephemeral-redis-upstash)): the messages exchanged, a (future) rolling summary, and a counter. Since the LLM is stateless, every turn reads this state to rebuild context and writes the new exchange back. Two modeling decisions:

1. **Indexing unit** — store per-**message** (alternating user/assistant, role-tagged) or per-**exchange** (user+assistant pairs)?
2. **Storage shape** — one JSON blob per session, or separate Redis keys / native structures (LIST / sorted set)?

### Decision

Store conversation state as **per-message entries inside a single JSON blob**, keyed `chat:{uid}:{sessionId}`:

```
chat:{uid}:{sessionId} → {
  "message_count": 0,        // monotonic counter (≈ industry's sequence_number)
  "summary": "",             // rolling summary of compressed-out messages (Phase 7 fills; 6B stub)
  "messages": [              // recent messages, role-tagged, in order (LLM API-native shape)
    { "role": "user",      "content": "...", "ts": 0, "interrupted": false },
    { "role": "assistant", "content": "...", "ts": 0, "interrupted": false }
  ],
  "created_at": 0,
  "updated_at": 0
}
TTL: 3600s (1h), sliding — re-set on each write (SET ... EX)
```
- `uid` comes from the verified JWT (not client-supplied) — namespaces by authenticated user.
- 2 commands/turn: `GET` (read context) + `SET ... EX` (write + refresh TTL).

### Alternatives Considered

**Indexing: per-message (chosen) vs per-exchange pairs**

| | Per-message (chosen) | Per-exchange pairs |
|---|---|---|
| Matches LLM API (`messages:[{role}]`) | ✅ direct, no transform | ✗ must flatten pairs per call |
| Asymmetric turns (user→tool→assistant) | ✅ any sequence | ✗ breaks pairing |
| Partials (user w/ no reply, interrupted assistant) | ✅ natural | ✗ awkward empty-assistant pairs |
| Industry norm (messages table + sequence_number) | ✅ | uncommon as storage |

**Storage shape: single JSON blob (chosen) vs Redis LIST / sorted set**

| Factor | Favors blob (chosen) | Favors LIST/sorted-set |
|---|---|---|
| Size | small + bounded (~30 KB, see below) | large / unbounded |
| Read pattern | read the WHOLE working set each turn | read slices/ranges |
| Write pattern | rewrite multiple fields together (messages+summary+count+TTL) | append one item |
| Concurrency | single writer (sequential turns) | many writers / high append rate |
| TTL | one key, one atomic sliding TTL (`SET ... EX`) | per-key EXPIRE coordination (footgun) |
| Commands/turn | 2 | 4–6 |

### Reasoning

- **Size estimate confirms "small":** the full 200K-token context ≈ 800 KB of text, but we never store that — we cap recent messages + a bounded summary. Realistic stored size ≈ **~30 KB** (recent ~10 exchanges + summary + metadata). At that size, rewriting the whole blob per turn is trivial; the LIST's "don't rewrite the whole dataset" advantage doesn't apply.
- **Access pattern is document-shaped, not log-shaped:** we read the whole working set every turn to build the prompt, and write several fields together. That's an atomic `GET`/`SET ... EX` on one key — simpler, cheaper, single sliding TTL. A LIST/sorted-set wins only for large, unbounded, append-heavy, range-queried, or concurrent data — none of which apply here.
- **Per-message is API-native and partial-friendly:** stored exactly as the LLM API consumes it; an interrupted turn saves a partial assistant message flagged `interrupted: true` (the ChatGPT-style behavior — partials are real conversation context).
- **Policy vs storage separation:** the *storage* is per-message in a blob; *policies* (keep recent N, compress oldest when tokens exceed a target — Phase 7) reason over it. Storage shape supports either policy.

### Consequences

- (+) One `GET`/`SET ... EX` per turn; atomic multi-field update; one clean sliding TTL; API-native message shape; partial-saving works.
- (−) Bounded by design — messages beyond the recent window are summarized away (Phase 7), not retained verbatim (production DBs keep all and window on retrieval; we cap because ephemeral). Acceptable for a short-lived assistant.
- (−) Would need re-modeling to a native structure if the data became large/unbounded/concurrent — not the case here.

### Related
- [ADR-027](#adr-027-chat-state-store--ephemeral-redis-upstash): ephemeral Redis as the source of truth
- [ADR-026](#adr-026-chat-session-lifetime--identity--per-tab-ephemeral): sessionId; uid from the verified JWT
- [ADR-028](#adr-028-chat-turn-lifecycle--sequential-turns-interruption-aborts): partial-as-final (informs `interrupted` flag)

---

## ADR-032: Embeddings — Voyage (Pre-Trained, No Fine-Tuning)

**Date:** 2026-06-06
**Status:** Accepted
**Phase:** 7A (Vector / RAG infrastructure)

### Context

Phase 7 adds semantic job↔resume matching: embed job descriptions (at extraction)
and resumes (at upload) into vectors, store in pgvector, retrieve top-K by cosine
for the "best match across all my jobs" query (RAG). We must choose:
1. **Which embedding provider** (cloud vs open-source; which vendor).
2. **Pre-trained vs fine-tuned.**

Key constraint: embeddings are computed in the **`ExtractorWorker` Lambda**
(256 MB, 30s) and at resume upload — so the *runtime environment* matters.

### Decision

- **Provider: Voyage AI** (Anthropic-recommended third-party embeddings; cloud, HTTP).
- **Pre-trained, general model — NO fine-tuning.**

### Reasoning

**Why a cloud API (not open-source local) — the runtime decides it:**
Embedding runs inside a **256 MB / 30s Lambda**. Bundling a local model
(sentence-transformers/BGE: 80 MB–1.3 GB) into that Lambda is hostile —
size/memory limits, cold-start model load, CPU-only. A **cloud embedding = a
simple HTTP call**, which fits Lambda cleanly. (Same "don't bundle heavy things
in Lambda" theme as ADR-024/025.) Open-source would be viable only if embedding
moved to a container — not worth it here.

**Why Voyage specifically:**
- **Free tier** — our usage is tiny (≈300 jobs embedded once at ingest ≈ a few
  hundred K tokens), so realistically **~$0**.
- Anthropic-recommended (we use Claude), strong quality, simple HTTP from Lambda.
- (OpenAI / Bedrock are comparable in quality + pennies in cost, but OpenAI needs
  a payment method and we have **no existing OpenAI API key** — the repo's
  "openai" is a *scraping extractor for the company OpenAI*, not API access.
  Bedrock has no free tier. Voyage's free tier is the cleanest $0 path.)

**Why pre-trained, not fine-tuned:**
- Job/resume text is **general English** — general embeddings already capture
  "distributed systems ≈ large-scale infrastructure." No specialized domain.
- Fine-tuning needs **labeled (resume, job, good/bad-match) pairs** + a **measured
  retrieval gap** — we have neither (no user-feedback labels). The senior move is
  to **evaluate** the general model's retrieval on a small hand-picked test set,
  not to train one.
- Quality of top open-source/cloud embeddings is comparable on general English
  (MTEB) — model choice is not the bottleneck.

### Embeddings ≠ chat model
Anthropic has **no first-party embedding model** — embeddings always come from a
separate provider regardless of the chat vendor. The embedding vendor (Voyage) is
independent of the chat vendor (Anthropic/Claude); matching them gives no quality
benefit, just convenience.

### Consequences

- (+) Simple HTTP from the ExtractorWorker Lambda; free-tier → ~$0; strong quality.
- (+) Pre-trained → no training pipeline, no labeled data needed.
- (−) A new vendor account/key (Voyage) → goes in `.env.local` + generators → Lambda env.
- **Roadmap:** fine-tune embeddings only if we later collect match-feedback labels
  AND a retrieval eval shows a real gap. Document, don't build.

### Related
- [ADR-031](#adr-031-conversation-storage-in-redis--per-message-entries-in-a-single-json-blob): per-message storage (vectors are separate, on the jobs table)
- [ADR-014](./DECISIONS.md#adr-014-use-hybrid-text-search-postgresql-full-text--fuzzy): existing keyword search (vectors add semantic retrieval)
- [ADR-030](#adr-030-single-standalone-python-mcp-server-multi-client): the MCP search tools that use these embeddings

---

## ADR-033: MCP Server Auth — Service-to-Service Token (Not CORS)

**Date:** 2026-06-06
**Status:** Accepted
**Phase:** 7B (MCP server hosting)

### Context

The MCP server (ADR-030) is hosted as a Lambda + Function URL inside
`jh-backend-stack` (ADR-030 sub-decision). The Function URL is **`AuthType: NONE`**
(no IAM/API-Gateway auth — same as the chat Lambda, ADR-025), so an in-handler
check is the *only* gate. This matters: the tools take `user_id` as an argument
and return that user's private data — `get_resume(user_id=…)` would leak any
user's resume if the endpoint were open. We must choose **what kind of auth**
sits in front of the MCP server.

The key question is *who the caller is*. The MCP server is never called by a
browser. Its clients are **backend services**: the Node chat agent (ADR-025/029)
and, later, the admin agent (Phase 8). The end user never talks to the MCP server
directly — they talk to the agent, which already verifies the user's JWT and then
calls the MCP server on their behalf.

### Decision

- **Service-to-service shared token.** The caller sends
  `Authorization: Bearer <MCP_SERVICE_TOKEN>`; the handler rejects anything else.
- **Fail closed.** If `MCP_SERVICE_TOKEN` is unset, the server returns 500 and
  refuses to serve — never runs unauthenticated.
- **`user_id` is a trusted tool argument**, not re-authenticated at the MCP layer.
  The agent (which holds and verifies the user's JWT) passes the authenticated
  `user_id`; the server trusts its caller, mirroring how the REST layer derives
  uid from the JWT.
- Enforced as Starlette `ServiceAuthMiddleware` wrapping the FastMCP ASGI app
  (`mcp_server/handler.py`).

### Reasoning

**Why service-to-service, not user-JWT, at the MCP layer:**
The MCP server's *client* is the agent, a trusted backend service — not the
browser and not the end user. Re-verifying the user's JWT here would be the wrong
boundary: the agent is the thing being authenticated, and it may act for different
users across calls (and the Phase-8 admin agent acts with no end user at all).
A single shared service token correctly models "only our backend may call this."
The per-user authorization already happened upstream (the agent verified the JWT);
the MCP server's job is to trust *that the caller is our agent*.

**Why NOT CORS:**
CORS is a **browser-only** mechanism — it restricts which *web origins* a browser
will let make a request; it does nothing against a non-browser caller (curl, a
Lambda, an attacker's script). This endpoint is called **server-to-server**, so
CORS would add zero security while implying protection. The real gate is the
shared token. (Contrast the chat Lambda, ADR-025, which *is* browser-facing and
*does* need CORS — different boundary, different control.)

**Why a shared static token (not signed/rotated/IAM):**
- The trust set is tiny and internal (our own agents), so a shared secret in
  Lambda env is proportionate — same trust model as the JWT `SECRET_KEY`.
- IAM/SigV4 on the Function URL would couple the Node agent to AWS SDK signing
  for marginal benefit over a token both sides already hold via env.
- Lives in `.env.local` + the SAM generators → Lambda env (never git-tracked),
  consistent with every other secret in the repo.

### Consequences

- (+) Correct boundary: authenticates the *service*, leaves per-user authz to the
  agent that holds the JWT. One env var, fail-closed, no AWS-signing coupling.
- (+) Same secret-handling pattern as the rest of the stack (`.env.local` →
  generators → Lambda env).
- (−) A static shared token must be rotated manually if leaked (acceptable for an
  internal-only surface; revisit if external clients are ever allowed).
- (−) The MCP server trusts the agent's `user_id` blindly — safe only because the
  token proves the caller is our agent. If the token leaked, a caller could read
  any user's data; the token is therefore the whole security boundary.

### Related
- [ADR-030](#adr-030-single-standalone-python-mcp-server-multi-client): the MCP server this auth protects
- [ADR-025](#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming): the chat Lambda — browser-facing, so it DOES use CORS (the contrast)
- [ADR-029](#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk): the agent (MCP client) that holds the JWT and passes `user_id`
- Learning: [vectors-rag-eval.md](../learning/vectors-rag-eval.md)

---

## ADR-034: Sandbox Execution — Local Docker (Dev), Lambda the Production Path

**Date:** 2026-06-08
**Status:** Accepted
**Phase:** 8 (autonomous extractor-discovery agent)

### Context

The Phase 8 agent runs **untrusted, LLM-generated trial code** that fetches arbitrary
external sites (to discover how to list a company's jobs). Untrusted code must be
**sandboxed** — never `exec()`'d in-process with our secrets / IAM / filesystem (it could
`rm -rf`, read `.env`, exfiltrate, or pivot to internal services). The question is **where**
the sandbox runs.

Two viable implementations, with the *same* isolation goal (no secrets, controlled
network, resource limits, ephemeral, unprivileged):
1. **Local Docker** — an ephemeral container per trial (`docker run --rm`).
2. **AWS Lambda** — invoke a zero-permission runner Lambda per trial (Firecracker microVM).

### Decision

- **Build + run with LOCAL DOCKER.** The agent's `run_trial(code)` ([host_harness.py](../../backend/extractor_agent/sandbox/host_harness.py)) ships trial code into a hardened, ephemeral container and returns the result.
- **Lambda is the documented PRODUCTION path, not built.** A production deployment would run trials in a zero-permission, network-restricted Lambda (`CodeUri: extractors_v2`, `Policies: []`, no secrets) — Firecracker microVM isolation, auto-scale.

### Reasoning

**Why local Docker for the build (it's a DEV-time choice, not a safety one):**
- **$0, no deploy, fast iteration** — edit → run instantly, no `sam build`/invoke round-trip, no AWS dependency. For a *local, on-demand admin tool* (the agent is run by hand, not user-facing), this is the pragmatic dev experience.
- **Owned + inspectable** — we wrote the isolation flags (`--rm`, `--read-only`, `--network`, `--cap-drop ALL`, no secrets), so the sandboxing is demonstrable and explainable, not outsourced.
- Docker is NOT safer or more capable than Lambda here — it's just **more convenient to build and iterate on.**

**Why Lambda is the right PRODUCTION path (consistent with the rest of the stack):**
- The whole app is already serverless Lambda (backend/MCP/chat). A production code-runner should be Lambda too — same architecture, no new infra type.
- **Firecracker microVM** isolation (what Lambda runs on) is *stronger* than a shared-kernel container, and Lambda auto-scales with $0 idle. EC2+Docker would mean managing servers (avoided everywhere else) for *worse* isolation — rejected.

**The swappable seam (the key design point):**
The ONLY thing that changes between dev and prod is **how `run_trial` executes the code** —
`docker run` (local) vs. `lambda.invoke` (prod). Both take a code string, run it isolated,
return JSON. So `run_trial` is a clean boundary: a future `RUN_TRIAL_MODE=lambda` could swap
the backend without touching the agent loop. This is what makes "Docker now, Lambda later" a
config change, not a redesign — *the sandboxing skill is portable; only the delivery differs.*

**Why this is fine for THIS project:**
The agent is a **local admin/build-time tool** (run on-demand to onboard a company; its
*output* — a discovered extractor — is what's published, not the agent). So a local-only
sandbox is proportionate; no production sandbox needs deploying. ([ADR-033](#adr-033-mcp-server-auth--service-to-service-token-not-cors)'s "boundary
follows the consumer" theme: the sandbox boundary is local because the consumer is local.)

### Self-contained `extractors_v2` enables both
Both deliveries require the trial's contract (`BaseExtractorV2`) be in the sandbox WITHOUT
the rest of the backend (no `db`/`config.settings`/secrets). That's why `extractors_v2/` is
**import-clean** — Docker bakes just that folder into the image; a Lambda would set
`CodeUri: extractors_v2`. A non-self-contained framework would leak the whole backend into
the sandbox.

### Consequences
- (+) Free, fast, owned dev sandbox; the sandboxing concept is fully demonstrated locally.
- (+) Clear production story (Lambda) that fits the all-serverless architecture — a config-level swap at `run_trial`, not a rewrite.
- (−) The local Docker sandbox isn't deployed/scalable as-is — acceptable, since the agent is a local admin tool (production would swap to Lambda).
- (−) `exec()`-ing untrusted code is sufficient for our semi-trusted (LLM scraping) case + microVM/container isolation; a maximally-hostile, internet-scale runner (e.g. LeetCode) would add gVisor/syscall-filtering/no-egress. Scale hardening to the threat.

### Related
- [PHASE_8B_SUMMARY](../logs/PHASE_8B_SUMMARY.md): the Docker sandbox harness this describes
- [ADR-024/025](#adr-025-chatbox-runtime--lambda-function-url--nodejs-streaming): "don't bundle heavy things in Lambda" / runtime-follows-consumer — same reasoning family
- [ADR-029](#adr-029-build-agent-loop--mcp-client-directly-reject-langchain--vercel-ai-sdk): own the mechanics (hand-built loop) — same "build it, understand it" ethos applied to the sandbox