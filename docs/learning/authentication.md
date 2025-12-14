# Authentication & Authorization

Complete guide to authentication concepts discussed during development.

---

## Table of Contents

1. [What is OAuth?](#what-is-oauth)
2. [How OAuth Works](#how-oauth-works)
3. [OAuth vs Password Login](#oauth-vs-password-login)
4. [Google OAuth Project Setup](#google-oauth-project-setup)
5. [Google OAuth Implementation](#google-oauth-implementation)
6. [JWT Explained](#jwt-explained)
7. [JWT vs Sessions](#jwt-vs-sessions)
8. [Token Storage](#token-storage)
9. [Token Security](#token-security)
10. [Auth0](#auth0)
11. [AWS Cognito](#aws-cognito)
12. [Auth Solutions Comparison](#auth-solutions-comparison)

---

## What is OAuth?

**OAuth = Open Authorization Protocol**

OAuth is a standard way to let users log into your app using their Google/GitHub/Facebook account - **without giving you their password**.

### The Problem OAuth Solves

**Without OAuth (OLD - BAD):**
```
Your App: "Enter your Google password"
User: Types password into YOUR app
Your App: Stores password, uses it
```

Problems:
- ❌ You handle passwords (security risk)
- ❌ User must trust you with Google password
- ❌ If hacked, their Google password is stolen
- ❌ Can't revoke without changing password

**With OAuth (MODERN - GOOD):**
```
Your App: "Login with Google" button
User: Clicks → redirected to Google.com
Google: "Allow this app? Yes/No"
User: Yes → Google gives YOUR app a token
Your App: Uses token (NOT password)
```

Benefits:
- ✅ You NEVER see user's password
- ✅ User trusts Google, not you
- ✅ Can revoke access anytime
- ✅ Limited permissions

### Simple Analogy

**Hotel Key Card System**

- **Without OAuth (password):** Hotel gives you master key
  - Access everything
  - If lost, must change all locks

- **With OAuth (token):** Hotel gives key card
  - Limited access (your room only)
  - Can deactivate card instantly
  - Expires automatically (checkout time)

---

## How OAuth Works

### Step-by-Step Flow

```
1. User clicks "Login with Google"
        ↓
2. Your app redirects to Google.com
        ↓
3. User logs in on Google (you never see this!)
        ↓
4. Google asks: "Allow Job Tracker to access your email?"
        ↓
5. User clicks "Allow"
        ↓
6. Google redirects back with TOKEN
        ↓
7. Your app receives token (NOT password!)
        ↓
8. Your app asks Google: "Who is this token for?"
        ↓
9. Google responds: "john@gmail.com"
        ↓
10. User is logged in!
```

### Real-World Example

**Medium.com's "Login with Google":**

1. Medium: "Hey Google, user wants to log in"
2. Google: Shows login page (Medium never sees it!)
3. You: Enter password on Google.com
4. Google: "Medium wants to read your email. OK?"
5. You: "Yes"
6. Google: Gives Medium a token: `eyJhbGc...`
7. Medium: "Who is token `eyJhbGc...`?"
8. Google: "That's john@gmail.com"
9. Medium: Logs you in as john@gmail.com

**Medium NEVER saw your password!**

---

## OAuth vs Password Login

| Aspect | Password Login | OAuth (Google) |
|--------|---------------|----------------|
| **User enters password in** | Your app ❌ | Google.com ✅ |
| **Who verifies password** | Your app | Google |
| **You store** | Hashed password | Nothing (or just email) |
| **Security risk** | High | Low |
| **User trust** | Must trust you | Trusts Google |
| **Revocation** | Change password | Click "revoke" in Google settings |
| **Two-factor auth** | You must implement | Google handles it |
| **Password reset** | You must handle | Google handles it |

---

## Google OAuth Project Setup

### Step-by-Step Guide to Creating Google OAuth Credentials

This section shows you how to create OAuth credentials in Google Cloud Console.

#### Step 1: Create a Google Cloud Project

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/

2. **Create a new project:**
   - Click the project dropdown at the top
   - Click "New Project"
   - **Project name:** `Job Hunt Tracker` (or any name)
   - Click "Create"

3. **Select your project:**
   - Click the project dropdown again
   - Select your newly created project

#### Step 2: Enable Google+ API

1. **Navigate to APIs & Services:**
   - In the left sidebar: **APIs & Services** → **Library**

2. **Search and enable:**
   - Search for "Google+ API" (or "Google Identity")
   - Click on it
   - Click "Enable"

   **Note:** This allows your app to access Google user profile information.

#### Step 3: Configure OAuth Consent Screen

1. **Go to OAuth consent screen:**
   - Left sidebar: **APIs & Services** → **OAuth consent screen**

2. **Choose user type:**
   - Select **External** (allows any Google account)
   - Click "Create"

3. **Fill in App information:**
   - **App name:** `Job Hunt Tracker`
   - **User support email:** Your email address
   - **Developer contact:** Your email address
   - Leave other fields blank for now
   - Click "Save and Continue"

4. **Scopes (Step 2):**
   - Click "Add or Remove Scopes"
   - Select these scopes:
     - `userinfo.email` - See your email address
     - `userinfo.profile` - See your basic profile info
     - `openid` - Associate you with your personal info
   - Click "Update"
   - Click "Save and Continue"

5. **Test users (Step 3):**
   - Click "Add Users"
   - Add your Google account email
   - Click "Add"
   - Click "Save and Continue"

   **Note:** In testing mode, only these emails can log in. Later, you can publish the app for public use.

6. **Summary (Step 4):**
   - Review your settings
   - Click "Back to Dashboard"

#### Step 4: Create OAuth Client ID

1. **Go to Credentials:**
   - Left sidebar: **APIs & Services** → **Credentials**

2. **Create credentials:**
   - Click "Create Credentials" button at the top
   - Select "OAuth client ID"

3. **Configure the OAuth client:**
   - **Application type:** Web application
   - **Name:** `Job Hunt Tracker Web Client`

4. **Add Authorized JavaScript origins:**

   Click "Add URI" under "Authorized JavaScript origins" and add:
   ```
   http://localhost:3000          # For local React development
   http://localhost:5173          # For Vite development (if using)
   https://your-app.vercel.app    # Add this after deploying to Vercel
   ```

5. **Add Authorized redirect URIs:**

   Click "Add URI" under "Authorized redirect URIs" and add:
   ```
   http://localhost:3000          # For local development
   https://your-app.vercel.app    # Add this after deploying to Vercel
   ```

   **Note:** You can edit these later when you deploy to production.

6. **Create:**
   - Click "Create"

#### Step 5: Save Your Credentials

After clicking Create, you'll see a popup with your credentials:

```
Your Client ID: 123456789-abcdefghijklmnop.apps.googleusercontent.com
Your Client Secret: GOCSPX-xxxxxxxxxxxxxxxxxxxx
```

**Important:**
- ✅ **Copy the Client ID** - You'll need this for both frontend and backend
- ⚠️ **Client Secret** - Not needed for our implementation (we use ID token validation)
- ✅ **Keep these safe** - Store in your `.env` files (never commit to git!)

#### Step 6: Add to Your Project

1. **Frontend `.env`:**
   ```bash
   cd frontend
   cp .env.example .env
   ```

   Edit `frontend/.env`:
   ```bash
   REACT_APP_GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
   REACT_APP_API_URL=http://localhost:8000
   ```

2. **Backend `.env`:**
   ```bash
   cd backend
   cp .env.example .env
   ```

   Edit `backend/.env`:
   ```bash
   # Use the SAME Client ID as frontend
   GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
   SECRET_KEY=<generate with: openssl rand -hex 32>
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ALLOWED_ORIGINS=http://localhost:3000
   ```

3. **Verify gitignore:**
   ```bash
   git status  # Should NOT show .env files
   ```

#### Step 7: Test Locally

1. **Start backend:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

2. **Start frontend:**
   ```bash
   cd frontend
   npm start
   ```

3. **Test login:**
   - Visit: http://localhost:3000
   - Click "Login with Google"
   - You should see the Google OAuth popup
   - Select your test user account
   - You should be redirected back and logged in!

#### Step 8: Update for Production (Later)

When you deploy to Vercel, you'll need to:

1. **Update Authorized JavaScript origins:**
   - Go back to Google Cloud Console → Credentials
   - Edit your OAuth client
   - Add: `https://your-actual-app.vercel.app`

2. **Update Authorized redirect URIs:**
   - Add: `https://your-actual-app.vercel.app`

3. **Save changes**

4. **Update backend CORS:**
   ```bash
   ALLOWED_ORIGINS=https://your-actual-app.vercel.app,http://localhost:3000
   ```

### Common Issues

**Issue 1: "redirect_uri_mismatch" error**

**Solution:**
- Check that the URL in the browser matches one of your Authorized redirect URIs
- Common mistake: `http://localhost:3000` vs `http://localhost:3000/` (trailing slash)
- Add both versions if needed

**Issue 2: "Access blocked: This app's request is invalid"**

**Solution:**
- Make sure you added your email to Test users in OAuth consent screen
- Verify the app is in "Testing" mode (or published)

**Issue 3: "Invalid authentication token" in backend**

**Solution:**
- Ensure `GOOGLE_CLIENT_ID` is the SAME in both frontend and backend `.env` files
- Copy the value from frontend to backend (don't type it manually)

**Issue 4: CORS errors**

**Solution:**
- Update `ALLOWED_ORIGINS` in backend to include your frontend URL
- For local dev: `http://localhost:3000`
- For production: `https://your-app.vercel.app`

### Security Notes

- ✅ **DO** use the same Client ID for frontend and backend
- ✅ **DO** keep credentials in `.env` files (gitignored)
- ✅ **DO** use HTTPS in production (Vercel provides this automatically)
- ❌ **DON'T** commit `.env` files to git
- ❌ **DON'T** share credentials in plaintext (use password managers)
- ❌ **DON'T** use the same credentials for development and production (create separate projects)

### Useful Google Console Links

- **Credentials:** https://console.cloud.google.com/apis/credentials
- **OAuth consent screen:** https://console.cloud.google.com/apis/credentials/consent
- **API Library:** https://console.cloud.google.com/apis/library
- **IAM & Admin:** https://console.cloud.google.com/iam-admin

---

## Google OAuth Implementation

### For Our Project

**Flow:**
```javascript
// 1. User clicks "Login with Google" (React)
<GoogleLogin onSuccess={handleSuccess} />

// 2. Google popup appears, user logs in
// 3. Google returns credential (ID token)
const handleSuccess = (response) => {
  const googleToken = response.credential;

  // 4. Send to our backend
  fetch('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ token: googleToken })
  });
};
```

```python
# 5. Backend validates token with Google
from google.oauth2 import id_token

@app.post("/auth/google")
def auth_google(token: str):
    # Verify with Google
    idinfo = id_token.verify_oauth2_token(
        token,
        requests.Request(),
        GOOGLE_CLIENT_ID
    )

    # idinfo contains:
    # - email: user@gmail.com
    # - name: John Doe
    # - picture: https://...

    # 6. Check email whitelist (access control)
    allowed_emails = settings.get_allowed_emails()
    if idinfo['email'].lower() not in allowed_emails:
        raise HTTPException(status_code=403, detail="Access denied")

    # 7. Create our own JWT (explained below)
    our_jwt = create_jwt(idinfo['email'])
    return {'access_token': our_jwt}
```

**Email Whitelist:**
- Set `ALLOWED_EMAILS` environment variable (comma-separated)
- Example: `ALLOWED_EMAILS=user1@gmail.com,user2@gmail.com`
- Only whitelisted emails can authenticate
- Hardcoded in `backend/config/settings.py` for quick iteration in Lambda console

### What's in a Google OAuth Token?

```json
{
  "iss": "accounts.google.com",
  "sub": "1234567890",
  "email": "john@gmail.com",
  "name": "John Doe",
  "picture": "https://lh3.googleusercontent.com/...",
  "iat": 1701234567,
  "exp": 1701238167
}
```

---

## JWT Explained

**JWT = JSON Web Token**

A JWT is a secure way to transmit information between parties as a JSON object.

### Structure

A JWT has 3 parts separated by dots:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

        HEADER                  .           PAYLOAD              .        SIGNATURE
```

**1. Header** (base64 encoded):
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**2. Payload** (base64 encoded):
```json
{
  "sub": "user@gmail.com",
  "name": "John Doe",
  "exp": 1702467890
}
```

**3. Signature** (prevents tampering):
```
HMACSHA256(
  base64(header) + "." + base64(payload),
  secret_key
)
```

### Why JWT?

✅ **Stateless** - No database lookup needed
✅ **Self-contained** - Has all info needed
✅ **Tamper-proof** - Signature prevents modification
✅ **Standard** - Works everywhere (APIs, mobile, web)

### How We Use JWT

```python
# Backend creates JWT after Google OAuth succeeds
import jwt
from datetime import datetime, timedelta

def create_jwt(email: str):
    payload = {
        'sub': email,              # Subject (user email)
        'exp': datetime.utcnow() + timedelta(days=1)  # Expires in 1 day
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token
```

```python
# Backend validates JWT on protected endpoints
@app.get("/api/user")
def get_user(authorization: str = Header(...)):
    token = authorization.replace('Bearer ', '')

    # Decode and verify signature
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

    # If signature invalid or expired, raises exception
    # Otherwise, payload contains user info
    return {"email": payload['sub']}
```

---

## JWT vs Sessions

Two ways to maintain authentication after login.

### JWT (What we're using)

```
User logs in
    ↓
Backend creates JWT (signed token)
    ↓
Frontend stores JWT (localStorage)
    ↓
Every request includes JWT in header
    ↓
Backend verifies signature (NO database lookup)
```

### Session-based

```
User logs in
    ↓
Backend creates session ID, stores in database
    ↓
Frontend stores session ID (cookie)
    ↓
Every request includes session ID
    ↓
Backend looks up session in database
```

### Comparison Table

| Aspect | JWT | Session |
|--------|-----|---------|
| **Backend stores** | Nothing (stateless) | Session data in DB/Redis |
| **Token contains** | User data | Random ID |
| **Validation** | Verify signature | Database lookup |
| **Speed** | ⚡ Fast (no DB lookup) | Slower (DB query) |
| **Scalability** | ✅ Easy (no shared state) | Needs shared session store |
| **Revocation** | ❌ Hard (wait for expiry) | ✅ Easy (delete session) |
| **Size** | Larger (~200 bytes) | Smaller (~32 bytes) |
| **Industry use** | Modern APIs, SPAs | Traditional web apps |

### When to Use Each

**Use JWT when:**
- Building REST API for React/mobile
- Need to scale horizontally
- Stateless architecture preferred
- Don't need immediate revocation

**Use Sessions when:**
- Building traditional web app
- Need to revoke immediately
- Want to track active sessions
- Server-side rendered pages

### Our Decision: JWT

**Why:**
1. ✅ Standard for React + API architecture
2. ✅ Stateless (easier deployment)
3. ✅ Fast (no DB lookups)
4. ✅ Scalable (multiple backend instances)

**Trade-off:**
- Can't revoke before expiration
- Solution: Use short expiration (1 day for POC, 15 min in production)

---

## Token Storage

Where to store JWT in the frontend?

### Options

| Storage | Security | Persists on Refresh | Best For |
|---------|----------|-------------------|----------|
| **localStorage** | ⚠️ Vulnerable to XSS | ✅ Yes | Simple POCs |
| **sessionStorage** | ⚠️ Vulnerable to XSS | ❌ No (lost on tab close) | Single sessions |
| **Memory (React state)** | ✅ More secure | ❌ No (lost on refresh) | High security apps |
| **httpOnly Cookie** | ✅ Most secure | ✅ Yes | Production apps |

### Our Choice: localStorage (for POC)

```javascript
// Store token
localStorage.setItem('access_token', jwt);

// Retrieve token
const token = localStorage.getItem('access_token');

// Include in requests
fetch('/api/user', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

// Clear on logout
localStorage.removeItem('access_token');
```

**Why localStorage for POC:**
- ✅ Simple to implement
- ✅ Survives page refresh
- ✅ Good enough for development

**Production upgrade: httpOnly Cookies**

More secure - JavaScript can't access the cookie (prevents XSS attacks).

---

## Token Security

### Main Security Concern: Token Interception

**Question:** "What if someone intercepts the JWT?"

**Answer:** HTTPS prevents interception.

### How HTTPS Protects Tokens

```
Without HTTPS (HTTP):
Frontend → [JWT travels in plain text - can be read!] → Backend
                     ❌ Attacker can steal JWT

With HTTPS:
Frontend → [Encrypted tunnel - gibberish if intercepted] → Backend
                     ✅ Attacker sees encrypted data
```

### If Token is Stolen (malware, phishing)

**JWT:**
- ❌ Valid until expiration
- Solution: Short expiration + refresh tokens

**Session:**
- ❌ Also valid until revoked
- ✅ Can revoke immediately

**Both require HTTPS to prevent theft!**

### Industry Best Practices

1. **HTTPS everywhere** (prevents interception)
2. **Short-lived access tokens** (15 min - 1 day)
3. **Refresh tokens** (get new access token)
4. **httpOnly cookies** (prevents XSS)
5. **Token rotation** (issue new tokens regularly)
6. **Device fingerprinting** (detect suspicious activity)

### Our POC Security

Phase 1:
- ✅ HTTPS (Vercel auto, EC2 with Let's Encrypt)
- ✅ JWT signed with strong secret
- ✅ 1-day expiration
- ⚠️ localStorage (acceptable for POC)

Phase 2+ Upgrades:
- 15-minute access tokens
- 7-day refresh tokens
- httpOnly cookies
- Token rotation

---

## Auth0

**Auth0 = Authentication-as-a-Service**

A third-party service that handles all authentication for you.

### What Auth0 Does

Handles:
- ✅ Social login (Google, GitHub, Facebook, etc.)
- ✅ Username/password auth
- ✅ Multi-factor authentication (MFA)
- ✅ Password reset flows
- ✅ Email verification
- ✅ Hosted login page
- ✅ User management dashboard
- ✅ Security (brute-force protection)

### How Auth0 Works

```
Your App → Auth0 (handles everything) → Returns token → Your App uses token
```

You don't write auth code - Auth0 provides it all.

### Auth0 vs Manual OAuth

| Aspect | Auth0 | Manual Google OAuth |
|--------|-------|-------------------|
| **Setup time** | 15-30 min | 30-45 min |
| **Code complexity** | ⭐ Very low | ⭐⭐ Medium |
| **Learning value** | ⭐ Low (black box) | ⭐⭐⭐ High |
| **Cost** | Free (7,500 users), then paid | Free forever |
| **Vendor lock-in** | ❌ Yes | ✅ No |
| **Features** | MFA, password reset, etc. | Just OAuth |

### Why We Didn't Use Auth0

1. Want to **learn** how OAuth works
2. Avoid vendor lock-in
3. Free forever (no user limits)
4. Better interview talking points

**Auth0 is great for:**
- Startups shipping fast
- Production apps needing enterprise auth
- When auth isn't your learning focus

---

## AWS Cognito

**AWS Cognito = AWS's authentication service**

Similar to Auth0, but AWS-native.

### Features

- User pools (manage users)
- Social login (Google, Facebook, etc.)
- MFA, password policies
- Lambda triggers for customization
- Integrates with API Gateway

### Cognito vs Auth0 vs Manual

| Feature | Cognito | Auth0 | Manual OAuth |
|---------|---------|-------|--------------|
| **Free tier** | 50K MAUs | 7.5K MAUs | Unlimited |
| **Setup** | Medium | Easy | Medium |
| **AWS integration** | ✅ Native | ❌ External | ❌ Manual |
| **Learning value** | ⭐⭐ Medium | ⭐ Low | ⭐⭐⭐ High |

### Why We Didn't Use Cognito

1. More complex setup than manual OAuth
2. AWS vendor lock-in
3. Want to learn OAuth internals

**Cognito is great for:**
- AWS-heavy applications
- Need built-in user management
- Want API Gateway integration

---

## Auth Solutions Comparison

### Quick Decision Matrix

**Choose Manual Google OAuth if:**
- ✅ Want to learn how OAuth works
- ✅ Building POC/learning project
- ✅ Avoid vendor lock-in
- ✅ Free forever with no limits

**Choose Auth0 if:**
- ✅ Need to ship fast
- ✅ Want MFA, password reset, etc.
- ✅ Don't care about learning auth internals
- ✅ Startup with <7,500 users

**Choose AWS Cognito if:**
- ✅ Heavy AWS ecosystem usage
- ✅ Need API Gateway integration
- ✅ Want AWS-native solution
- ✅ <50,000 users

**Choose Sessions (not OAuth) if:**
- ✅ Building traditional web app
- ✅ Need custom username/password
- ✅ Need immediate revocation
- ✅ Server-side rendered pages

### Our Final Choice

**Manual Google OAuth + JWT**

Because:
1. Learning value (understand OAuth deeply)
2. No vendor lock-in
3. Free forever
4. Great interview talking points
5. Production-ready (Google's OAuth is enterprise-grade)

---

## Key Takeaways

1. **OAuth** = Let users login with Google/GitHub without sharing passwords
2. **JWT** = Token format that's stateless, fast, and scalable
3. **HTTPS** = Critical for preventing token interception
4. **Storage** = localStorage for POC, httpOnly cookies for production
5. **Industry standard** = OAuth + JWT for modern APIs with React frontends

---

**Next:** See [security.md](./security.md) for detailed security best practices.
