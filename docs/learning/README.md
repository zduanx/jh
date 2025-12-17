# Learning Documentation

Educational content about technologies and concepts used in this project.

---

## Core Technologies

### Authentication & Security
**[authentication.md](./authentication.md)** - OAuth, JWT, sessions, Auth0
- What is OAuth and how it works
- JWT vs Sessions comparison
- Google OAuth implementation
- Token storage and security

**[security.md](./security.md)** - HTTPS, CORS, vulnerabilities
- Why HTTPS matters
- Token interception prevention
- localStorage vs httpOnly cookies
- Common security vulnerabilities

### Backend
**[backend.md](./backend.md)** - FastAPI, Django, REST, GraphQL
- FastAPI vs Django comparison
- API design patterns
- Pydantic validation
- System architecture concepts

**[python-fastapi.md](./python-fastapi.md)** - Generators, yield, Depends()
- How Python generators work
- yield vs return
- FastAPI dependency injection
- Type annotations for generators

**[sqlalchemy.md](./sqlalchemy.md)** - ORM, sessions, queries
- SessionLocal factory pattern
- Query patterns (object vs tuple)
- Session lifecycle
- Loading strategies

### Frontend
**[frontend.md](./frontend.md)** - React, routing, state management
- Why React
- Component architecture
- Protected routes
- Frontend-backend integration

### Cloud & Deployment
**[aws.md](./aws.md)** - EC2, Lambda, API Gateway, SAM
- EC2 vs Lambda comparison
- API Gateway patterns
- AWS SAM deployment
- Environment variables in Lambda

### Testing
**[pytest.md](./pytest.md)** - pytest commands and patterns
- Running tests (all, specific, filtered)
- Useful flags (-v, -s, -x, -k)
- Test structure and discovery
- Debugging failed tests

---

## Phase 2A: Job Scraping Architecture

**[kafka.md](./kafka.md)** - Message queue architecture
- Kafka vs RabbitMQ vs SQS
- Producer-consumer patterns
- When to use message queues

**[lambda-sqs.md](./lambda-sqs.md)** - Lambda + SQS integration
- SQS queue setup
- Lambda triggers and concurrency
- Error handling and retries

---

## Quick Reference

### Common Questions
- **"What is OAuth?"** → [authentication.md](./authentication.md)
- **"EC2 or Lambda?"** → [aws.md](./aws.md)
- **"JWT or Sessions?"** → [authentication.md](./authentication.md)
- **"FastAPI or Django?"** → [backend.md](./backend.md)
- **"How do generators work?"** → [python-fastapi.md](./python-fastapi.md)
- **"How to run tests?"** → [pytest.md](./pytest.md)

### Technology Comparisons
Most files include side-by-side comparisons with:
- Feature tables
- Use case recommendations
- Pros/cons analysis
- Code examples

---

## Files Overview

| File | Topics | Lines |
|------|--------|-------|
| [authentication.md](./authentication.md) | OAuth, JWT, sessions, Auth0, security tokens | ~838 |
| [aws.md](./aws.md) | EC2, Lambda, API Gateway, deployment | ~1081 |
| [backend.md](./backend.md) | FastAPI, Django, REST, GraphQL, architecture | ~664 |
| [frontend.md](./frontend.md) | React, routing, state, API integration | ~523 |
| [security.md](./security.md) | HTTPS, token security, vulnerabilities | ~361 |
| [python-fastapi.md](./python-fastapi.md) | Generators, yield, Depends() | ~725 |
| [sqlalchemy.md](./sqlalchemy.md) | ORM, sessions, queries | ~684 |
| [pytest.md](./pytest.md) | pytest commands and patterns | ~262 |
| [kafka.md](./kafka.md) | Message queues, Kafka architecture | ~834 |
| [lambda-sqs.md](./lambda-sqs.md) | Lambda + SQS integration | ~392 |

---

## How to Use

1. **Browse by topic** - Use sections above to find relevant file
2. **Search** - Use Cmd+F to find keywords
3. **Follow links** - Click to jump to detailed explanations
4. **Cross-reference** - Related topics are linked within files
