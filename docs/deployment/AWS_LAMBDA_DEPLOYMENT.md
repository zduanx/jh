# AWS Lambda Deployment Guide

Complete step-by-step guide to deploy the FastAPI backend to AWS Lambda + API Gateway.

---

## 📋 Prerequisites

- AWS Account (Free tier eligible)
- AWS CLI installed and configured
- Python 3.13
- AWS SAM CLI (recommended) or manual deployment

---

## 🎯 Deployment Options

Choose one of these methods:

1. **AWS SAM CLI** (Recommended - easiest)
2. **Serverless Framework** (Popular alternative)
3. **AWS Console** (Manual - for learning)

---

## Option 1: AWS SAM CLI (Recommended)

### Step 1: Install AWS SAM CLI

**macOS:**
```bash
brew install aws-sam-cli
```

**Windows:**
```bash
# Download installer from:
# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
```

**Linux:**
```bash
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
```

**Verify installation:**
```bash
sam --version
# Should show: SAM CLI, version 1.x.x
```

### Step 2: Configure AWS Credentials

```bash
# Install AWS CLI if not already installed
pip install awscli

# Configure credentials
aws configure
```

Enter when prompted:
```
AWS Access Key ID: YOUR_ACCESS_KEY
AWS Secret Access Key: YOUR_SECRET_KEY
Default region: us-east-1
Default output format: json
```

**Get credentials from:**
1. AWS Console → IAM → Users → Your user → Security credentials
2. Create access key if you don't have one

### Step 3: Prepare Deployment

```bash
cd backend

# Ensure requirements.txt is up to date
cat requirements.txt

# Your template.yaml should already exist
cat template.yaml
```

### Step 4: Build the Application

```bash
sam build
```

**What this does:**
- Installs dependencies from `requirements.txt`
- Packages your code
- Creates `.aws-sam/build/` directory

**Expected output:**
```
Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml
```

### Step 5: Deploy (First Time)

```bash
sam deploy --guided
```

**You'll be prompted for:**

```bash
Stack Name [job-hunt-tracker-api]: job-hunt-tracker-api
AWS Region [us-east-1]: us-east-1
Parameter GoogleClientId []: <see frontend/.env>
Parameter JWTSecretKey []: <see backend/.env>
Parameter AllowedOrigins []: http://localhost:3000,http://localhost:5173
Confirm changes before deploy [Y/n]: Y
Allow SAM CLI IAM role creation [Y/n]: Y
Disable rollback [y/N]: N
JobHuntTrackerAPI has no authentication. Is this okay? [y/N]: y
Save arguments to configuration file [Y/n]: Y
SAM configuration file [samconfig.toml]: samconfig.toml
SAM configuration environment [default]: default
```

**Wait for deployment (2-5 minutes)...**

### Step 6: Get Your API URL

**After successful deployment:**
```
CloudFormation outputs from deployed stack
-------------------------------------------------------------------------
Outputs
-------------------------------------------------------------------------
Key                 ApiUrl
Description         API Gateway endpoint URL
Value               https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
-------------------------------------------------------------------------
```

**Save this URL!** You'll use it in your frontend.

### Step 7: Test the Deployment

```bash
# Test health endpoint
curl https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/health

# Expected response:
# {"status":"healthy","timestamp":"2024-12-13T10:30:00Z"}
```

### Step 8: Subsequent Deployments

After the first deployment, you can use:

```bash
sam build && sam deploy
# Uses saved config from samconfig.toml - no prompts!
```

---

## Option 2: Manual Deployment (AWS Console)

### Step 1: Package Dependencies

```bash
cd backend

# Create package directory
mkdir -p package

# Install dependencies
pip install -r requirements.txt -t package/

# Copy your code
cp main.py package/
cp -r auth/ api/ config/ package/

# Create deployment zip
cd package
zip -r ../deployment.zip .
cd ..
```

### Step 2: Create Lambda Function

1. **Go to AWS Console** → Lambda
2. **Create function**
   - Function name: `JobHuntTrackerAPI`
   - Runtime: `Python 3.11`
   - Architecture: `x86_64`
   - Click **Create function**

### Step 3: Upload Code

1. **Code source** section
2. **Upload from** → `.zip file`
3. Select `deployment.zip`
4. Click **Save**

### Step 4: Configure Handler

1. **Runtime settings** → **Edit**
2. **Handler**: `main.handler`
3. **Save**

### Step 5: Set Environment Variables

1. **Configuration** → **Environment variables** → **Edit**
2. **Add environment variables:**
   - `GOOGLE_CLIENT_ID` = `<see frontend/.env>`
   - `SECRET_KEY` = `<see backend/.env>`
   - `ALLOWED_ORIGINS` = `http://localhost:3000,http://localhost:5173`
3. **Save**

### Step 6: Create API Gateway

1. **Go to API Gateway** console
2. **Create API** → **HTTP API** → **Build**
3. **Add integration:**
   - Integration type: `Lambda`
   - Lambda function: `JobHuntTrackerAPI`
   - API name: `JobHuntTrackerHTTPAPI`
4. **Configure routes:**
   - Method: `ANY`
   - Resource path: `/{proxy+}`
5. **Configure CORS:**
   - Access-Control-Allow-Origin: `*` (or specific domains)
   - Access-Control-Allow-Headers: `*`
   - Access-Control-Allow-Methods: `GET,POST,PUT,DELETE,OPTIONS`
6. **Create**

### Step 7: Get API URL

1. **API Gateway** → Your API → **Stages**
2. Copy **Invoke URL**: `https://abc123.execute-api.us-east-1.amazonaws.com`

---

## 🔧 Post-Deployment Configuration

### Update Frontend Environment Variables

1. **Update your Vercel environment variables:**
   ```
   REACT_APP_API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/prod
   ```

2. **Redeploy frontend:**
   ```bash
   cd frontend
   vercel --prod
   ```

### Update CORS After Getting Vercel URL

1. **Get your Vercel deployment URL:**
   ```
   https://job-hunt-tracker.vercel.app
   ```

2. **Update Lambda environment variable:**
   ```
   ALLOWED_ORIGINS=https://job-hunt-tracker.vercel.app,http://localhost:3000
   ```

3. **If using SAM, redeploy:**
   ```bash
   sam deploy
   ```

### Update Google OAuth Authorized Origins

1. **Go to:** https://console.cloud.google.com/apis/credentials
2. **Edit your OAuth 2.0 Client ID**
3. **Authorized JavaScript origins:**
   - Add: `https://job-hunt-tracker.vercel.app`
4. **Authorized redirect URIs:**
   - Add: `https://job-hunt-tracker.vercel.app`
5. **Save**

---

## 📊 Monitoring and Debugging

### View Logs

**Via AWS Console:**
1. Lambda → Your function → **Monitor** → **View CloudWatch logs**

**Via CLI:**
```bash
sam logs -n JobHuntTrackerAPI --tail
```

### Test Endpoints

```bash
# Health check
curl https://your-api-url.execute-api.us-east-1.amazonaws.com/prod/health

# Auth endpoint (need valid Google token)
curl -X POST https://your-api-url/prod/auth/google \
  -H "Content-Type: application/json" \
  -d '{"token": "google_id_token_here"}'

# Protected endpoint (need JWT)
curl https://your-api-url/prod/api/user \
  -H "Authorization: Bearer your_jwt_token"
```

### Enable Detailed Logging

Edit `main.py` to add logging:

```python
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

@app.post("/auth/google")
async def google_auth(request: GoogleTokenRequest):
    logger.info(f"Google auth request received")
    # ... rest of code
```

---

## 💰 Cost Estimation

**Free Tier (First 12 months + Always Free):**
- Lambda: 1M requests/month + 400,000 GB-seconds compute (Always Free)
- API Gateway: 1M requests/month (First 12 months)

**After Free Tier:**
- Lambda: $0.20 per 1M requests
- API Gateway: $1.00 per 1M requests
- **Total for 1M requests/month: ~$1.20/month**

**For POC with ~1,000 requests/month: Essentially FREE**

---

## 🔄 Update Deployment

### Update Code

```bash
# Make your code changes
# Then:

sam build
sam deploy
```

### Update Environment Variables

**Via SAM:**
```bash
sam deploy --parameter-overrides \
  GoogleClientId="NEW_VALUE" \
  JWTSecretKey="NEW_SECRET"
```

**Via Console:**
1. Lambda → Configuration → Environment variables → Edit
2. Update values
3. Save (Lambda auto-restarts)

---

## 🗑️ Delete Stack

**To remove all AWS resources:**

```bash
sam delete
```

Or via AWS Console:
1. CloudFormation → Stacks
2. Select `job-hunt-tracker-api`
3. Delete

---

## 🐛 Common Issues

### "AccessDeniedException"

**Problem:** AWS credentials not configured or insufficient permissions

**Solution:**
```bash
aws configure
# Or attach AdministratorAccess policy to your IAM user
```

### "Runtime.ImportModuleError"

**Problem:** Missing dependencies or wrong handler

**Solution:**
- Ensure all dependencies in `requirements.txt`
- Verify handler is `main.handler`
- Check file structure in deployment package

### Cold Start Latency

**Problem:** First request takes 2-3 seconds

**Solution:**
- Expected behavior for Lambda
- Can add provisioned concurrency (costs money)
- Or use Lambda warming (scheduled pings)

### CORS Errors

**Problem:** Browser blocks requests

**Solution:**
- Update `ALLOWED_ORIGINS` in Lambda env vars
- Ensure API Gateway CORS is configured
- Check browser console for specific origin

---

## 📚 Next Steps

- [ ] Set up custom domain (Route 53 + API Gateway)
- [ ] Add CloudWatch alarms for errors
- [ ] Implement Lambda warming for production
- [ ] Set up CI/CD with GitHub Actions
- [ ] Add AWS X-Ray for tracing

---

## 📖 Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Lambda Python Documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [API Gateway HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [Mangum (FastAPI adapter)](https://mangum.io/)
