# Learning Notes Index

Quick reference to find topics discussed during development.

---

## Authentication & Security

### OAuth & Authentication
- [What is OAuth?](./authentication.md#what-is-oauth)
- [How OAuth works](./authentication.md#how-oauth-works)
- [OAuth vs Password login](./authentication.md#oauth-vs-password-login)
- [Google OAuth implementation](./authentication.md#google-oauth-implementation)

### Tokens & Sessions
- [JWT explained](./authentication.md#jwt-explained)
- [JWT vs Sessions comparison](./authentication.md#jwt-vs-sessions)
- [Token storage options](./authentication.md#token-storage)
- [Token security concerns](./authentication.md#token-security)

### Security Best Practices
- [HTTPS and why it matters](./security.md#https-and-ssl)
- [Preventing token interception](./security.md#preventing-token-interception)
- [localStorage vs httpOnly cookies](./security.md#token-storage-security)
- [Common vulnerabilities](./security.md#common-vulnerabilities)

---

## Backend Development

### Framework Comparisons
- [FastAPI vs Django](./backend.md#fastapi-vs-django)
- [When to use each framework](./backend.md#framework-selection)
- [FastAPI advantages](./backend.md#fastapi-advantages)

### API Design
- [REST vs GraphQL](./backend.md#rest-vs-graphql)
- [API endpoint design](./backend.md#api-endpoint-design)
- [Request validation with Pydantic](./backend.md#pydantic-validation)

---

## Frontend Development

### React Basics
- [Why React](./frontend.md#why-react)
- [Component architecture](./frontend.md#component-architecture)
- [Protected routes](./frontend.md#protected-routes)

### Frontend-Backend Integration
- [How frontend serves users](./frontend.md#frontend-serving)
- [Bootstrap process explained](./frontend.md#bootstrap-process)
- [Making API calls](./frontend.md#api-calls)
- [Including tokens in requests](./frontend.md#token-in-requests)

---

## AWS & Deployment

### AWS Services
- [EC2 vs Lambda comparison](./aws-deployment.md#ec2-vs-lambda)
- [When to use API Gateway](./aws-deployment.md#api-gateway)
- [AWS free tier options](./aws-deployment.md#free-tier)

### Deployment Strategies
- [Deploying FastAPI to EC2](./aws-deployment.md#fastapi-on-ec2)
- [Deploying React to Vercel](./aws-deployment.md#react-on-vercel)
- [Setting up HTTPS](./aws-deployment.md#https-setup)

---

## Third-Party Services

### Authentication Services
- [What is Auth0](./authentication.md#auth0)
- [AWS Cognito](./authentication.md#aws-cognito)
- [Comparing auth solutions](./authentication.md#auth-solutions-comparison)

### Other Tools
- [Bootstrap.js library](./frontend.md#bootstrap-library)
- [Passport.js (Node.js)](./backend.md#passportjs)

---

## System Design Concepts

### Scalability
- [Stateless vs Stateful architecture](./backend.md#stateless-vs-stateful)
- [Horizontal vs Vertical scaling](./aws-deployment.md#scaling)
- [Message queues](./backend.md#message-queues)

### Architecture Patterns
- [Microservices](./backend.md#microservices)
- [Single vs Multiple backend servers](./backend.md#single-vs-multiple-servers)
- [WebSocket for real-time updates](./backend.md#websocket)

---

## Quick Lookups

### Common Questions
- "What is OAuth?" → [authentication.md#what-is-oauth](./authentication.md#what-is-oauth)
- "EC2 or Lambda?" → [aws-deployment.md#ec2-vs-lambda](./aws-deployment.md#ec2-vs-lambda)
- "JWT or Sessions?" → [authentication.md#jwt-vs-sessions](./authentication.md#jwt-vs-sessions)
- "FastAPI or Django?" → [backend.md#fastapi-vs-django](./backend.md#fastapi-vs-django)
- "Is JWT secure?" → [security.md#jwt-security](./security.md#jwt-security)
- "How does frontend load?" → [frontend.md#bootstrap-process](./frontend.md#bootstrap-process)

### Technology Comparisons
All major "A vs B" comparisons are documented with:
- Side-by-side feature tables
- Use case recommendations
- Pros/cons analysis
- Code examples where applicable

---

## How to Use This Index

1. **Browse by topic**: Use the sections above
2. **Search**: Use Cmd+F to find keywords
3. **Follow links**: Click to jump to detailed explanations
4. **Cross-reference**: Related topics are linked within each file

---

## Files in this Directory

- **authentication.md** - OAuth, JWT, sessions, Auth0, security tokens
- **aws-deployment.md** - EC2, Lambda, API Gateway, deployment strategies
- **backend.md** - FastAPI, Django, REST, GraphQL, system architecture
- **frontend.md** - React, routing, state, frontend-backend communication
- **security.md** - HTTPS, token security, best practices, vulnerabilities
