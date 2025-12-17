# Phase 2B: Web Application Skeleton & Database Setup

**Status**: ✅ Completed
**Date**: December 17, 2025
**Goal**: Build foundational web application structure with database, authentication, user management, and polished UI

---

## Overview

Phase 2B established the core web application framework with PostgreSQL database, SQLAlchemy ORM, Alembic migrations, React Router navigation, and optimized user state management.

**Included in this phase**:
- PostgreSQL database setup (Neon) with Alembic migrations
- User table schema with OAuth integration
- Frontend architecture with React Context state management
- Polished UI components (sidebar, dashboard, navigation)
- Performance optimizations (DB queries, JWT tokens, frontend caching)
- pytest test infrastructure

**Explicitly excluded** (deferred to Phase 2C+):
- Company settings table
- Job-related tables
- Ingestion workflow UI

---

## Key Achievements

### 1. Database Infrastructure
- **PostgreSQL**: Neon serverless database with connection pooling
- **SQLAlchemy**: ORM for database models and queries
- **Alembic**: Schema migration management
- **Test database**: Separate branch for local testing (prevents production data modification)
- Reference: [ADR-011 (PostgreSQL)](../architecture/DECISIONS.md#adr-011-use-postgresql-sql-over-nosql), [ADR-012 (Neon)](../architecture/DECISIONS.md#adr-012-use-neon-for-postgresql-hosting), [ADR-013 (SQLAlchemy+Alembic)](../architecture/DECISIONS.md#adr-013-use-sqlalchemy--alembic-for-database-access), [Alembic Migrations Guide](../deployment/ALEMBIC_MIGRATIONS.md), [SQLAlchemy Guide](../learning/sqlalchemy.md)

### 2. User Management System
- **User table**: BIGSERIAL PK (64-bit auto-increment), unique email with index, OAuth profile data
- **Create on first login**: User record created during first authentication (not on settings change)
- **Last login tracking**: Updated on each authentication, included in JWT
- **Profile updates**: Automatic sync of name and picture from Google on each login
- **Database query optimization**: Reduced authentication queries from 2 → 1 (50% reduction)
- Reference: [ADR-009 (Create on First Login)](../architecture/DECISIONS.md#adr-009-create-user-record-on-first-login-not-on-first-settings-change), [ADR-010 (BIGSERIAL IDs)](../architecture/DECISIONS.md#adr-010-use-bigserial-for-user-ids)

### 3. Frontend Architecture
- **React Router**: Client-side routing with protected routes
- **React Context**: Global user state management (`UserContext`)
- **Component structure**: Layout wrapper, collapsible sidebar, page components
- **State caching**: User data loaded once per session, zero repeat API calls
- Reference: [Frontend Learning Guide](../learning/frontend.md)

### 4. Polished UI Components
- **Collapsible sidebar**: 240px → 72px with smooth transitions
- **Dashboard**: User profile banner with Google avatar, last login, placeholder stats
- **Logout modal**: Confirmation dialog before sign-out
- **Material icons**: react-icons/md for consistent iconography

### 5. Performance Optimizations
- **JWT optimization**: Include `last_login` in token → eliminates DB query on dashboard load (100% reduction)
- **Frontend caching**: React Context loads user data once → zero repeat API calls
- **Direct object updates**: Modify SQLAlchemy objects directly → no redundant queries

### 6. Testing Infrastructure
- **pytest setup**: Test database fixtures, async test support
- **User service tests**: CRUD operation validation
- **Test database**: Separate Neon branch for isolated testing
- Reference: [Testing Guide](../deployment/TESTING.md), [pytest Guide](../learning/pytest.md)

---

## Database Schema

**users table**:
- `user_id`: BIGSERIAL primary key (64-bit auto-increment), indexed
- `email`: VARCHAR(255), unique constraint, indexed (OAuth lookup)
- `name`: VARCHAR(255), synced from Google profile
- `picture_url`: TEXT, Google profile picture URL
- `created_at`: TIMESTAMP WITH TIMEZONE, server default now()
- `last_login`: TIMESTAMP WITH TIMEZONE, updated on each auth

**Design rationale**:
- `user_id` BIGSERIAL for sequential IDs (hidden in JWT, see [ADR-010](../architecture/DECISIONS.md#adr-010-use-bigserial-for-user-ids))
- `email` index for fast OAuth lookups
- `last_login` in JWT to avoid extra queries
- User created on first login (see [ADR-009](../architecture/DECISIONS.md#adr-009-create-user-record-on-first-login-not-on-first-settings-change))

Reference: [User Model](../../backend/models/user.py)

---

## API Endpoints

**POST `/auth/google`** (updated):
- Purpose: Exchange Google ID token for JWT, create/update user
- Request: `{ credential: string }`
- Response: `{ access_token: string, user: { email, name, picture, last_login } }`
- Database: Creates user if new, updates profile + last_login if existing
- Auth: None (public endpoint)

**GET `/api/user`** (updated):
- Purpose: Get authenticated user data from JWT (no DB query)
- Request: Headers with `Authorization: Bearer <jwt>`
- Response: `{ email, name, picture, last_login }` (from JWT payload)
- Database: Zero queries (all data in JWT)
- Auth: JWT required

Reference: [API_DESIGN.md](../architecture/API_DESIGN.md)

---

## Highlights

### React Context State Management
**Pattern**: Fetch user data once on app mount, cache in memory, all child components access via `useUser()` hook.

**Benefits**: Zero repeat API calls, centralized logout logic, no loading spinners on route changes, DRY principle for auth state.

### Database Query Optimization
**Before**: `get_or_create_user` made 2 queries (SELECT + UPDATE in separate functions)
**After**: Single SELECT, modify object directly, commit
**Result**: 50% reduction in authentication queries

### JWT Token Optimization
**Before**: Dashboard made API call → DB query to fetch `last_login`
**After**: `last_login` included in JWT at authentication time
**Result**: 100% reduction in dashboard DB queries (0 queries per page load)

### Sidebar Design
Collapsible sidebar with floating toggle button (hinge design), smooth fade transitions for text labels, icons remain stationary for consistent alignment.

---

## Testing & Validation

**Manual Testing**:
- ✅ Google OAuth login flow
- ✅ Email whitelist enforcement
- ✅ User creation on first login
- ✅ Profile updates on subsequent logins
- ✅ Sidebar collapse/expand animation
- ✅ Logout confirmation modal
- ✅ Dashboard displays user data
- ✅ Protected routes redirect to login
- ✅ Last login timestamp display

**Automated Testing**:
- ✅ pytest setup with test database fixtures
- ✅ User service CRUD tests
- ✅ Async test support (pytest-asyncio)
- Future: Frontend component tests

---

## Metrics

- **Files created**: 25+
- **Lines of code**: ~2,000 (backend + frontend)
- **DB query reduction**: 50% (2→1 per auth)
- **API response time**: <50ms (JWT-based, no DB queries)
- **Frontend bundle size**: ~250KB (gzipped)
- **Database tables**: 1 (users)

---

## Next Steps → Phase 2C

Phase 2C will implement the ingestion workflow UI:
- Horizontal stepper UI component (5 stages)
- User company settings table
- Stage 1: Company configuration interface
- CRUD endpoints for company settings
- Workflow state management

**Target**: Complete Stage 1 (company selection) with full frontend-backend integration

---

## File Structure

```
backend/
├── models/
│   └── user.py              # SQLAlchemy user model
├── db/
│   └── user_service.py      # User CRUD operations
├── alembic/
│   ├── alembic.ini          # Alembic configuration
│   ├── env.py               # Migration environment
│   └── versions/            # Migration files
├── tests/
│   ├── conftest.py          # pytest fixtures
│   └── test_user_service.py # User service tests
└── auth/
    └── routes.py            # Updated with user creation/update

frontend/src/
├── context/
│   └── UserContext.js       # Global user state
├── components/
│   ├── Layout.js            # Main layout wrapper
│   ├── Sidebar.js           # Collapsible sidebar
│   └── Logo.js              # Custom SVG logo
└── pages/
    ├── DashboardPage.js     # User dashboard
    ├── LoginPage.js         # OAuth login
    ├── IngestPage.js        # Placeholder
    ├── SearchPage.js        # Placeholder
    └── TrackPage.js         # Placeholder
```

**Key Files**:
- [user.py](../../backend/models/user.py) - SQLAlchemy user model
- [user_service.py](../../backend/db/user_service.py) - User CRUD operations
- [UserContext.js](../../frontend/src/context/UserContext.js) - State management
- [Sidebar.js](../../frontend/src/components/Sidebar.js) - Navigation component

---

## Key Learnings

### Alembic Migrations
Alembic manages schema changes with version control. `alembic revision --autogenerate` detects model changes, `alembic upgrade head` applies migrations.

**Reference**: [Alembic Migrations](../deployment/ALEMBIC_MIGRATIONS.md)

### SQLAlchemy Session Management
Modify SQLAlchemy objects directly, commit once. Avoid redundant queries by updating objects in-place before commit.

**Reference**: [SQLAlchemy Guide](../learning/sqlalchemy.md)

### React Context vs Props
Context provides global state without prop drilling. Ideal for user authentication, theme, language settings. Avoids component tree pollution.

### JWT for Stateless Auth
Include frequently accessed data (last_login, user_id) in JWT payload to avoid database lookups. Balance between token size and query reduction.

---

## References

**External Documentation**:
- [Alembic Documentation](https://alembic.sqlalchemy.org/) - Database migrations
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/) - Python SQL toolkit
- [React Context API](https://react.dev/reference/react/createContext) - State management
- [React Router](https://reactrouter.com/) - Client-side routing
- [pytest Documentation](https://docs.pytest.org/) - Testing framework

---

**Status**: Ready for Phase 2C
