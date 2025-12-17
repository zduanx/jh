# Environment Variables Management

## Overview

This project uses different environment variables for local development vs production deployment. The `.env.local` files contain local development values with production values documented in special comments.

## File Locations

- **Backend (Local)**: `backend/.env.local` (gitignored)
- **Frontend (Local)**: `frontend/.env.local` (gitignored)
- **Backend (Production)**: AWS Lambda Console → Environment Variables
- **Frontend (Production)**: Vercel Dashboard → Environment Variables

## Production Value Format

Production values are documented using special comments in `.env.local` files:

```bash
# Local development value
VARIABLE_NAME=local_value
# VARIABLE_NAME_PROD_VALUE=production_value
```

### Example (Frontend):

```bash
# Backend API URL
REACT_APP_API_URL=http://localhost:8000
# REACT_APP_API_URL_PROD_VALUE=https://ub6uz1k584.execute-api.us-east-1.amazonaws.com/prod
```

### Example (Backend):

```bash
# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
# ALLOWED_ORIGINS_PROD_VALUE=https://zduan-job.vercel.app,http://localhost:3000
```

## Why This Format?

1. **No hardcoded secrets in dev.sh**: Scripts parse production values from `.env.local` comments
2. **Single source of truth**: Production values are documented next to their local counterparts
3. **Easy parsing**: The `# <VAR_NAME>_PROD_VALUE=` format makes it easy to identify which variable's production value is being defined
4. **Version controlled comments**: While `.env.local` is gitignored, the format is documented

## Deployment Commands

### Backend (AWS Lambda)

```bash
jpushapi
```

This command:
- Builds with SAM
- Deploys to AWS
- Verifies environment variables are set
- Compares with values from `backend/.env.local`

### Frontend (Vercel)

```bash
jpushvercel
```

This command:
- Checks Vercel project status
- Compares environment variables with `frontend/.env.local`
- Handles encrypted/sensitive variables
- Offers deployment via git or manual

### Environment Check

```bash
jenvcheck
```

Quick verification of all environment variables without deploying.

## Encrypted Variables (Vercel)

Vercel allows marking variables as "Sensitive" which encrypts them. The CLI cannot retrieve their values, so:

- `jpushreact` and `jenvcheck` detect if variables exist
- Shows "Encrypted/Sensitive" status
- Displays expected value from `.env.local` for manual verification
- Provides link to Vercel Dashboard

## Backend Production Values

| Variable | Source | Notes |
|----------|--------|-------|
| `GOOGLE_CLIENT_ID` | `# GOOGLE_CLIENT_ID_PROD_VALUE=` | Google OAuth credentials |
| `SECRET_KEY` | `# SECRET_KEY_PROD_VALUE=` | JWT signing key |
| `ALLOWED_ORIGINS` | `# ALLOWED_ORIGINS_PROD_VALUE=` | Includes Vercel app URL |
| `ALLOWED_EMAILS` | `# ALLOWED_EMAILS_PROD_VALUE=` | Comma-separated allowed users |
| `DATABASE_URL` | `# DATABASE_URL_PROD_VALUE=` | **Production database branch** |

## Frontend Production Values

| Variable | Source | Notes |
|----------|--------|-------|
| `REACT_APP_GOOGLE_CLIENT_ID` | `# REACT_APP_GOOGLE_CLIENT_ID_PROD_VALUE=` | Google OAuth client ID |
| `REACT_APP_API_URL` | `# REACT_APP_API_URL_PROD_VALUE=` | AWS API Gateway URL |

## Database URLs

**CRITICAL**: Local and production use different database branches:

- **Local** (`DATABASE_URL`): `ep-aged-darkness-ahpqrn39-pooler` (test/dev branch)
- **Production** (`# PROD_VALUE=`): `ep-quiet-hat-ahe8vhso-pooler` (production branch)

## Troubleshooting

### "differs" errors in jenvcheck

If you see comparison errors:

1. Check for trailing newlines: Vercel sometimes adds `\n` to values
2. Verify the value in Vercel Dashboard (for encrypted variables)
3. Update `.env.local` <VAR_NAME>_PROD_VALUE comment if production changed

### DATABASE_URL not set in Lambda

Lambda doesn't get `DATABASE_URL` from `samconfig.toml` by default. Add it manually:

1. Go to AWS Lambda Console → JobHuntTrackerAPI
2. Configuration → Environment variables
3. Add `DATABASE_URL` with the production value from `backend/.env.local` comment

### Vercel variable is empty

If a Vercel variable shows as empty but exists:

1. It's likely marked as "Sensitive/Encrypted"
2. Check Vercel Dashboard to verify it's set
3. The value cannot be retrieved via CLI for security reasons

## See Also

- [Local Development](./LOCAL_DEVELOPMENT.md)
- [Deployment Guide](./ENVIRONMENT_SETUP.md)
- Session Guide: Security Rules section
