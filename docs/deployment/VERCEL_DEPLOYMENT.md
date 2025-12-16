# Vercel Frontend Deployment Guide

Quick guide for deploying React frontend to Vercel.

---

## 🚀 Quick Update (Most Common)

**If you've already deployed once and just need to push updates:**

```bash
cd /Users/duan/coding/jh
git add .
git commit -m "Update routing logic"
git push origin main
```

That's it! Vercel auto-deploys in ~2 minutes. Check status at: https://vercel.com/dashboard

---

## 🆕 First-Time Setup

### Option 1: GitHub Integration (Recommended)

**1. Push to GitHub:**
```bash
cd /Users/duan/coding/jh
git add .
git commit -m "Initial commit"
git push origin main
```

**2. Import to Vercel:**
- Go to https://vercel.com/dashboard
- Click "Add New..." → "Project"
- Import your `jh` repository
- Set **Root Directory** to `frontend`
- Framework auto-detects as "Create React App"

**3. Add Environment Variables:**
```
REACT_APP_GOOGLE_CLIENT_ID = <from frontend/.env>
REACT_APP_API_URL = https://your-api.execute-api.us-east-1.amazonaws.com/prod
```

**4. Click Deploy**

**5. Update Google OAuth:**
- Go to https://console.cloud.google.com/apis/credentials
- Add Vercel URL to "Authorized JavaScript origins"
- Add Vercel URL to "Authorized redirect URIs"

**6. Update Backend CORS:**
```bash
# Add Vercel URL to Lambda environment variable
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

### Option 2: Vercel CLI (For Quick Testing)

```bash
# Install once
npm install -g vercel

# Deploy
cd frontend
vercel --prod
```

Follow prompts, then add environment variables via dashboard.

---

## 🔄 Common Tasks

### Push Updates
```bash
git add .
git commit -m "Your changes"
git push
# Auto-deploys!
```

### Force Redeploy
```bash
cd frontend
vercel --prod --force
```

### Rollback to Previous Version
1. Vercel Dashboard → Deployments
2. Find working deployment
3. Click "Promote to Production"

### Test Build Locally
```bash
cd frontend
npm run build
```

### View Logs
Vercel Dashboard → Your Project → Deployments → Click deployment → View logs

---

## 🐛 Troubleshooting

### Changes not showing
- Clear browser cache (Cmd+Shift+R / Ctrl+Shift+R)
- Check Vercel dashboard for build errors
- Force redeploy: `vercel --prod --force`

### "Invalid Client ID" error
- Update Google OAuth authorized origins with Vercel URL
- Wait 5 minutes for propagation

### CORS errors
- Add Vercel URL to backend `ALLOWED_ORIGINS`
- Redeploy backend with `sam deploy`

### Build fails
```bash
# Test locally first
cd frontend
npm install
npm run build
# Fix any errors shown
```

---

## 📝 Environment Variables Reference

| Variable | Production Value | Development Value |
|----------|-----------------|-------------------|
| `REACT_APP_GOOGLE_CLIENT_ID` | `<from Google Console>` | Same |
| `REACT_APP_API_URL` | `https://your-api.amazonaws.com/prod` | `http://localhost:8000` |

Set in: Vercel Dashboard → Settings → Environment Variables

---

## 💰 Cost

**Free tier:** Unlimited deployments, 100 GB bandwidth/month, automatic HTTPS. Perfect for this project.

---

## 📖 Full Documentation

For advanced topics (custom domains, analytics, deployment protection):
- [Vercel Docs](https://vercel.com/docs)
- [CLI Reference](https://vercel.com/docs/cli)
