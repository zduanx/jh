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
- Uses extractors from src/extractors/
- Saves HTML to S3, metadata to DB

**JobParserLambda (backend/parser/main.py):**
- Triggered by SQS Queue B
- Uses extractors from src/extractors/
- Reads HTML from S3, parses, updates DB

**Shared code strategy:**
- Package src/extractors/ in all Lambda deployment packages
- Consider Lambda Layers for shared dependencies later if needed

---

## Phase 2 Pending Decisions

The following architectural decisions are deferred for future discussion and will be resolved during Phase 2 implementation.

### PDR-001: Database Choice

**Question:** Which database should we use for storing job data, user settings, and application tracking?

**Options:**
1. **PostgreSQL on AWS RDS**
   - ✅ Full ACID compliance, complex queries, SQL familiarity
   - ❌ Cost (~$15-20/month minimum), need to manage

2. **Neon (Serverless Postgres)**
   - ✅ Serverless, generous free tier, auto-scaling
   - ❌ Newer service, less proven at scale

3. **DynamoDB**
   - ✅ Serverless, AWS integration, unlimited scale
   - ❌ NoSQL learning curve, query limitations

**Status:** To be decided
**Target:** Before JobCrawlerLambda implementation

---

### PDR-002: Settings Storage Strategy

**Question:** How should we store user crawling settings (companies, filters)?

**Options:**
1. **Dedicated settings table in main database**
   - ✅ Simple, normalized, easy queries
   - ❌ More DB calls

2. **JSON field in users table**
   - ✅ Single query for user + settings
   - ❌ Less normalized, harder to query all settings

3. **Separate DynamoDB table (if using DynamoDB)**
   - ✅ Fast key-value lookups
   - ❌ Eventual consistency considerations

**Status:** To be decided
**Depends on:** PDR-001 (database choice)

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
