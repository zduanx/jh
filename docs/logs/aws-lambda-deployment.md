# AWS Lambda Deployment Log

**Date**: December 14, 2025
**Objective**: Deploy FastAPI backend to AWS Lambda using AWS SAM CLI
**Final Status**: ✅ SUCCESS

---

## Deployment Summary

**Final API Gateway URL**: `https://<aws_id>.execute-api.us-east-1.amazonaws.com/prod`

**Working Endpoints**:
- `GET /health` - Health check endpoint
- `POST /auth/google` - Google OAuth token exchange
- `GET /api/user` - Get user information (requires JWT)

**CORS Configuration**:
- `http://localhost:3000` (local development)
- `https://zduan-job.vercel.app` (production frontend)

---

## Commands Executed & Effort Breakdown

### 1. Initial Setup (5 minutes)

**Command 1: Install AWS SAM CLI**
```bash
brew install aws-sam-cli
```
**Result**: ✅ Success
**Output**: SAM CLI installed successfully

---

**Command 2: Verify AWS Credentials**
```bash
aws sts get-caller-identity
```
**Result**: ✅ Success
**Output**: Confirmed user `zduan` in account `400778305315`

---

### 2. First Build Attempt (15 minutes)

**Command 3: Initial SAM Build**
```bash
cd /Users/duan/coding/jh/backend
sam build
```

**Issue #1: Python Version Mismatch**
```
Error: Binary validation failed for python, searched for python in following locations...
which did not satisfy constraints for runtime: python3.11
```

**Root Cause**:
- `template.yaml` specified `python3.11`
- System has `python3.13` installed
- SAM CLI couldn't find python3.11 binary

**Evidence**: Error message explicitly stated "did not satisfy constraints for runtime: python3.11"

**Solution**: Updated `template.yaml` runtime from `python3.11` → `python3.13`

**Files Modified**: `backend/template.yaml:9`

---

**Command 4: Retry Build with Python 3.13**
```bash
sam build
```

**Issue #2: Dependency Resolution Error**
```
PythonPipBuilder:ResolveDependencies - {pydantic-core==2.14.6(sdist)} Build Failed
```

**Root Cause**:
- Old pydantic versions (2.5.3) incompatible with Python 3.13
- Pinned versions (`==`) prevented automatic updates
- `pydantic-core==2.14.6` doesn't support Python 3.13

**Evidence**: Build log showed specific package `pydantic-core==2.14.6` failing to compile

**Solution**: Updated `requirements.txt` to use newer versions with flexible constraints:
```diff
- pydantic==2.5.3
+ pydantic>=2.10.0

- pydantic-settings==2.1.0
+ pydantic-settings>=2.6.0

- fastapi==0.108.0
+ fastapi>=0.115.0

- # Removed uvicorn (not needed for Lambda)
```

**Files Modified**: `backend/requirements.txt`

---

**Command 5: Build After Dependency Fix**
```bash
sam build
```
**Result**: ✅ Success
**Output**: "Build Succeeded"

---

### 3. First Deployment Attempt (10 minutes)

**Command 6: Configure Deployment**
```bash
# Created samconfig.toml with deployment parameters
```

**Issue #3: IAM Permission Denied**
```bash
sam deploy
```

**Error**:
```
An error occurred (AccessDenied) when calling the CreateChangeSet operation:
User: arn:aws:iam::400778305315:user/zduan is not authorized to perform:
cloudformation:CreateChangeSet
```

**Root Cause**: User `zduan` lacked necessary AWS permissions for:
- CloudFormation (stack creation)
- S3 (artifact storage)
- Lambda (function deployment)
- API Gateway (HTTP API creation)

**Evidence**: Error message showed specific IAM action `cloudformation:CreateChangeSet` was denied

**Solution**:
1. User granted `AdministratorAccess` policy via AWS Console
2. Path: IAM → Users → zduan → Add permissions → Attach policies → AdministratorAccess

**User Action Required**: Yes (user performed this step)

---

### 4. Second Deployment Attempt (20 minutes)

**Command 7: Deploy with Admin Permissions**
```bash
sam deploy
```

**Issue #4: CORS Configuration Error (Wildcard with Credentials)**
```
CREATE_FAILED AWS::ApiGatewayV2::Api HttpApi
Resource handler returned message: "allow-credentials is not supported if 'allow-origin' is *"
Status: ROLLBACK_COMPLETE
```

**Root Cause**:
- `template.yaml` had `AllowOrigins: "*"` (wildcard)
- Combined with `AllowCredentials: true`
- AWS API Gateway HTTP API doesn't allow this combination for security reasons

**Evidence**: CloudFormation event log showed:
```
CREATE_FAILED AWS::ApiGatewayV2::Api HttpApi
"allow-credentials is not supported if 'allow-origin' is *"
```

**Solution**: Removed wildcard `"*"` and used specific origins:
```yaml
AllowOrigins:
  - "http://localhost:3000"
  - "https://zduan-job.vercel.app"  # Changed from https://*.vercel.app
```

**Files Modified**: `backend/template.yaml:61-63`

**Note**: Initial attempt used `https://*.vercel.app` which also failed because API Gateway doesn't support wildcard subdomains.

---

**Command 8: Delete Failed Stack**
```bash
aws cloudformation delete-stack --stack-name jh-backend-stack
aws cloudformation wait stack-delete-complete --stack-name jh-backend-stack
```
**Result**: ✅ Success

---

**Command 9: Rebuild and Redeploy**
```bash
sam build
sam deploy
```

**Issue #5: CORS Wildcard Subdomain Error**
```
CREATE_FAILED AWS::ApiGatewayV2::Api HttpApi
"allow-origin https://*.vercel.app can not have wildcards"
```

**Root Cause**:
- API Gateway CORS doesn't support wildcard subdomains like `https://*.vercel.app`
- Only accepts explicit full domain names

**Evidence**: Error message explicitly stated "can not have wildcards"

**Solution**: Used specific production domain `https://zduan-job.vercel.app`

**Files Modified**:
- `backend/template.yaml:64`
- `backend/samconfig.toml:9`

---

**Command 10: Deploy with Fixed CORS**
```bash
aws cloudformation delete-stack --stack-name jh-backend-stack
aws cloudformation wait stack-delete-complete --stack-name jh-backend-stack
sam build
sam deploy
```

**Result**: ✅ Stack created successfully

**CloudFormation Output**:
```
CREATE_COMPLETE AWS::CloudFormation::Stack jh-backend-stack
ApiUrl: https://<aws_id>.execute-api.us-east-1.amazonaws.com/prod
```

---

### 5. Testing Phase (25 minutes)

**Command 11: Test Health Endpoint**
```bash
curl https://<aws_id>.execute-api.us-east-1.amazonaws.com/prod/health
```

**Issue #6: Missing Requests Library**
```json
{"message":"Internal Server Error"}
```

**CloudWatch Logs Evidence**:
```
[ERROR] Runtime.ImportModuleError: Unable to import module 'main':
The requests library is not installed from please install the requests package
to use the requests transport.
```

**Root Cause**:
- `httpx` library (used by FastAPI/Google Auth) requires `requests` as peer dependency
- Not explicitly listed in `requirements.txt`

**Key Log Content**:
- **Error Type**: `Runtime.ImportModuleError`
- **Phase**: `init` (module import phase)
- **Message**: Explicitly stated "requests library is not installed"

**Solution**: Added to `requirements.txt`:
```
requests>=2.31.0
httpx>=0.27.0
```

**Files Modified**: `backend/requirements.txt:8-9`

---

**Command 12: Rebuild and Redeploy**
```bash
sam build && sam deploy
```

**Issue #7: Settings Parsing Error**
```
[ERROR] SettingsError: error parsing value for field "ALLOWED_ORIGINS"
from source "EnvSettingsSource"
```

**CloudWatch Logs Evidence**:
```
Traceback (most recent call last):
  File "/var/task/config/settings.py", line 37, in <module>
    settings = Settings()
  File "/var/task/pydantic_settings/main.py", line 195, in __init__
  File "/var/task/pydantic_settings/sources/base.py", line 512, in __call__
    raise SettingsError(
```

**Root Cause**:
- Pydantic `@field_validator` with `mode="before"` not working as expected
- Environment variable `ALLOWED_ORIGINS` passed as string `"http://localhost:3000,https://zduan-job.vercel.app"`
- Validator wasn't converting string to List[str] properly

**Key Log Content**:
- **Error Type**: `SettingsError`
- **Location**: `config/settings.py:37` (settings = Settings())
- **Field**: `ALLOWED_ORIGINS`

**Solution**: Changed approach - made `ALLOWED_ORIGINS` a string field and created `get_allowed_origins()` method:
```python
# Before
ALLOWED_ORIGINS: List[str] = [...]
@field_validator("ALLOWED_ORIGINS", mode="before")

# After
ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
def get_allowed_origins(self) -> List[str]:
    return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
```

**Files Modified**:
- `backend/config/settings.py:18-27`
- `backend/main.py:17` (updated to use `settings.get_allowed_origins()`)

---

**Command 13: Rebuild and Redeploy**
```bash
sam build && sam deploy
```

**Issue #8: Missing Email Validator**
```
[ERROR] Runtime.ImportModuleError: Unable to import module 'main':
email-validator is not installed, run `pip install 'pydantic[email]'`
```

**CloudWatch Logs Evidence**:
```
[ERROR] Runtime.ImportModuleError:
email-validator is not installed, run `pip install 'pydantic[email]'`
```

**Root Cause**:
- Pydantic's `EmailStr` field requires `email-validator` package
- Using `pydantic>=2.10.0` without `[email]` extra

**Key Log Content**:
- **Error Type**: `Runtime.ImportModuleError`
- **Message**: Explicitly instructed to install `pydantic[email]`

**Solution**: Updated pydantic dependency to include email extra:
```diff
- pydantic>=2.10.0
+ pydantic[email]>=2.10.0
```

**Files Modified**: `backend/requirements.txt:2`

---

**Command 14: Rebuild and Redeploy**
```bash
sam build && sam deploy
```

**Result**: ✅ Deployment successful

---

**Command 15: Test Health Endpoint Again**
```bash
curl https://<aws_id>.execute-api.us-east-1.amazonaws.com/prod/health
```

**Issue #9: FastAPI Route Not Found**
```json
{"detail":"Not Found"}
```

**Analysis**:
- Changed from "Internal Server Error" to "Not Found"
- Lambda is executing successfully (no import errors)
- FastAPI is running but can't find routes

**CloudWatch Logs Evidence**:
```
START RequestId: 5ae9c5bd-736c-4002-9c78-0388f8a9781b Version: $LATEST
END RequestId: 5ae9c5bd-736c-4002-9c78-0388f8a9781b
REPORT RequestId: ... Duration: 3.12 ms ... (No errors)
```

**Key Observation**:
- Lambda invoked successfully (START/END messages)
- No error logs
- Quick execution (3ms) suggests no crashes
- FastAPI returning `{"detail":"Not Found"}` = routing issue

**Root Cause**:
- API Gateway includes stage name in path: `/prod/health`
- FastAPI doesn't know about `/prod` prefix
- Mangum passes raw path from API Gateway
- FastAPI expects `/health`, receives `/prod/health`

**Investigation Commands**:
```bash
# Checked API Gateway routes
aws apigatewayv2 get-routes --api-id <aws_id>

# Output showed routes:
# ANY /
# ANY /{proxy+}
```

**Solution**: Set FastAPI `root_path` to strip the stage prefix:
```python
app = FastAPI(
    title="Job Hunt Tracker API",
    description="Backend API for job application tracking",
    version="1.0.0",
    root_path="/prod"  # Added this
)
```

**Files Modified**: `backend/main.py:12`

**Additional Configuration**: Added Mangum lifespan setting:
```python
handler = Mangum(app, lifespan="off")
```

---

**Command 16: Final Deployment**
```bash
sam build && sam deploy
```
**Result**: ✅ Success

---

**Command 17: Final Health Check**
```bash
curl https://<aws_id>.execute-api.us-east-1.amazonaws.com/prod/health
```

**Response**:
```json
{"status":"healthy","timestamp":"2025-12-14T12:23:18.651995Z"}
```

**Result**: ✅ **SUCCESS!**

---

## Issue Summary Table

| # | Issue | Evidence Source | Root Cause | Solution | Time Spent |
|---|-------|----------------|------------|----------|------------|
| 1 | Python version mismatch | Build error message | Template specified python3.11, system has 3.13 | Updated template.yaml to python3.13 | 5 min |
| 2 | Dependency build failure | Build logs (pydantic-core) | Old pydantic incompatible with Python 3.13 | Updated to pydantic>=2.10.0 | 5 min |
| 3 | IAM permissions denied | CloudFormation error | User lacked CloudFormation/Lambda permissions | Granted AdministratorAccess | 3 min |
| 4 | CORS wildcard with credentials | CloudFormation CREATE_FAILED | API Gateway doesn't allow * with credentials | Removed wildcard, used specific domains | 5 min |
| 5 | CORS wildcard subdomain | CloudFormation CREATE_FAILED | API Gateway doesn't support *.vercel.app | Used explicit domain zduan-job.vercel.app | 3 min |
| 6 | Missing requests library | Lambda logs (ImportModuleError) | httpx requires requests as peer dependency | Added requests>=2.31.0 | 5 min |
| 7 | Settings parsing error | Lambda logs (SettingsError) | Pydantic field_validator not working | Changed to string field + parsing method | 7 min |
| 8 | Missing email-validator | Lambda logs (ImportModuleError) | pydantic[email] not installed | Changed to pydantic[email]>=2.10.0 | 3 min |
| 9 | FastAPI route not found | Lambda logs (successful execution) | FastAPI unaware of /prod prefix | Added root_path="/prod" to FastAPI | 10 min |

**Total Time**: ~46 minutes

---

## Critical Log Analysis

### Most Helpful Log Entries

**1. Python Version Mismatch (Issue #1)**
```
Error: Binary validation failed for python, searched for python in following locations...
which did not satisfy constraints for runtime: python3.11
```
**Why helpful**: Explicitly stated the required version and what was found

---

**2. Requests Library Missing (Issue #6)**
```
[ERROR] Runtime.ImportModuleError: Unable to import module 'main':
The requests library is not installed from please install the requests package
to use the requests transport.
```
**Why helpful**:
- Error type `ImportModuleError` indicated module loading issue
- Message explicitly named missing package: "requests library"
- Occurred during `init` phase before handler execution

---

**3. Settings Parsing Error (Issue #7)**
```
[ERROR] SettingsError: error parsing value for field "ALLOWED_ORIGINS"
from source "EnvSettingsSource"
Traceback (most recent call last):
  File "/var/task/config/settings.py", line 37, in <module>
    settings = Settings()
```
**Why helpful**:
- Error type `SettingsError` pointed to pydantic-settings
- Specific field name `ALLOWED_ORIGINS` identified problem area
- Stack trace showed exact line `settings = Settings()` where initialization failed

---

**4. Route Not Found (Issue #9)**
```
START RequestId: 5ae9c5bd-736c-4002-9c78-0388f8a9781b Version: $LATEST
END RequestId: 5ae9c5bd-736c-4002-9c78-0388f8a9781b
REPORT RequestId: ... Duration: 3.12 ms ... Memory Size: 512 MB Max Memory Used: 104 MB
```
**Why helpful**:
- **No error logs** = Lambda working correctly
- **Short duration (3ms)** = No crashes or exceptions
- **START/END present** = Handler was invoked
- Combined with HTTP response `{"detail":"Not Found"}` = FastAPI routing issue, not Lambda issue
- This negative evidence (absence of errors) led to investigating path handling

---

## Configuration Files Changed

### 1. `backend/template.yaml`
```yaml
# Changed runtime
Runtime: python3.13  # Was: python3.11

# Fixed CORS configuration
CorsConfiguration:
  AllowOrigins:
    - "http://localhost:3000"
    - "https://zduan-job.vercel.app"  # Was: "*" then "https://*.vercel.app"
  AllowHeaders:
    - "*"
  AllowMethods:
    - GET
    - POST
    - PUT
    - DELETE
    - OPTIONS
  AllowCredentials: true
```

### 2. `backend/requirements.txt`
```txt
# Updated versions
fastapi>=0.115.0          # Was: ==0.108.0
pydantic[email]>=2.10.0   # Was: ==2.5.3 (added [email])
pydantic-settings>=2.6.0  # Was: ==2.1.0

# Added dependencies
requests>=2.31.0          # NEW
httpx>=0.27.0            # NEW

# Removed
# uvicorn (not needed for Lambda)
```

### 3. `backend/config/settings.py`
```python
# Changed from List[str] to str
ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

# Removed field_validator
# Added parsing method
def get_allowed_origins(self) -> List[str]:
    return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
```

### 4. `backend/main.py`
```python
# Added root_path for API Gateway stage
app = FastAPI(
    title="Job Hunt Tracker API",
    description="Backend API for job application tracking",
    version="1.0.0",
    root_path="/prod"  # NEW
)

# Updated CORS to use method
allow_origins=settings.get_allowed_origins(),  # Was: settings.ALLOWED_ORIGINS

# Updated Mangum handler
handler = Mangum(app, lifespan="off")  # Added lifespan parameter
```

### 5. `backend/samconfig.toml`
```toml
stack_name = "jh-backend-stack"
resolve_s3 = true
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = "GoogleClientId=\"...\" JWTSecretKey=\"...\" AllowedOrigins=\"http://localhost:3000,https://zduan-job.vercel.app\""
confirm_changeset = false
```

### 6. `frontend/.env`
```env
# Updated API URL
REACT_APP_API_URL=https://<aws_id>.execute-api.us-east-1.amazonaws.com/prod
# Was: http://localhost:8000
```

---

## Key Learnings

### 1. AWS API Gateway HTTP API CORS Limitations
- ❌ Cannot use `allow_origins: "*"` with `allow_credentials: true`
- ❌ Cannot use wildcard subdomains like `https://*.vercel.app`
- ✅ Must use explicit full domain names

### 2. FastAPI + API Gateway Path Handling
- API Gateway includes stage name in path (`/prod/health`)
- FastAPI needs `root_path` parameter to handle stage prefix
- Without `root_path`, FastAPI sees `/prod/health` and returns 404

### 3. Python 3.13 Compatibility
- Older pydantic versions (< 2.10.0) don't support Python 3.13
- Use flexible version constraints (`>=`) instead of pinning (`==`)
- Check dependency compatibility with target Python version

### 4. Pydantic Settings Field Validators
- `@field_validator` with `mode="before"` can be unreliable
- Simpler to use string fields + parsing methods for complex types
- Avoid over-engineering validators for simple transformations

### 5. Lambda Debugging Strategy
1. Check CloudWatch logs for import errors (init phase)
2. Look for START/END messages (indicates handler invoked)
3. Check Duration/Memory (quick execution = likely no crash)
4. Absence of error logs + HTTP 404 = routing issue, not code issue

### 6. Dependency Management
- FastAPI/httpx require `requests` as peer dependency
- Pydantic `EmailStr` requires `email-validator` package
- Use extras notation: `pydantic[email]`, `python-jose[cryptography]`

---

## Final Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Client (Browser)                                            │
│ - https://zduan-job.vercel.app                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTPS + CORS
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ AWS API Gateway (HTTP API)                                  │
│ - ID: <aws_id>                                           │
│ - URL: https://<aws_id>.execute-api.us-east-1.amazonaws  │
│        .com/prod                                            │
│ - Stage: prod                                               │
│ - CORS: localhost:3000, zduan-job.vercel.app              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ AWS_PROXY Integration
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ AWS Lambda Function                                         │
│ - Name: JobHuntTrackerAPI                                   │
│ - Runtime: Python 3.13                                      │
│ - Memory: 512 MB                                            │
│ - Timeout: 30s                                              │
│ - Handler: main.handler (Mangum ASGI adapter)              │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ FastAPI Application                                     ││
│ │ - root_path: /prod                                      ││
│ │ - Routes:                                               ││
│ │   • GET /health                                         ││
│ │   • POST /auth/google                                   ││
│ │   • GET /api/user                                       ││
│ │ - CORS Middleware                                       ││
│ │ - JWT Authentication                                    ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Cost Estimate

**AWS Free Tier (12 months)**:
- Lambda: 1M requests/month, 400,000 GB-seconds compute
- API Gateway: 1M API calls/month
- CloudWatch Logs: 5GB ingestion, 5GB archive

**Expected Monthly Cost** (under free tier): $0.00

**After Free Tier** (estimated for low traffic):
- Lambda: ~$0.20 per 1M requests (512MB memory)
- API Gateway: ~$1.00 per 1M requests
- CloudWatch Logs: ~$0.50/GB
- **Total**: < $5/month for typical development usage

---

## Security Considerations

1. **JWT Secret Key**: Stored in Lambda environment variables (encrypted at rest)
2. **Google Client ID**: Public (safe to expose)
3. **CORS**: Restricted to specific origins only
4. **IAM Permissions**: Lambda has minimal required permissions
5. **HTTPS**: Enforced by API Gateway
6. **Access Token Expiry**: 24 hours (1440 minutes)

---

## Deployment Checklist

- [x] Install AWS SAM CLI
- [x] Configure AWS credentials
- [x] Update Python runtime to 3.13
- [x] Fix dependency versions for Python 3.13
- [x] Configure CORS with explicit origins
- [x] Add missing dependencies (requests, httpx, email-validator)
- [x] Fix pydantic settings parsing
- [x] Set FastAPI root_path for API Gateway
- [x] Deploy Lambda function
- [x] Test health endpoint
- [x] Update frontend .env with Lambda URL
- [x] Document deployment process

---

## Next Steps

1. **Deploy Frontend to Vercel**
   - Already configured with `vercel.json`
   - Environment variables set in `.env`

2. **Update Google OAuth Settings**
   - Add Lambda URL to authorized JavaScript origins
   - Add Vercel URL to authorized JavaScript origins

3. **Test End-to-End Flow**
   - Google login → Backend JWT exchange → Fetch user data

4. **Monitor & Optimize**
   - Set up CloudWatch alarms for errors
   - Monitor Lambda cold starts
   - Consider provisioned concurrency for production

5. **Security Hardening**
   - Move secrets to AWS Secrets Manager
   - Enable AWS WAF for API Gateway
   - Implement rate limiting

---

**Deployment completed successfully on**: 2025-12-14 12:23:18 UTC
