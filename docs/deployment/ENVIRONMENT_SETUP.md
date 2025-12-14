# Environment Variables & Secret Management

This guide explains how to manage secrets securely across development and production environments.

---

## 🔒 Security Principles

### ✅ DO
- Store secrets in `.env` files (gitignored)
- Use environment variables in deployment platforms
- Share secrets via secure channels (password managers, encrypted messaging)
- Rotate secrets regularly

### ❌ DON'T
- **NEVER** commit `.env` files to git
- **NEVER** hardcode secrets in source code
- **NEVER** share secrets in plaintext (email, Slack, tickets)
- **NEVER** reuse secrets across environments

---

## 📁 File Structure

```
project/
├── backend/
│   ├── .env              # ❌ NOT in git (gitignored)
│   ├── .env.example      # ✅ Committed (template only)
│   └── .gitignore        # ✅ Contains .env
└── frontend/
    ├── .env              # ❌ NOT in git (gitignored)
    ├── .env.example      # ✅ Committed (template only)
    └── .gitignore        # ✅ Contains .env
```

---

## 🛠️ Local Development Setup

### Backend Setup

1. **Copy the example file:**
   ```bash
   cd backend
   cp .env.example .env
   ```

2. **Generate SECRET_KEY:**
   ```bash
   openssl rand -hex 32
   ```

3. **Edit `.env` with real values:**
   ```bash
   # backend/.env
   # Copy GOOGLE_CLIENT_ID from frontend/.env (same value for both)
   GOOGLE_CLIENT_ID=<see frontend/.env for actual value>
   # Generate with: openssl rand -hex 32
   SECRET_KEY=<generate new secret key>
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
   ```

4. **Verify it's gitignored:**
   ```bash
   git status  # .env should NOT appear
   ```

### Frontend Setup

1. **Copy the example file:**
   ```bash
   cd frontend
   cp .env.example .env
   ```

2. **Edit `.env` with real values:**
   ```bash
   # frontend/.env
   # Get from: https://console.cloud.google.com/apis/credentials
   REACT_APP_GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
   REACT_APP_API_URL=http://localhost:8000
   ```

3. **Verify it's gitignored:**
   ```bash
   git status  # .env should NOT appear
   ```

---

## ☁️ Production Deployment

### Backend (AWS Lambda)

#### Option 1: AWS SAM Template (Recommended)

Edit `backend/template.yaml`:

```yaml
Parameters:
  GoogleClientId:
    Type: String
    Description: Google OAuth Client ID
    NoEcho: false

  JWTSecretKey:
    Type: String
    Description: Secret key for JWT signing
    NoEcho: true  # Hide from console output

  AllowedOrigins:
    Type: String
    Description: Comma-separated CORS origins
    Default: "https://your-app.vercel.app"
```

**Deploy with parameters:**
```bash
sam deploy --guided \
  --parameter-overrides \
    GoogleClientId="<see frontend/.env>" \
    JWTSecretKey="<see backend/.env>" \
    AllowedOrigins="https://your-app.vercel.app"
```

#### Option 2: AWS Console

1. **Go to Lambda Console** → Your function
2. **Configuration** → **Environment variables**
3. **Add variables:**
   - `GOOGLE_CLIENT_ID` = `<see frontend/.env>`
   - `SECRET_KEY` = `<see backend/.env>`
   - `ALLOWED_ORIGINS` = `https://your-app.vercel.app`

![AWS Lambda Environment Variables](https://docs.aws.amazon.com/images/lambda/latest/dg/images/console-env-variables.png)

#### Option 3: AWS Secrets Manager (Production Best Practice)

**Store secrets in Secrets Manager:**
```bash
# Create secret
aws secretsmanager create-secret \
  --name job-hunt-tracker/prod/secrets \
  --secret-string '{
    "GOOGLE_CLIENT_ID": "<see frontend/.env>",
    "SECRET_KEY": "<see backend/.env>"
  }'
```

**Update Lambda to read from Secrets Manager:**
```python
# In your Lambda code
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='job-hunt-tracker/prod/secrets')
    return json.loads(response['SecretString'])

secrets = get_secrets()
GOOGLE_CLIENT_ID = secrets['GOOGLE_CLIENT_ID']
```

**Grant Lambda permission:**
- Attach policy: `SecretsManagerReadWrite` to Lambda execution role

---

### Frontend (Vercel)

#### Step 1: Deploy to Vercel

```bash
cd frontend
npm install -g vercel
vercel login
vercel
```

#### Step 2: Set Environment Variables in Vercel

**Via Vercel Dashboard:**

1. Go to: https://vercel.com/dashboard
2. Select your project
3. **Settings** → **Environment Variables**
4. Add variables:

| Name | Value | Environments |
|------|-------|--------------|
| `REACT_APP_GOOGLE_CLIENT_ID` | `<see frontend/.env>` | Production, Preview, Development |
| `REACT_APP_API_URL` | `https://your-api-id.execute-api.us-east-1.amazonaws.com/prod` | Production |
| `REACT_APP_API_URL` | `http://localhost:8000` | Development |

![Vercel Environment Variables](https://vercel.com/_next/image?url=https%3A%2F%2Fimages.ctfassets.net%2Fe5382hct74si%2F4YQsOzLdYdBhLEjDm0JHwa%2F2e0e8e5f8c4e3e3e3e3e3e3e3e3e3e3e%2Fenv-vars.png&w=3840&q=75)

**Via Vercel CLI:**

```bash
vercel env add REACT_APP_GOOGLE_CLIENT_ID production
# Paste value from frontend/.env when prompted

vercel env add REACT_APP_API_URL production
# Enter: https://your-api-id.execute-api.us-east-1.amazonaws.com/prod
```

#### Step 3: Redeploy

After adding environment variables:
```bash
vercel --prod
```

Or push to git (auto-deploys):
```bash
git push origin main
```

---

## 🔗 Connecting Frontend to Backend

### Update CORS After Deployment

Once you have your Vercel URL (e.g., `https://job-hunt-tracker.vercel.app`):

1. **Update Backend CORS:**

   **Option A: Lambda Environment Variables**
   ```
   ALLOWED_ORIGINS=https://job-hunt-tracker.vercel.app,http://localhost:3000
   ```

   **Option B: Update SAM template**
   ```yaml
   AllowedOrigins: "https://job-hunt-tracker.vercel.app"
   ```

2. **Redeploy backend:**
   ```bash
   sam deploy
   ```

### Update Frontend API URL

1. **In Vercel Environment Variables:**
   ```
   REACT_APP_API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/prod
   ```

2. **Redeploy frontend:**
   ```bash
   vercel --prod
   ```

---

## 🔄 Full Deployment Flow

### Initial Setup

```bash
# 1. Deploy Backend to AWS
cd backend
sam build
sam deploy --guided
# Note the API Gateway URL from output

# 2. Update Google OAuth Redirect URIs
# Go to: https://console.cloud.google.com/apis/credentials
# Add: https://your-vercel-app.vercel.app

# 3. Deploy Frontend to Vercel
cd ../frontend
vercel
# Set environment variables in Vercel dashboard

# 4. Update Backend CORS with Vercel URL
# Update Lambda environment variable: ALLOWED_ORIGINS

# 5. Test the flow
# Visit: https://your-vercel-app.vercel.app
```

### Making Changes

```bash
# Backend changes
cd backend
# Make code changes
sam build && sam deploy

# Frontend changes
cd frontend
# Make code changes
git push  # Auto-deploys via Vercel GitHub integration
```

---

## 📋 Environment Variables Reference

### Backend Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | ✅ Yes | Google OAuth Client ID | `<see frontend/.env>` |
| `GOOGLE_CLIENT_SECRET` | ❌ No | Google OAuth Secret (optional) | Leave empty for ID token validation |
| `SECRET_KEY` | ✅ Yes | JWT signing key (256-bit hex) | `<see backend/.env>` or generate: `openssl rand -hex 32` |
| `ALGORITHM` | ❌ No | JWT algorithm | `HS256` (default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ No | JWT expiration time | `1440` (24 hours, default) |
| `ALLOWED_ORIGINS` | ❌ No | CORS allowed origins | `https://your-app.vercel.app` |

### Frontend Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `REACT_APP_GOOGLE_CLIENT_ID` | ✅ Yes | Google OAuth Client ID | `<see frontend/.env>` |
| `REACT_APP_API_URL` | ✅ Yes | Backend API base URL | `https://api-id.execute-api.us-east-1.amazonaws.com/prod` |

---

## 🐛 Troubleshooting

### "Environment variable not found" error

**Problem:** Pydantic can't find required variables

**Solution:**
```bash
# Check .env file exists
ls backend/.env

# Check values are set
cat backend/.env

# Ensure no typos in variable names
```

### CORS errors in browser

**Problem:** `Access-Control-Allow-Origin` error

**Solution:**
```python
# Update backend ALLOWED_ORIGINS to include your Vercel URL
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

### "Invalid authentication token" on production

**Problem:** Google Client ID mismatch

**Solution:**
- Ensure **same** `GOOGLE_CLIENT_ID` in both frontend and backend (copy from frontend/.env)
- Check Google Console → Credentials → Authorized JavaScript origins includes Vercel URL

### Changes not reflecting on Vercel

**Problem:** Old environment variable values

**Solution:**
```bash
# Redeploy after changing env vars
vercel --prod --force
```

---

## 🔐 Security Best Practices

### Rotate Secrets Regularly

```bash
# Generate new JWT secret
openssl rand -hex 32

# Update in all environments:
# - Local: backend/.env
# - AWS: Lambda environment variables
# - Redeploy
```

### Different Secrets per Environment

```
Development:  SECRET_KEY=dev_secret_key_here
Staging:      SECRET_KEY=staging_secret_key_here
Production:   SECRET_KEY=prod_secret_key_here
```

### Monitor Access

- **AWS:** Enable CloudTrail to log Lambda invocations
- **Vercel:** Check deployment logs in dashboard

### Least Privilege

- Lambda execution role: Only permissions needed
- Secrets Manager: Restrict to specific Lambda ARNs

---

## 📚 Additional Resources

- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Create React App Environment Variables](https://create-react-app.dev/docs/adding-custom-environment-variables/)
