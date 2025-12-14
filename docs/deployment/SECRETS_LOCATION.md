# 🔐 Secrets Location Reference

**IMPORTANT:** This project follows security best practices by keeping secrets out of git.

---

## Where to Find Actual Secret Values

### Local Development

All actual secret values are stored in `.env` files, which are **gitignored** and never committed:

| Secret | Location | How to Get |
|--------|----------|------------|
| `GOOGLE_CLIENT_ID` | `frontend/.env` | Google Cloud Console → APIs & Services → Credentials |
| `SECRET_KEY` (backend) | `backend/.env` | Generate with: `openssl rand -hex 32` |
| `REACT_APP_API_URL` | `frontend/.env` | `http://localhost:8000` (local) or your deployed API URL |

### What IS Committed to Git

✅ **Safe to commit:**
- `backend/.env.example` - Template with placeholder values
- `frontend/.env.example` - Template with placeholder values
- `docs/deployment/*.md` - Guides with `<see .env>` placeholders
- `backend/config/settings.py` - No hardcoded secrets

❌ **Never committed:**
- `backend/.env` - Contains actual secrets
- `frontend/.env` - Contains actual secrets
- Any file with real API keys, tokens, or passwords

---

## Quick Setup for New Team Members

### 1. Clone the Repository
```bash
git clone <repo-url>
cd jh
```

### 2. Set Up Backend
```bash
cd backend
cp .env.example .env
# Edit .env and fill in:
# - GOOGLE_CLIENT_ID (get from team lead or Google Console)
# - SECRET_KEY (generate: openssl rand -hex 32)
```

### 3. Set Up Frontend
```bash
cd ../frontend
cp .env.example .env
# Edit .env and fill in:
# - REACT_APP_GOOGLE_CLIENT_ID (same as backend GOOGLE_CLIENT_ID)
# - REACT_APP_API_URL (http://localhost:8000 for local dev)
```

### 4. Verify Secrets are Gitignored
```bash
git status
# .env files should NOT appear in the list
```

---

## How Documentation References Secrets

Throughout the deployment guides, you'll see placeholders like:

```bash
# Example from docs:
GOOGLE_CLIENT_ID=<see frontend/.env>
SECRET_KEY=<see backend/.env>
```

This means:
1. Open the specified `.env` file
2. Copy the actual value from there
3. Use it in your deployment (AWS, Vercel, etc.)

---

## Sharing Secrets Securely

When sharing secrets with team members:

✅ **Good practices:**
- Use password managers (1Password, LastPass, Bitwarden)
- Encrypted messaging (Signal, encrypted Slack DMs)
- Secure note-sharing services (with expiration)

❌ **Bad practices:**
- Email
- Slack/Discord public channels
- Git commits
- Jira/Linear tickets
- Code comments

---

## Production Secrets

For production deployments, secrets are stored in:

| Platform | Secret Storage |
|----------|---------------|
| **AWS Lambda** | Lambda Environment Variables (encrypted at rest) |
| **Vercel** | Project Settings → Environment Variables |
| **AWS (alternative)** | AWS Secrets Manager |

See deployment guides for detailed instructions:
- [AWS Lambda Deployment](./AWS_LAMBDA_DEPLOYMENT.md)
- [Vercel Deployment](./VERCEL_DEPLOYMENT.md)
- [Environment Setup](./ENVIRONMENT_SETUP.md)

---

## Rotating Secrets

If a secret is compromised:

### Google Client ID
1. Google Console → Credentials → Create new OAuth client
2. Update in both `frontend/.env` and `backend/.env`
3. Update in AWS Lambda environment variables
4. Update in Vercel environment variables
5. Redeploy both frontend and backend
6. Delete old OAuth client

### JWT Secret Key
1. Generate new key: `openssl rand -hex 32`
2. Update `backend/.env`
3. Update AWS Lambda environment variables
4. Redeploy backend
5. Note: All existing user sessions will be invalidated

---

## Verification Checklist

Before committing code:

```bash
# 1. Check git status
git status
# Should NOT see: backend/.env or frontend/.env

# 2. Search for accidental secrets in staged files
git diff --cached | grep -i "secret\|client_id\|api_key"
# Should return no actual secret values

# 3. Verify .gitignore is working
git check-ignore backend/.env frontend/.env
# Should show both files are ignored
```

---

## Questions?

- **"Where do I get the Google Client ID?"**
  → Ask team lead or check Google Cloud Console if you have access

- **"How do I generate a SECRET_KEY?"**
  → Run: `openssl rand -hex 32`

- **"I accidentally committed a secret, what do I do?"**
  → 1. Rotate the secret immediately
  → 2. Use `git rebase` to remove from history
  → 3. Force push (if allowed)
  → 4. Consider the secret compromised

- **"Can I use the same SECRET_KEY for dev and prod?"**
  → ❌ No! Always use different secrets per environment
