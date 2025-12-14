# Vercel Frontend Deployment Guide

Complete step-by-step guide to deploy the React frontend to Vercel.

---

## 📋 Prerequisites

- Vercel account (free - sign up at https://vercel.com)
- GitHub account (for auto-deployments)
- Node.js and npm installed locally

---

## 🎯 Deployment Methods

Choose one:

1. **Vercel CLI** (Fastest for testing)
2. **GitHub Integration** (Recommended for production - auto-deploys on push)
3. **Vercel Dashboard** (Manual upload)

---

## Method 1: Vercel CLI (Quick Start)

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Login to Vercel

```bash
vercel login
```

Follow the prompts to authenticate via email or GitHub.

### Step 3: Deploy

```bash
cd frontend
vercel
```

**You'll be prompted:**

```
? Set up and deploy "~/coding/jh/frontend"? [Y/n] y
? Which scope do you want to deploy to? <Your Name>
? Link to existing project? [y/N] n
? What's your project's name? job-hunt-tracker
? In which directory is your code located? ./
? Want to override the settings? [y/N] n
```

**Wait for deployment (1-2 minutes)...**

### Step 4: Get Your URL

```
✅  Preview: https://job-hunt-tracker-abc123.vercel.app
```

### Step 5: Set Environment Variables

```bash
# Add Google Client ID
vercel env add REACT_APP_GOOGLE_CLIENT_ID

# When prompted:
# ? What's the value of REACT_APP_GOOGLE_CLIENT_ID?
# Paste value from frontend/.env
# ? Add REACT_APP_GOOGLE_CLIENT_ID to which Environments?
# Select: Production, Preview, Development (use space to select, enter to confirm)

# Add API URL
vercel env add REACT_APP_API_URL

# When prompted:
# ? What's the value of REACT_APP_API_URL?
# Paste: https://your-lambda-api-url.execute-api.us-east-1.amazonaws.com/prod
# ? Add REACT_APP_API_URL to which Environments?
# Select: Production
```

### Step 6: Redeploy with Environment Variables

```bash
vercel --prod
```

Your production app is now live at: `https://job-hunt-tracker.vercel.app`

---

## Method 2: GitHub Integration (Recommended)

### Step 1: Push Code to GitHub

```bash
cd /Users/duan/coding/jh
git add .
git commit -m "Add backend and prepare for deployment"
git push origin main
```

### Step 2: Import Project to Vercel

1. **Go to:** https://vercel.com/dashboard
2. **Click:** "Add New..." → "Project"
3. **Import Git Repository:**
   - Click "Import" next to your `jh` repository
   - If not listed, click "Adjust GitHub App Permissions" and grant access

### Step 3: Configure Project

**Root Directory:**
```
frontend
```

**Framework Preset:**
```
Create React App
```

**Build Settings:**
- Build Command: `npm run build` (auto-detected)
- Output Directory: `build` (auto-detected)
- Install Command: `npm install` (auto-detected)

### Step 4: Add Environment Variables

**Before clicking "Deploy", add environment variables:**

Click **"Environment Variables"** dropdown:

| Name | Value | Environments |
|------|-------|--------------|
| `REACT_APP_GOOGLE_CLIENT_ID` | `<see frontend/.env>` | Production, Preview, Development |
| `REACT_APP_API_URL` | `https://your-api.execute-api.us-east-1.amazonaws.com/prod` | Production |
| `REACT_APP_API_URL` | `http://localhost:8000` | Development |

### Step 5: Deploy

1. Click **"Deploy"**
2. Wait for build (2-3 minutes)
3. Your app is live! 🎉

### Step 6: Configure Auto-Deployment

**Already configured!** Every time you push to GitHub:
- `main` branch → Production deployment
- Pull requests → Preview deployment (unique URL per PR)

```bash
# Future updates:
git add .
git commit -m "Update feature"
git push
# Automatically deploys to Vercel!
```

---

## Method 3: Manual Upload (Vercel Dashboard)

### Step 1: Build Locally

```bash
cd frontend
npm run build
```

This creates a `build/` folder with static files.

### Step 2: Upload to Vercel

1. **Go to:** https://vercel.com/dashboard
2. **Click:** "Add New..." → "Project"
3. **Select:** "Browse" under "Import from file system"
4. **Upload:** Select the `frontend/build` folder
5. **Configure environment variables** (same as Method 2)
6. **Deploy**

**Note:** This method doesn't support auto-deployments.

---

## 🔧 Post-Deployment Configuration

### Update Google OAuth Authorized Origins

1. **Go to:** https://console.cloud.google.com/apis/credentials
2. **Edit your OAuth 2.0 Client ID**
3. **Authorized JavaScript origins:**
   - Add: `https://job-hunt-tracker.vercel.app` (your actual Vercel URL)
   - Add: `https://job-hunt-tracker-git-main-yourname.vercel.app` (preview URLs)
4. **Authorized redirect URIs:**
   - Add: `https://job-hunt-tracker.vercel.app`
5. **Save**

### Update Backend CORS

**Update Lambda environment variable:**

```bash
# Via SAM
sam deploy --parameter-overrides \
  AllowedOrigins="https://job-hunt-tracker.vercel.app,http://localhost:3000"

# Or via AWS Console
# Lambda → Configuration → Environment Variables
# ALLOWED_ORIGINS=https://job-hunt-tracker.vercel.app,http://localhost:3000
```

---

## 🎨 Custom Domain (Optional)

### Step 1: Add Domain in Vercel

1. **Vercel Dashboard** → Your project → **Settings** → **Domains**
2. **Add:** `jobhunttracker.com` (or your domain)
3. **Follow instructions** to update DNS records

### Step 2: Update Google OAuth

Add your custom domain to authorized origins:
- `https://jobhunttracker.com`

### Step 3: Update Backend CORS

```
ALLOWED_ORIGINS=https://jobhunttracker.com,http://localhost:3000
```

---

## 📊 Monitoring and Analytics

### View Deployment Logs

1. **Vercel Dashboard** → Your project → **Deployments**
2. Click any deployment to see build logs

### Runtime Logs

1. **Vercel Dashboard** → Your project → **Functions**
2. View function invocation logs (if using Vercel Functions)

### Analytics (Optional)

1. **Vercel Dashboard** → Your project → **Analytics**
2. Enable Web Analytics (free tier available)
3. See page views, performance metrics, etc.

---

## 🔄 Environment-Specific Deployments

### Production

```bash
vercel --prod
```

Deploys to: `https://job-hunt-tracker.vercel.app`

### Preview (Testing)

```bash
vercel
```

Deploys to: `https://job-hunt-tracker-abc123.vercel.app`

### Local Development

```bash
npm start
```

Runs on: `http://localhost:3000`

---

## 💰 Cost

**Free Tier (Hobby Plan):**
- Unlimited deployments
- 100 GB bandwidth/month
- Automatic HTTPS
- Global CDN
- **Cost: $0/month**

**Pro Plan ($20/month):**
- Unlimited bandwidth
- Team collaboration
- Advanced analytics

**For POC: Free tier is perfect!**

---

## 🔐 Security Best Practices

### Environment Variables

- ✅ Set via Vercel dashboard (encrypted at rest)
- ✅ Different values per environment
- ❌ Never commit `.env` files to git

### HTTPS

- ✅ Automatic HTTPS on all deployments
- ✅ Free SSL certificates (auto-renewed)

### Preview Deployments

- Each PR gets a unique URL
- Test changes before merging to production
- Preview URLs are public (don't use production secrets)

---

## 🐛 Common Issues

### "Failed to compile" error

**Problem:** Missing dependencies or build errors

**Solution:**
```bash
# Test build locally first
cd frontend
npm install
npm run build

# Fix any errors shown
```

### Environment variables not working

**Problem:** Variables not set or wrong environment

**Solution:**
1. Check: Vercel Dashboard → Settings → Environment Variables
2. Ensure variables are set for correct environment (Production/Preview/Development)
3. Redeploy: `vercel --prod --force`

### "Invalid Client ID" error

**Problem:** Google OAuth not configured for Vercel URL

**Solution:**
1. Google Console → Credentials → Edit OAuth Client
2. Add Vercel URL to Authorized JavaScript origins
3. Save and wait 5 minutes for propagation

### CORS errors

**Problem:** Backend not allowing Vercel domain

**Solution:**
```bash
# Update backend ALLOWED_ORIGINS
ALLOWED_ORIGINS=https://your-vercel-url.vercel.app,http://localhost:3000

# Redeploy backend
sam deploy
```

### Changes not reflecting

**Problem:** Browser cache or old deployment

**Solution:**
```bash
# Force redeploy
vercel --prod --force

# Or clear browser cache
# Chrome: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

---

## 🚀 Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Project imported to Vercel
- [ ] Environment variables set (`REACT_APP_GOOGLE_CLIENT_ID`, `REACT_APP_API_URL`)
- [ ] Successful deployment
- [ ] Google OAuth authorized origins updated
- [ ] Backend CORS updated with Vercel URL
- [ ] Test login flow on production URL
- [ ] Check browser console for errors

---

## 🔄 Update Deployment

### Via Git (Recommended)

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main
# Auto-deploys to Vercel!
```

### Via CLI

```bash
cd frontend
vercel --prod
```

### Rollback

1. **Vercel Dashboard** → **Deployments**
2. Find previous successful deployment
3. Click **"Promote to Production"**

---

## 📚 Next Steps

- [ ] Set up custom domain
- [ ] Enable Vercel Analytics
- [ ] Configure deployment protection (password-protect preview URLs)
- [ ] Set up staging environment
- [ ] Add GitHub Actions for automated testing before deployment

---

## 📖 Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Vercel CLI Reference](https://vercel.com/docs/cli)
- [Environment Variables Guide](https://vercel.com/docs/concepts/projects/environment-variables)
- [Custom Domains](https://vercel.com/docs/concepts/projects/domains)
- [Deployment Protection](https://vercel.com/docs/security/deployment-protection)
