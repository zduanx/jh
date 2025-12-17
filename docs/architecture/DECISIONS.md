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

## Phase 2 Pending Decisions

The following architectural decisions are deferred for future discussion and will be resolved during Phase 2 implementation.

### ~~PDR-001: Database Choice~~ ✅ Resolved

**Status:** Resolved in ADR-011, ADR-012
**Decision:** PostgreSQL hosted on Neon

---

### ~~PDR-002: Settings Storage Strategy~~ ✅ Resolved

**Status:** Resolved (see ADR-011, ADR-013)
**Decision:** Dedicated tables with SQLAlchemy ORM for user settings and job applications

---

### PDR-003: Crawling Rate Limits

**Question:** How should we implement rate limiting to avoid getting blocked by company career pages?

**Considerations:**
- Different companies may have different tolerance
- Need delay between requests to same company
- Batch size per Lambda invocation affects rate

**Options:**
1. **Fixed delay per company (e.g., 2 seconds)**
   - ✅ Simple to implement
   - ❌ May be too slow or too fast for some companies

2. **Configurable delay in extractor class**
   - ✅ Flexible per company
   - ❌ Need to test and tune for each company

3. **Use SQS delay/visibility timeout**
   - ✅ Native AWS feature
   - ❌ Less control

**Status:** To be decided
**Target:** Before JobCrawlerLambda load testing

---

### PDR-004: Error Handling Strategy

**Question:** How should we handle crawling/parsing failures?

**Considerations:**
- Network failures (timeout, connection error)
- HTTP errors (404, 403, 500)
- Parsing errors (unexpected HTML structure)
- Rate limiting (429 Too Many Requests)

**Options:**
1. **SQS Dead Letter Queue (DLQ)**
   - ✅ AWS-native, automatic retry
   - ✅ Failed messages go to DLQ for inspection
   - ❌ Fixed retry count

2. **Custom retry logic with exponential backoff**
   - ✅ Flexible retry strategy
   - ❌ More code to write

3. **Hybrid: SQS retry + custom handling**
   - ✅ Best of both worlds
   - ❌ More complex

**Status:** To be decided
**Target:** Before JobCrawlerLambda implementation

---

### PDR-005: S3 Cleanup Policy

**Question:** How long should we keep raw HTML files in S3?

**Options:**
1. **Keep forever**
   - ✅ Can re-parse anytime, debugging
   - ❌ S3 storage costs grow over time

2. **Delete after successful parsing**
   - ✅ Minimal storage cost
   - ❌ Cannot re-parse or debug later

3. **S3 Lifecycle Policy (30/60/90 days)**
   - ✅ Balance cost and utility
   - ❌ Need to choose retention period

**Status:** To be decided
**Recommendation:** Start with 30-day retention

---

### PDR-006: JobCrawlerLambda Batching Strategy

**Question:** Should JobCrawlerLambda process one URL or multiple URLs per invocation?

**Options:**
1. **1 URL per Lambda invocation**
   - ✅ Simple, auto-scales, easy to retry
   - ❌ More Lambda invocations (but within free tier)

2. **Batch 10-50 URLs per invocation**
   - ✅ Fewer cold starts, more efficient
   - ❌ Harder to handle partial failures
   - ❌ Risk of timeout (15-minute Lambda limit)

**Status:** To be decided
**Recommendation:** Start with 1 URL, optimize later if needed

---

### PDR-007: WebSocket Infrastructure

**Question:** How should we implement real-time crawl status updates?

**Options:**
1. **API Gateway WebSocket**
   - ✅ AWS-native, serverless
   - ❌ Complex to set up with Lambda

2. **Polling (GET /api/crawl-status)**
   - ✅ Simple, no infrastructure change
   - ❌ Higher latency, more API calls

3. **Server-Sent Events (SSE)**
   - ✅ Simpler than WebSocket, one-way push
   - ❌ Requires long-running connection

**Status:** Deferred to Phase 2B
**Recommendation:** Start with polling, add WebSocket later

---

**Review Process:** These decisions will be reviewed and resolved as we implement each component of Phase 2.
