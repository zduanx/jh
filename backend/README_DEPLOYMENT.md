# Backend Deployment Configuration

## Overview

The backend deployment system automatically generates `template.yaml` (CloudFormation template) and `samconfig.toml` (SAM CLI config) from two source files:

- **`.sam-config`**: Deployment metadata (committed to git)
- **`.env.local`**: Environment variables with production values (gitignored)

## File Structure

```
backend/
├── .sam-config              # Deployment metadata (committed)
├── .env.local               # Environment variables (gitignored)
├── .env.example             # Template for .env.local (committed)
├── template.yaml            # Auto-generated CloudFormation template
├── samconfig.toml           # Auto-generated SAM CLI config
└── scripts/
    ├── generate_template.py    # Generates template.yaml
    └── generate_samconfig.py   # Generates samconfig.toml
```

## Configuration Files

### `.sam-config` (Deployment Metadata)

Contains pure deployment configuration with no secrets. Safe to commit to git.

**What it contains:**
- CloudFormation stack name, region, capabilities
- Lambda function configuration (name, description, handler, timeout, memory, runtime)
- API Gateway configuration (stage name, CORS origins)
- Static environment variables (same across all environments)

**Example:**
```bash
CFN_STACK_NAME=jh-backend-stack
CFN_REGION=us-east-1
LAMBDA_FUNCTION_NAME=JobHuntTrackerAPI
LAMBDA_FUNCTION_DESCRIPTION=FastAPI backend for Job Hunt Tracker
LAMBDA_TIMEOUT=30
LAMBDA_MEMORY=512
LAMBDA_RUNTIME=python3.13
API_STAGE_NAME=prod
API_CORS_ALLOW_ORIGINS=http://localhost:3000,https://zduan-job.vercel.app

# Static environment variables (not parameterized)
ENV_VAR_ALGORITHM=HS256
ENV_VAR_ACCESS_TOKEN_EXPIRE_MINUTES=1440
ENV_VAR_GOOGLE_CLIENT_SECRET=optional-for-token-validation
```

### `.env.local` (Environment Variables)

Contains environment variables with local and production values. Gitignored for security.

**Format for each parameterized variable:**
```bash
VARIABLE_NAME=local_value
# VARIABLE_NAME_PROD_VALUE=production_value
# VARIABLE_NAME_PARAM_NAME=CloudFormationParameterName
# VARIABLE_NAME_DESCRIPTION=Description for CloudFormation
# VARIABLE_NAME_NO_ECHO=true|false
# VARIABLE_NAME_DEFAULT=optional_default_value
```

**Example:**
```bash
GOOGLE_CLIENT_ID=local-dev-client-id.apps.googleusercontent.com
# GOOGLE_CLIENT_ID_PROD_VALUE=prod-client-id.apps.googleusercontent.com
# GOOGLE_CLIENT_ID_PARAM_NAME=GoogleClientId
# GOOGLE_CLIENT_ID_DESCRIPTION=Google OAuth Client ID
# GOOGLE_CLIENT_ID_NO_ECHO=false

SECRET_KEY=local-dev-secret-key
# SECRET_KEY_PROD_VALUE=production-secret-key
# SECRET_KEY_PARAM_NAME=JWTSecretKey
# SECRET_KEY_DESCRIPTION=Secret key for JWT signing (use openssl rand -hex 32)
# SECRET_KEY_NO_ECHO=true
```

## Deployment Workflow

When you run `jpushapi`, it automatically:

1. **Generates configuration files:**
   ```bash
   python3 scripts/generate_template.py  # Creates template.yaml
   python3 scripts/generate_samconfig.py # Creates samconfig.toml
   ```

2. **Checks Lambda environment variables** against `.env.local` PROD_VALUE comments

3. **Checks git status** for uncommitted `backend/` changes

4. **Confirms deployment** with user

5. **Builds and deploys** using SAM CLI

6. **Verifies deployment** by checking Lambda environment variables

## Modifying Configuration

### To add a new environment variable:

1. **Add to `.env.local`** with all metadata:
   ```bash
   NEW_VARIABLE=local-value
   # NEW_VARIABLE_PROD_VALUE=production-value
   # NEW_VARIABLE_PARAM_NAME=NewVariable
   # NEW_VARIABLE_DESCRIPTION=Description of the variable
   # NEW_VARIABLE_NO_ECHO=false
   ```

2. **Run `jpushapi`** - configuration files will be auto-generated

### To modify deployment settings:

1. **Edit `.sam-config`** - update Lambda config, API Gateway settings, etc.

2. **Run `jpushapi`** - `template.yaml` will be regenerated

### To change production values:

1. **Update PROD_VALUE comments in `.env.local`**:
   ```bash
   # VARIABLE_NAME_PROD_VALUE=new-production-value
   ```

2. **Run `jpushapi`** - `samconfig.toml` will be regenerated with new values

## Benefits

- **Single source of truth**: All configuration comes from `.sam-config` and `.env.local`
- **No manual YAML editing**: `template.yaml` is auto-generated
- **No manual TOML editing**: `samconfig.toml` is auto-generated
- **Consistent format**: Python scripts ensure correct syntax
- **Easy to update**: Just change comments in `.env.local` or values in `.sam-config`
- **Type safety**: Scripts validate and escape values properly
- **Git-friendly**: Only `.sam-config` and `.env.example` are committed

## Files That Are Generated (Do Not Edit Manually)

- `template.yaml` - Generated from `.sam-config` + `.env.local` metadata
- `samconfig.toml` - Generated from `.sam-config` + `.env.local` PROD_VALUE comments

## Files That You Should Edit

- `.sam-config` - Deployment metadata
- `.env.local` - Environment variables and production values
- `.env.example` - Template for new developers (update when adding new variables)
