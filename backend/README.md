# Job Hunt Tracker - Backend API

FastAPI backend for job application tracking system, designed for AWS Lambda deployment.

## Architecture

- **Framework**: FastAPI (async Python web framework)
- **Authentication**: Google OAuth 2.0 + JWT tokens
- **Deployment**: AWS Lambda + API Gateway (serverless)
- **Adapter**: Mangum (FastAPI → Lambda)

## Project Structure

```
backend/
├── main.py                 # FastAPI app + Lambda handler
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (not committed)
├── .env.example           # Environment template
├── auth/
│   ├── routes.py          # Authentication endpoints
│   ├── models.py          # Pydantic models for auth
│   ├── utils.py           # JWT & Google OAuth utilities
│   └── dependencies.py    # FastAPI dependencies (get_current_user)
├── api/
│   └── routes.py          # Protected API endpoints
└── config/
    └── settings.py        # Configuration management
```

## Setup (Local Development)

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `GOOGLE_CLIENT_ID`: From Google Cloud Console
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `ALLOWED_ORIGINS`: Your frontend URL(s)

### 3. Run Locally

```bash
uvicorn main:app --reload --port 8000
```

API will be available at: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## API Endpoints

### Public Endpoints

#### `GET /health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-13T10:30:00Z"
}
```

#### `POST /auth/google`
Exchange Google OAuth token for JWT

**Request:**
```json
{
  "token": "google_id_token_from_frontend"
}
```

**Response:**
```json
{
  "access_token": "our_jwt_token",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Protected Endpoints

#### `GET /api/user`
Get current user information

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "email": "user@gmail.com",
  "name": "John Doe",
  "picture": "https://lh3.googleusercontent.com/..."
}
```

## AWS Lambda Deployment

### Using AWS SAM (Recommended)

1. **Install AWS SAM CLI**
   ```bash
   brew install aws-sam-cli  # macOS
   ```

2. **Create `template.yaml`** (see deployment guide in docs)

3. **Deploy**
   ```bash
   sam build
   sam deploy --guided
   ```

### Manual Deployment

1. **Package dependencies**
   ```bash
   pip install -r requirements.txt -t package/
   cp -r *.py auth/ api/ config/ package/
   cd package && zip -r ../deployment.zip . && cd ..
   ```

2. **Create Lambda function** in AWS Console
   - Runtime: Python 3.11
   - Handler: `main.handler`
   - Upload `deployment.zip`

3. **Configure API Gateway**
   - Create HTTP API
   - Add Lambda integration
   - Configure CORS

4. **Set environment variables** in Lambda configuration

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | ✅ Yes | - |
| `SECRET_KEY` | JWT signing key | ✅ Yes | - |
| `ALGORITHM` | JWT algorithm | No | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | No | 1440 (24h) |
| `ALLOWED_ORIGINS` | CORS allowed origins | No | localhost |

## Security Notes

1. **JWT Storage**: Frontend stores JWT in localStorage (Phase 1)
   - Phase 2+: Move to httpOnly cookies
2. **Token Expiration**: 24 hours (POC), will reduce to 15 min + refresh tokens
3. **HTTPS**: Required in production (API Gateway provides this)
4. **CORS**: Only allow trusted frontend domains

## Testing

```bash
# Run FastAPI with auto-reload
uvicorn main:app --reload

# Test health endpoint
curl http://localhost:8000/health

# Test auth endpoint (need valid Google token)
curl -X POST http://localhost:8000/auth/google \
  -H "Content-Type: application/json" \
  -d '{"token": "your_google_token"}'

# Test protected endpoint
curl http://localhost:8000/api/user \
  -H "Authorization: Bearer your_jwt_token"
```

## Common Issues

### "Invalid authentication token"
- Check `GOOGLE_CLIENT_ID` matches frontend
- Ensure token is fresh (Google tokens expire)

### "Could not validate credentials"
- Check `SECRET_KEY` is set
- Verify JWT hasn't expired

### CORS errors
- Add frontend URL to `ALLOWED_ORIGINS` in `.env`

## Next Steps

- [ ] Add PostgreSQL database (Phase 2)
- [ ] Implement job CRUD endpoints
- [ ] Add refresh token mechanism
- [ ] Set up monitoring (CloudWatch)
- [ ] Add rate limiting
