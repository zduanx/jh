# API Design

## Base URL

- **Development:** `http://localhost:8000`
- **Production:** `https://abc123.execute-api.us-east-1.amazonaws.com/prod` (AWS Lambda + API Gateway)

---

## Authentication

All protected endpoints require JWT in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`
**Authentication:** Not required

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2024-12-13T10:30:00Z"
}
```

---

### 2. Google OAuth Login

**Endpoint:** `POST /auth/google`
**Authentication:** Not required
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
}
```

**Success Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Error Response:** `401 Unauthorized`
```json
{
  "detail": "Invalid authentication token"
}
```

---

### 3. Get Current User

**Endpoint:** `GET /api/user`
**Authentication:** Required (JWT)

**Headers:**
```
Authorization: Bearer <your_jwt_token>
```

**Success Response:** `200 OK`
```json
{
  "email": "user@gmail.com",
  "name": "John Doe",
  "picture": "https://lh3.googleusercontent.com/..."
}
```

**Error Responses:**

`401 Unauthorized` - Missing or invalid token
```json
{
  "detail": "Not authenticated"
}
```

`401 Unauthorized` - Expired token
```json
{
  "detail": "Token has expired"
}
```

---

### 4. List Available Companies

**Endpoint:** `GET /api/ingestion/companies`
**Authentication:** Not required

**Response:** `200 OK`
```json
[
  {"name": "google", "display_name": "Google", "logo_url": "https://..."},
  {"name": "amazon", "display_name": "Amazon", "logo_url": "https://..."},
  {"name": "anthropic", "display_name": "Anthropic", "logo_url": "https://..."}
]
```

---

### 5. Get User's Company Settings

**Endpoint:** `GET /api/ingestion/settings`
**Authentication:** Required (JWT)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "company_name": "anthropic",
    "title_filters": {"include": [], "exclude": ["intern"]},
    "is_enabled": true,
    "updated_at": "2024-12-18T10:30:00Z"
  }
]
```

**Note:** `title_filters.include` is always `[]` (never `null`). Empty array means "include all jobs".

---

### 6. Batch Update Company Settings

**Endpoint:** `POST /api/ingestion/settings`
**Authentication:** Required (JWT)
**Content-Type:** `application/json`

**Request Body:**
```json
[
  {"op": "upsert", "company_name": "google", "title_filters": {"include": ["engineer"], "exclude": []}, "is_enabled": true},
  {"op": "upsert", "company_name": "amazon", "title_filters": {"include": [], "exclude": []}, "is_enabled": false},
  {"op": "delete", "company_name": "netflix"}
]
```

**Success Response:** `200 OK`
```json
[
  {"op": "upsert", "success": true, "company_name": "google", "id": 1, "updated_at": "2024-12-18T..."},
  {"op": "upsert", "success": true, "company_name": "amazon", "id": 2, "updated_at": "2024-12-18T..."},
  {"op": "delete", "success": true, "company_name": "netflix"}
]
```

**Error Response:** `422 Unprocessable Entity` (invalid company name)
```json
{
  "detail": [{"loc": ["body", 0, "company_name"], "msg": "Company 'invalid' not found..."}]
}
```

---

### 7. Dry Run (Preview Extraction)

**Endpoint:** `POST /api/ingestion/dry-run`
**Authentication:** Required (JWT)

Extracts job URLs for all enabled companies without full crawl. Returns per-company results with included/excluded jobs.

**Request Body:** None (uses user's enabled settings from DB)

**Success Response:** `200 OK`
```json
{
  "google": {
    "status": "success",
    "total_count": 128,
    "filtered_count": 3,
    "urls_count": 125,
    "included_jobs": [
      {"id": "123", "title": "Software Engineer", "location": "NYC", "url": "https://..."}
    ],
    "excluded_jobs": [
      {"id": "456", "title": "Senior Staff Engineer", "location": "SF", "url": "https://..."}
    ],
    "error_message": null
  },
  "amazon": {
    "status": "error",
    "total_count": 0,
    "filtered_count": 0,
    "urls_count": 0,
    "included_jobs": [],
    "excluded_jobs": [],
    "error_message": "Request timed out - career site may be slow"
  }
}
```

**Error Response:** `400 Bad Request` (no enabled companies)
```json
{
  "detail": "No enabled companies configured. Add companies in Stage 1."
}
```

---

### 8. Source URLs (Legacy)

**Endpoint:** `POST /api/sourcing/source-urls`
**Authentication:** Required (JWT)
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "company": "anthropic"
}
```

**Response:** `200 OK`
```json
{
  "urls": ["https://...", "https://..."],
  "count": 42
}
```

---

### 9. List Companies (Legacy)

**Endpoint:** `GET /api/sourcing/companies`
**Authentication:** Not required

**Response:** `200 OK`
```json
["google", "amazon", "anthropic", "tiktok", "roblox", "netflix"]
```

---

### 10. Get Tracked Job IDs (Phase 4A)

**Endpoint:** `GET /api/tracked/ids`
**Authentication:** Required (JWT)

Returns all tracked job IDs for the current user (lightweight endpoint for Search page).

**Success Response:** `200 OK`
```json
{
  "tracked": {
    "123": { "tracking_id": 5, "stage": "interested" },
    "456": { "tracking_id": 8, "stage": "applied" }
  }
}
```

---

### 11. Add Job to Tracking (Phase 4A)

**Endpoint:** `POST /api/tracked`
**Authentication:** Required (JWT)
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "job_id": 123
}
```

**Success Response:** `200 OK`
```json
{
  "tracking_id": 5,
  "job_id": 123,
  "stage": "interested",
  "tracked_at": "2026-01-22T10:00:00Z"
}
```

**Error Responses:**

`404 Not Found` - Job doesn't exist
```json
{
  "detail": "Job not found"
}
```

`409 Conflict` - Already tracked
```json
{
  "detail": "Job already tracked"
}
```

---

### 12. Remove Job from Tracking (Phase 4A)

**Endpoint:** `DELETE /api/tracked/{tracking_id}`
**Authentication:** Required (JWT)

**Success Response:** `200 OK`
```json
{
  "success": true
}
```

**Error Responses:**

`404 Not Found` - Tracking record doesn't exist or doesn't belong to user
```json
{
  "detail": "Tracking record not found"
}
```

`400 Bad Request` - Cannot delete if stage is not "interested"
```json
{
  "detail": "Cannot remove job that has progressed past 'interested' stage"
}
```

---

### 13. List Tracked Jobs (Phase 4B)

**Endpoint:** `GET /api/tracked`
**Authentication:** Required (JWT)

Returns all tracked jobs with full job details for the Track page.

**Success Response:** `200 OK`
```json
{
  "tracked_jobs": [
    {
      "id": 1,
      "job_id": 123,
      "stage": "interested",
      "is_archived": false,
      "notes": null,
      "tracked_at": "2026-01-22T10:00:00Z",
      "job": {
        "id": 123,
        "title": "Senior Software Engineer",
        "company": "google",
        "company_logo_url": "https://www.google.com/s2/favicons?domain=google.com&sz=128",
        "location": "Seattle, WA",
        "description": "Build scalable distributed systems...",
        "url": "https://careers.google.com/jobs/..."
      }
    }
  ],
  "total": 1
}
```

---

### 14. Update Tracked Job (Phase 4B/4C)

**Endpoint:** `PATCH /api/tracked/{tracking_id}`
**Authentication:** Required (JWT)
**Content-Type:** `application/json`

Update one or more fields on a tracked job. All fields are optional - only include what you want to change.

**Request Body:**
```json
{
  "is_archived": true,        // Phase 4B: toggle archive status
  "stage": "applied",         // Phase 4C: update stage
  "notes": "Had a referral"   // Phase 4C: update notes
}
```

**Success Response:** `200 OK`
```json
{
  "id": 1,
  "job_id": 123,
  "stage": "applied",
  "is_archived": true,
  "notes": "Had a referral",
  "tracked_at": "2026-01-22T10:00:00Z",
  "updated_at": "2026-01-22T15:30:00Z"
}
```

**Error Responses:**

`404 Not Found` - Tracking record doesn't exist or doesn't belong to user
```json
{
  "detail": "Tracking record not found"
}
```

`422 Unprocessable Entity` - Invalid stage value
```json
{
  "detail": "Invalid stage. Must be one of: interested, applied, screening, interviewing, offer, accepted, rejected"
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (auth required or invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Validation Error (Pydantic validation failed)
- `500` - Internal Server Error

