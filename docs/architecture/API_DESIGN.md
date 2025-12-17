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

