# AWS & Deployment

Guide to AWS services and deployment strategies.

---

## Table of Contents

1. [AWS SAM: template.yaml vs samconfig.toml](#aws-sam-templateyaml-vs-samconfigtoml)
2. [EC2 vs Lambda](#ec2-vs-lambda)
3. [API Gateway](#api-gateway)
4. [Free Tier](#free-tier)
5. [FastAPI on EC2](#fastapi-on-ec2)
6. [React on Vercel](#react-on-vercel)
7. [HTTPS Setup](#https-setup)
8. [Scaling](#scaling)

---

## AWS SAM: template.yaml vs samconfig.toml

### Why API Gateway Gets Deployed with Lambda

When you run `sam deploy` to deploy a Lambda function, **API Gateway is also deployed automatically** because it's defined in your `template.yaml` file. This is Infrastructure as Code (IaC) - you define all your AWS resources in one template, and AWS creates them together.

**Think of it like this:**
- Lambda function = Your backend code (FastAPI)
- API Gateway = The front door that routes HTTP requests to your Lambda function
- They work together as a pair

### The Three Key Files

```
backend/
├── template.yaml      # WHAT to deploy (infrastructure blueprint)
├── samconfig.toml     # HOW to deploy (deployment configuration)
└── main.py           # YOUR CODE (FastAPI application)
```

### template.yaml - The Blueprint (WHAT)

**Purpose:** Defines **what AWS resources** to create and how they're connected.

**Analogy:** An architectural blueprint for a house
- "Build a kitchen (Lambda function)"
- "Build a front door (API Gateway)"
- "Connect the front door to the kitchen"

**Our template.yaml breakdown:**

```yaml
# 1. METADATA: Tell AWS this is a SAM template
Transform: AWS::Serverless-2016-10-31
Description: Job Hunt Tracker API - FastAPI on Lambda

# 2. PARAMETERS: Values that can change per deployment
Parameters:
  GoogleClientId:      # ← Input from samconfig.toml
    Type: String
  JWTSecretKey:        # ← Input from samconfig.toml
    Type: String

# 3. GLOBALS: Settings applied to all functions
Globals:
  Function:
    Runtime: python3.13          # Python version
    Timeout: 30                  # Max execution time
    Environment:
      Variables:
        GOOGLE_CLIENT_ID: !Ref GoogleClientId  # ← Use parameter value
        SECRET_KEY: !Ref JWTSecretKey

# 4. RESOURCES: The actual AWS services to create
Resources:
  JobHuntTrackerAPI:             # ← Lambda Function
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: JobHuntTrackerAPI
      Handler: main.handler      # Python function to call
      Events:                    # ← What triggers this Lambda?
        HttpApiEvent:
          Type: HttpApi          # ← HTTP request triggers it
          Properties:
            Path: /{proxy+}      # Any path (/, /health, /auth/google)
            Method: ANY          # Any HTTP method (GET, POST, etc.)
            ApiId: !Ref HttpApi  # ← Connect to API Gateway below

  HttpApi:                       # ← API Gateway
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: prod            # Stage name (/prod in URL)
      CorsConfiguration:         # CORS settings
        AllowOrigins:
          - "http://localhost:3000"
          - "https://your-app.vercel.app"

# 5. OUTPUTS: Values to display after deployment
Outputs:
  ApiUrl:
    Description: API Gateway endpoint URL
    Value: !Sub "https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com/prod"
```

**Key concept:** The `Events` section in the Lambda function definition automatically creates the API Gateway and connects them together. That's why API Gateway gets deployed when you deploy Lambda.

### samconfig.toml - Deployment Configuration (HOW)

**Purpose:** Defines **how to run** `sam deploy` (which AWS account, region, parameter values, etc.)

**Analogy:** Instructions for the construction crew
- "Build in New York (region)"
- "Use this contractor (AWS account)"
- "Here are the door codes (parameters)"

**Our samconfig.toml breakdown:**

```toml
version = 0.1

[default]                    # Profile name (can have multiple: dev, prod, etc.)
[default.deploy]
[default.deploy.parameters]

# Deployment settings
stack_name = "jh-backend-stack"        # CloudFormation stack name
resolve_s3 = true                      # Auto-create S3 bucket for code upload
region = "us-east-1"                   # AWS region
capabilities = "CAPABILITY_IAM"        # Permission to create IAM roles

# Parameter values (fed into template.yaml Parameters)
parameter_overrides = "GoogleClientId=\"your-client-id.apps.googleusercontent.com\" JWTSecretKey=\"your-secret-key\" AllowedOrigins=\"http://localhost:3000,https://your-app.vercel.app\" AllowedEmails=\"your-email@gmail.com\""

confirm_changeset = false              # Skip manual confirmation prompt
```

**Key concept:** The values in `parameter_overrides` are passed to `template.yaml` Parameters, which then become Lambda environment variables.

### How They Work Together

**When you run `sam deploy`:**

```
Step 1: Read samconfig.toml
  ↓ "Deploy to us-east-1, stack name jh-backend-stack"
  ↓ "Use these parameter values: GoogleClientId=..., JWTSecretKey=..."

Step 2: Read template.yaml
  ↓ "Create Lambda function named JobHuntTrackerAPI"
  ↓ "Create API Gateway named HttpApi"
  ↓ "Connect API Gateway to Lambda via Events"
  ↓ "Set environment variables from Parameters"

Step 3: Build deployment package
  ↓ sam build
  ↓ Package Python code + dependencies into .zip

Step 4: Upload to S3
  ↓ Upload .zip file to S3 bucket (auto-created by resolve_s3)

Step 5: Create CloudFormation stack
  ↓ CloudFormation reads template.yaml
  ↓ Creates all Resources: Lambda + API Gateway + IAM roles
  ↓ Connects them together
  ↓ Sets environment variables

Step 6: Output results
  ↓ Displays Outputs section from template.yaml
  ↓ ApiUrl: https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
```

### Visual Relationship

```
┌─────────────────────────────────────────────────────────────┐
│ template.yaml (Infrastructure Blueprint)                    │
│                                                              │
│  ┌─────────────────┐         ┌──────────────────┐          │
│  │ Lambda Function │◄────────│ API Gateway      │          │
│  │                 │         │ (HttpApi)        │          │
│  │ - Name: JobHunt │         │ - Stage: prod    │          │
│  │ - Runtime: py313│         │ - CORS: enabled  │          │
│  │ - Handler: main │         │ - Path: /{proxy+}│          │
│  │ - Env vars: ... │         │                  │          │
│  └─────────────────┘         └──────────────────┘          │
│         ▲                             ▲                     │
│         │                             │                     │
│         └─────────Events connection───┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ Uses values from
                           │
┌─────────────────────────────────────────────────────────────┐
│ samconfig.toml (Deployment Settings)                        │
│                                                              │
│  - Region: us-east-1                                        │
│  - Stack name: jh-backend-stack                             │
│  - Parameters: GoogleClientId="...", JWTSecretKey="..."     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Why Both Files?

**Separation of concerns:**

| File | Purpose | Changes | Who uses it |
|------|---------|---------|-------------|
| **template.yaml** | Infrastructure structure | Rarely (only when adding new resources) | Developers defining architecture |
| **samconfig.toml** | Deployment configuration | Often (different values per environment) | DevOps configuring deployments |

**Example scenario:**

You want to deploy the same application to `dev` and `prod` environments:

**template.yaml** (same for both):
```yaml
Resources:
  JobHuntTrackerAPI:
    Type: AWS::Serverless::Function
    # ... same infrastructure definition
```

**samconfig.toml** (different for each):
```toml
# Dev environment
[dev.deploy.parameters]
stack_name = "jh-backend-dev"
parameter_overrides = "AllowedOrigins=\"http://localhost:3000\""

# Prod environment
[prod.deploy.parameters]
stack_name = "jh-backend-prod"
parameter_overrides = "AllowedOrigins=\"https://your-app.vercel.app\""
```

Deploy to dev: `sam deploy --config-env dev`
Deploy to prod: `sam deploy --config-env prod`

### Common Questions

**Q: Can I deploy Lambda without API Gateway?**

Yes! Just remove the `Events` section from the Lambda function in `template.yaml`. Then Lambda can be triggered by other events (S3 uploads, CloudWatch schedules, etc.) instead of HTTP requests.

**Q: Do I need samconfig.toml?**

No, but it's convenient. Without it, you'd need to pass all parameters via command line:
```bash
sam deploy --stack-name jh-backend-stack --region us-east-1 --parameter-overrides GoogleClientId="..." JWTSecretKey="..."
```

**Q: What's CloudFormation?**

CloudFormation is AWS's Infrastructure as Code service. SAM is a simplified version of CloudFormation specifically for serverless applications. When you run `sam deploy`, it converts your `template.yaml` into a full CloudFormation template and deploys it.

**Q: Where are the actual resources created?**

All resources are tracked in a **CloudFormation stack**:
1. Go to https://console.aws.amazon.com/cloudformation
2. Find your stack (e.g., `jh-backend-stack`)
3. Click "Resources" tab to see everything created (Lambda, API Gateway, IAM roles, etc.)

### Quick Reference: File Comparison

```yaml
# template.yaml - WHAT infrastructure to build
Resources:
  MyLambda:                    # ← Define Lambda
    Type: AWS::Serverless::Function
    Events:
      MyApi:                   # ← This creates API Gateway automatically!
        Type: HttpApi
```

```toml
# samconfig.toml - HOW to deploy it
stack_name = "my-stack"        # ← Deployment name
region = "us-east-1"           # ← Where to deploy
parameter_overrides = "..."    # ← Configuration values
```

### Summary

**Why API Gateway gets deployed with Lambda:**
- Because `template.yaml` defines both resources and connects them via the `Events` section
- SAM automatically creates API Gateway when you specify `Type: HttpApi` in Events
- This is intentional - Lambda functions need a trigger, and HTTP API is a common trigger

**Relationship:**
```
template.yaml (blueprint) + samconfig.toml (config) → sam deploy → CloudFormation → Lambda + API Gateway
```

---

## EC2 vs Lambda

### EC2 (Elastic Compute Cloud)

**= Virtual Server (like your own computer in the cloud)**

- Rent a virtual machine
- Runs 24/7 (unless you stop it)
- You manage everything: OS, dependencies, scaling

**Analogy:** Renting an apartment
- You get the whole space
- Pay monthly
- Decorate/manage yourself

### Lambda

**= Serverless Function (code that runs on-demand)**

- No server to manage
- Runs only when triggered
- AWS manages everything

**Analogy:** Hotel room
- Only pay when you use it
- Hotel manages maintenance

### Detailed Comparison

| Feature | EC2 | Lambda |
|---------|-----|--------|
| **Pricing** | Pay for uptime ($/hour) even if idle | Pay per request + execution time |
| **Free Tier** | 750 hrs/month for 12 months | 1M requests/month **forever** |
| **Runs** | 24/7 (always on) | On-demand (triggered) |
| **Scaling** | Manual (or auto-scaling groups) | Automatic (1 to 1000s of requests) |
| **Management** | You manage OS, updates, patches | AWS manages everything |
| **Startup Time** | Instant (always running) | Cold start: 100ms-2s |
| **Max Runtime** | Unlimited | 15 minutes per invocation |
| **Use Case** | Traditional servers, long-running apps | Event-driven, API endpoints |

### Code Example

**EC2:**
```bash
# You SSH into EC2
ssh ec2-user@your-ec2-ip

# Install Python
sudo apt install python3

# Run FastAPI (stays running 24/7)
uvicorn main:app --host 0.0.0.0 --port 80

# Server runs continuously, waiting for requests
```

**Lambda:**
```python
# Your code (main.py)
def lambda_handler(event, context):
    # Runs only when API Gateway calls it
    return {
        'statusCode': 200,
        'body': 'Hello World'
    }

# Deploy: Upload to Lambda (no server management)
# Execution: Request comes in → Lambda starts → Runs code → Stops
# No request? Lambda does nothing (costs $0)
```

### Performance Comparison

**Benchmarks (requests/second):**
- EC2 (t2.micro): ~500-1,000 req/s
- Lambda: ~10,000-25,000 req/s (auto-scales)

### Cost Comparison

**Scenario:** Your job tracker gets 1,000 requests/day

**EC2 (t2.micro):**
- Runs 24/7: 720 hours/month
- Free tier: 750 hours/month → **FREE for 12 months**
- After 12 months: ~$8-10/month (even if no traffic!)

**Lambda:**
- 1,000 req/day × 30 days = 30,000 requests/month
- Free tier: 1M requests/month → **FREE FOREVER**
- After 1M: ~$0.20 per additional 1M requests

### When to Use Each

**Use EC2 when:**
- ✅ Long-running applications (WebSocket servers, background workers)
- ✅ Traditional frameworks that expect a server
- ✅ Need full OS control
- ✅ Consistent high traffic
- ✅ Need more than 15 min execution time

**Examples:** Database server, game server, scraper workers

**Use Lambda when:**
- ✅ Event-driven / on-demand workload
- ✅ API endpoints (REST APIs)
- ✅ Scheduled tasks (cron jobs)
- ✅ Low/unpredictable traffic
- ✅ Want zero server management

**Examples:** API endpoints, image processing, scheduled tasks

### Our Decision: EC2 for Phase 1

**Why:**
1. ✅ Simpler mental model (just a server)
2. ✅ Easier to debug (SSH in, check logs)
3. ✅ No cold starts
4. ✅ Can run long scraping jobs (>15 min)
5. ✅ Still free for 12 months

**Future:** Migrate APIs to Lambda in Phase 2, keep EC2 for scraper workers

---

## API Gateway

### What is API Gateway?

**AWS API Gateway = Managed service that creates HTTP endpoints for your Lambda functions**

```
User Request → API Gateway → Lambda Function
```

### Do You NEED API Gateway?

**It depends on your deployment:**

| Deployment | Need API Gateway? | Why |
|------------|-------------------|-----|
| **EC2** | ❌ No | EC2 has public IP, expose ports directly |
| **Lambda** | ✅ Yes | Lambda needs API Gateway to expose HTTP endpoints |
| **Elastic Beanstalk** | ❌ No | Has built-in load balancer |

### What API Gateway Provides

**1. Routing**
```
API Gateway routes:
  /auth/*     → Auth Lambda
  /jobs/*     → Jobs Lambda
  /scraper/*  → Scraper Lambda
```

**2. Authentication/Authorization**
- Validate JWT/Cognito tokens **before** hitting Lambda
- Your Lambda only runs if authenticated

**3. Rate Limiting**
- Built-in throttling (e.g., 100 req/sec per user)
- Prevents abuse

**4. Request/Response Transformation**
- Modify headers, format responses
- CORS handling

**5. Caching**
- Cache responses at API Gateway level
- Reduces Lambda invocations

**6. Lambda Integration**
- Lambda doesn't have a public URL by default
- API Gateway gives it an HTTPS endpoint

### Architecture Comparison

**Without API Gateway (EC2):**
```
Frontend → EC2 (public IP) → FastAPI handles everything
```

**With API Gateway (Lambda):**
```
Frontend → API Gateway → Lambda (FastAPI via Mangum)
```

### Our Decision: No API Gateway (Phase 1)

Using EC2, so API Gateway not needed.

**Future:** If we migrate to Lambda, we'll add API Gateway.

---

## Free Tier

### AWS Free Tier Options

#### EC2 (t2.micro/t3.micro)
- ✅ 750 hours/month free
- ✅ Duration: 12 months
- ✅ Full control
- ❌ Runs 24/7 → costs money after free tier

#### Lambda + API Gateway
- ✅ 1M requests/month free (permanent!)
- ✅ API Gateway: 1M requests/month free
- ✅ No server management
- ✅ Only pay when used
- ❌ 15-min timeout

#### RDS (PostgreSQL)
- ✅ 750 hours/month (t3.micro)
- ✅ Duration: 12 months
- ✅ 20GB storage
- ❌ ~$15/month after free tier

#### ElastiCache (Redis)
- ✅ 750 hours/month (t3.micro)
- ✅ Duration: 12 months
- ❌ ~$15/month after

#### S3
- ✅ 5GB storage
- ✅ 20,000 GET requests/month
- ✅ **Permanent** free tier

#### CloudFront (CDN)
- ✅ 1TB data transfer/month
- ✅ Duration: 12 months

### Cost After Free Tier

**Monthly costs for job tracker:**
- EC2 t2.micro: $8-10
- RDS PostgreSQL: $15
- ElastiCache Redis: $15
- Total: ~$40/month

**Cost Optimization:**
- Use Lambda instead of EC2: Free forever
- Self-host PostgreSQL on EC2: Save $15
- Use Redis on EC2: Save $15
- Total: ~$10/month (just EC2)

---

## FastAPI on EC2

### Deployment Steps

**1. Launch EC2 Instance**
```bash
# AWS Console:
- Choose Ubuntu 22.04 LTS
- Instance type: t2.micro (free tier)
- Create key pair (for SSH)
- Security group: Allow ports 22, 80, 443
- Launch instance
```

**2. SSH into Instance**
```bash
# Download .pem key file
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

**3. Install Dependencies**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install pip
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
```

**4. Upload Code**
```bash
# Option A: Git clone
git clone https://github.com/yourusername/job-tracker.git
cd job-tracker/backend

# Option B: SCP upload
scp -i your-key.pem -r ./backend ubuntu@your-ec2-ip:~/
```

**5. Install Python Dependencies**
```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**6. Set Environment Variables**
```bash
# Create .env file
nano .env

# Add:
GOOGLE_CLIENT_ID=...
SECRET_KEY=...
ALLOWED_ORIGINS=https://yourapp.vercel.app
```

**7. Run FastAPI**
```bash
# Simple way (development)
uvicorn main:app --host 0.0.0.0 --port 80

# Production way (with gunicorn + uvicorn workers)
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:80
```

**8. Keep Running (Background Process)**
```bash
# Option A: nohup
nohup uvicorn main:app --host 0.0.0.0 --port 80 &

# Option B: systemd service (better)
sudo nano /etc/systemd/system/fastapi.service

# Add:
[Unit]
Description=FastAPI
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/backend
ExecStart=/home/ubuntu/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 80
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable fastapi
sudo systemctl start fastapi
```

**9. Configure Security Group**
```bash
# AWS Console → EC2 → Security Groups
# Inbound rules:
- Port 22 (SSH): Your IP only
- Port 80 (HTTP): 0.0.0.0/0
- Port 443 (HTTPS): 0.0.0.0/0
```

**10. Test**
```bash
curl http://your-ec2-public-ip/health
# Should return: {"status": "healthy"}
```

---

## React on Vercel

### Deployment Steps

**1. Push Code to GitHub**
```bash
cd frontend
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/job-tracker-frontend.git
git push -u origin main
```

**2. Sign Up for Vercel**
- Go to https://vercel.com
- Sign in with GitHub

**3. Import Project**
- Click "New Project"
- Import your GitHub repository
- Framework: Detect automatically (React)
- Click "Deploy"

**4. Set Environment Variables**
```
# Vercel Dashboard → Settings → Environment Variables
REACT_APP_GOOGLE_CLIENT_ID=...
REACT_APP_API_URL=http://your-ec2-public-ip
```

**5. Redeploy**
- Any push to main branch auto-deploys
- Or click "Redeploy" in Vercel dashboard

**6. Get Production URL**
- Vercel gives you: `yourapp.vercel.app`
- Can add custom domain later

**7. Update Backend CORS**
```python
# backend/.env
ALLOWED_ORIGINS=https://yourapp.vercel.app,http://localhost:3000
```

---

## HTTPS Setup

### Why HTTPS is Critical

**Without HTTPS:**
```
Frontend → [JWT travels in plain text] → Backend
           ❌ Attacker can steal JWT
```

**With HTTPS:**
```
Frontend → [Encrypted tunnel] → Backend
           ✅ Attacker sees gibberish
```

### Vercel (Frontend)

✅ **Auto HTTPS** - Vercel provides SSL certificates automatically

No action needed!

### EC2 (Backend)

**Option A: Let's Encrypt (Free SSL)**

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate (requires domain name)
sudo certbot --nginx -d api.yourdomain.com

# Certbot auto-renews every 90 days
```

**Option B: AWS Certificate Manager (ACM)**

1. Create certificate in ACM
2. Create Application Load Balancer
3. Attach certificate to ALB
4. Point ALB to EC2 instance

**For POC:** Can start with HTTP, add HTTPS before production

---

## Scaling

### Vertical Scaling (Bigger Server)

```
t2.micro → t2.small → t2.medium → t2.large
```

**Pros:** Simple
**Cons:** Limited, expensive

### Horizontal Scaling (More Servers)

```
1 EC2 instance → 3 EC2 instances behind load balancer
```

**Pros:** Unlimited scaling
**Cons:** More complex

**Implementation:**
1. Create Auto Scaling Group
2. Add Application Load Balancer
3. Configure health checks
4. AWS auto-scales based on CPU/traffic

### Serverless Scaling (Lambda)

Lambda auto-scales from 1 to 1000s of concurrent executions.

**No configuration needed!**

### Our Scaling Path

**Phase 1:** Single EC2 (good for POC)
**Phase 2:** Add database (RDS)
**Phase 3:** Horizontal scaling (multiple EC2 + ALB)
**Phase 4:** Hybrid (Lambda for APIs, EC2 for scrapers)

---

## How to Find Your AWS Resources from Web Console

When you deploy to AWS, you'll need to find your resources (API Gateway URLs, Lambda functions, etc.) from the AWS Console. Here's how:

### Finding API Gateway URL

**Method 1: CloudFormation Stack Outputs (Easiest)**

1. Go to https://console.aws.amazon.com/cloudformation
2. Click on your stack (e.g., `jh-backend-stack`)
3. Click the **"Outputs"** tab
4. Look for the `ApiUrl` key
5. The **Value** column shows your full API URL

Example:
```
Key: ApiUrl
Description: API Gateway endpoint URL
Value: https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
```

**Method 2: API Gateway Console**

1. Go to https://console.aws.amazon.com/apigateway
2. Click **"APIs"** in the left sidebar
3. Find your API (e.g., `jh-backend-stack`)
4. Click on it
5. The **API endpoint** is shown at the top: `https://abc123xyz.execute-api.us-east-1.amazonaws.com`
6. Click **"Stages"** in the left sidebar to see stage names (e.g., `prod`)
7. **Full URL** = `{API endpoint}/{stage}` = `https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod`

**Method 3: Lambda Console**

1. Go to https://console.aws.amazon.com/lambda
2. Click on your function (e.g., `JobHuntTrackerAPI`)
3. Go to **"Configuration"** tab → **"Triggers"**
4. You'll see the API Gateway trigger with the endpoint URL

### Finding Lambda Function Details

**Lambda Console:**

1. Go to https://console.aws.amazon.com/lambda
2. Click **"Functions"** in the left sidebar
3. Click on your function name (e.g., `JobHuntTrackerAPI`)
4. You can see:
   - Function ARN
   - Runtime (e.g., Python 3.13)
   - Memory/Timeout settings
   - Environment variables
   - Recent invocations

**Viewing Logs (CloudWatch):**

1. In the Lambda function page, click **"Monitor"** tab
2. Click **"View CloudWatch logs"**
3. Or go directly to https://console.aws.amazon.com/cloudwatch
4. Click **"Log groups"** in the left sidebar
5. Find `/aws/lambda/JobHuntTrackerAPI`
6. Click on the latest log stream to see execution logs

### Finding S3 Buckets

**S3 Console:**

1. Go to https://console.aws.amazon.com/s3
2. Search for your bucket (e.g., `aws-sam-cli-managed-default-samclisourcebucket`)
3. Click on it to browse uploaded artifacts

### Finding EC2 Instances

**EC2 Console:**

1. Go to https://console.aws.amazon.com/ec2
2. Click **"Instances"** in the left sidebar
3. Find your instance by name or ID
4. The **Public IPv4 address** is your server's URL
5. Click on the instance to see:
   - Public/Private IP addresses
   - Instance type (e.g., t2.micro)
   - Security groups
   - Key pair name

### Quick Reference: Console URLs

| Service | Direct Link |
|---------|-------------|
| CloudFormation | https://console.aws.amazon.com/cloudformation |
| API Gateway | https://console.aws.amazon.com/apigateway |
| Lambda | https://console.aws.amazon.com/lambda |
| CloudWatch Logs | https://console.aws.amazon.com/cloudwatch |
| EC2 | https://console.aws.amazon.com/ec2 |
| S3 | https://console.aws.amazon.com/s3 |
| IAM | https://console.aws.amazon.com/iam |
| RDS | https://console.aws.amazon.com/rds |

### Pro Tip: Using AWS CLI

If you prefer command line, you can get the same info:

```bash
# Get CloudFormation stack outputs
aws cloudformation describe-stacks \
  --stack-name jh-backend-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text

# Output: https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod

# List API Gateway APIs
aws apigatewayv2 get-apis \
  --query 'Items[?Name==`jh-backend-stack`].[ApiEndpoint,Name]' \
  --output table

# List Lambda functions
aws lambda list-functions \
  --query 'Functions[?FunctionName==`JobHuntTrackerAPI`].[FunctionName,Runtime,Handler]' \
  --output table
```

### Understanding the URL Structure

**API Gateway URL Format:**
```
https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/{path}
         ↓                        ↓              ↓       ↓
    abc123xyz              us-east-1         prod   /health
```

**Breakdown:**
- `api-id`: Unique identifier for your API (auto-generated)
- `region`: AWS region where API is deployed
- `stage`: Deployment stage (prod, dev, staging)
- `path`: Your API endpoint path (/health, /api/user, etc.)

**Example Full Endpoint:**
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/health
```

This would map to your FastAPI route: `@app.get("/health")`

### Common Issues

**Issue: Can't find my API**
- Check you're in the correct AWS region (top-right dropdown)
- Search by stack name in CloudFormation first

**Issue: API Gateway URL returns 403/404**
- Verify the stage name is correct (usually `prod`)
- Check if Lambda has proper permissions (should be auto-configured by SAM)
- View CloudWatch logs for Lambda execution errors

**Issue: Different URL each time I deploy**
- API Gateway URL stays the same for updates to existing stacks
- Only changes if you delete and recreate the stack
- Use CloudFormation stack outputs to get the stable URL

---

## Environment Variables in AWS Lambda

### How .env Files Work (Local vs AWS)

**Important:** The `.env` file is **only used for local development** and is **NOT uploaded to AWS Lambda**.

### Local Development (Your Computer)

When you run `uvicorn main:app` locally, Pydantic reads from the `.env` file:

```python
# backend/config/settings.py
class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    SECRET_KEY: str
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    class Config:
        env_file = ".env"  # ← Only works locally
        case_sensitive = True

settings = Settings()
```

**Flow:**
1. You run: `uvicorn main:app`
2. Pydantic sees `env_file = ".env"` in Config
3. Reads values from `backend/.env` file
4. Creates Settings object with those values

### AWS Lambda (Production)

When deployed to Lambda, there is **NO .env file**. Instead, AWS provides environment variables directly to the Lambda runtime.

**Flow:**
```
samconfig.toml → template.yaml → Lambda Environment Variables → Pydantic
```

**Step 1: samconfig.toml** defines parameter values:
```toml
parameter_overrides = "GoogleClientId=\"...\" JWTSecretKey=\"...\" AllowedOrigins=\"...\""
```

**Step 2: template.yaml** receives as CloudFormation parameters:
```yaml
Parameters:
  GoogleClientId:
    Type: String
  JWTSecretKey:
    Type: String
  AllowedOrigins:
    Type: String

Globals:
  Function:
    Environment:
      Variables:
        GOOGLE_CLIENT_ID: !Ref GoogleClientId  # ← Set as Lambda env var
        SECRET_KEY: !Ref JWTSecretKey
        ALLOWED_ORIGINS: !Ref AllowedOrigins
```

**Step 3: Lambda receives environment variables**
- Go to Lambda Console → JobHuntTrackerAPI → Configuration → Environment variables
- You'll see: `GOOGLE_CLIENT_ID`, `SECRET_KEY`, `ALLOWED_ORIGINS`, etc.

**Step 4: Pydantic reads from environment variables**
- When `.env` file doesn't exist (like in Lambda), Pydantic automatically reads from system environment variables
- No code changes needed - it "just works"

### Viewing Environment Variables in Lambda Console

1. Go to https://console.aws.amazon.com/lambda
2. Click **JobHuntTrackerAPI** function
3. Click **Configuration** tab
4. Click **Environment variables** in left menu
5. You'll see all your variables listed

### Hardcoded vs Environment Variable

**Environment Variable (recommended for production):**
```python
# Will read from Lambda environment variable
ALLOWED_EMAILS: str
```

**Hardcoded (quick iteration):**
```python
# Ignores environment variable, uses hardcoded value
ALLOWED_EMAILS: str = "zduanx@gmail.com"
```

**Trade-off:**
- **Environment variable**: Change via Lambda console → Configuration → Environment variables (no code edit)
- **Hardcoded**: Edit code directly in Lambda console → Code tab (requires clicking "Deploy")

### How SAM Deploy Sets Environment Variables

When you run `sam deploy`:

```bash
sam build   # Builds deployment package (code + dependencies)
sam deploy  # Uploads to S3, creates CloudFormation stack
```

CloudFormation creates the Lambda function with environment variables from `template.yaml`. The `.env` file is **excluded** from the deployment package (SAM ignores it by default).

**What gets uploaded:**
```
✅ Python code (*.py)
✅ Dependencies (from requirements.txt)
❌ .env file (excluded)
❌ __pycache__
❌ .git
```

### Key Takeaway

**`.env` file = Local development only**

**AWS Lambda = Environment variables set via CloudFormation (template.yaml + samconfig.toml)**

No "virtual .env file" is created - Pydantic simply reads from the Lambda runtime's environment variables, which AWS provides automatically.

---

**Next:** See [backend.md](./backend.md) for FastAPI and system architecture concepts.
