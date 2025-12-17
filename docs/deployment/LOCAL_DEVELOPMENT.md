# Local Testing Guide

Quick reference for running and testing the application locally.

---

## 🚀 Quick Start

### Load Dev Shortcuts (Recommended)

**One-time per terminal session:**
```bash
# From project root
source dev.sh

# See all available commands
jh-help
```

This loads convenient shortcuts like `jh-start-be`, `jh-start-fe`, `jh-kill-all`, etc.

---

### Prerequisites

**One-time setup (if not done already):**
```bash
# 1. Ensure .env.local files exist (gitignored)
ls backend/.env.local   # Should exist
ls frontend/.env.local  # Should exist

# 2. Install backend dependencies
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install frontend dependencies
cd ../frontend
npm install
```

### Start Backend (Terminal 1)

**Option 1: Using shortcuts (recommended)**
```bash
source dev.sh        # Load shortcuts
jh-start-be          # Start backend
```

**Option 2: Manual**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Option 3: Background process (survives terminal close)**
```bash
source dev.sh
jh-start-be-bg       # Starts in background
tail -f backend/server.log  # View logs
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test it works:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{"status":"healthy","timestamp":"2025-12-14T09:47:50.586479Z"}
```

### Start Frontend (Terminal 2)

**Option 1: Using shortcuts (recommended)**
```bash
source dev.sh        # Load shortcuts
jh-start-fe          # Start frontend
```

**Option 2: Manual**
```bash
cd frontend
npm start
```

**Option 3: Background process (survives terminal close)**
```bash
source dev.sh
jh-start-fe-bg       # Starts in background
tail -f frontend/server.log  # View logs
```

**URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend API Docs: http://localhost:8000/docs

**Important:**
- Backend uses **test/dev database** from `.env.local` (safe for development)
- Production database is only used in AWS Lambda deployment
- Frontend connects to `http://localhost:8000` from `.env.local`

---

## 🧪 Running Tests

### Backend Authentication Tests

**Location:** `backend/test_auth.py`

**Run tests:**
```bash
cd backend
source venv/bin/activate
python test_auth.py
```

**What it tests:**
- ✅ Health check endpoint
- ✅ Invalid Google token rejection
- ✅ JWT creation and validation
- ✅ Protected endpoint access
- ✅ Expired token rejection
- ✅ API documentation availability

**Expected output:**
```
============================================================
  TEST SUMMARY
============================================================

Total Tests: 7
✅ Passed: 6
❌ Failed: 1

Success Rate: 85.7%
```

**Important:**
- ⚠️ **Backend must be running before tests**
- Tests connect to `http://localhost:8000`
- Tests do NOT start a temporary server
- Start backend first (see above), then run tests

---

## 🛑 Stopping Services

### Stop Backend
**Option 1: Using shortcuts (recommended)**
```bash
source dev.sh
jh-kill-be          # Kill backend
```

**Option 2: Manual**
- Press `Ctrl+C` in the terminal running uvicorn
- Or: `lsof -ti:8000 | xargs kill -9`

### Stop Frontend
**Option 1: Using shortcuts (recommended)**
```bash
source dev.sh
jh-kill-fe          # Kill frontend
```

**Option 2: Manual**
- Press `Ctrl+C` in the terminal running npm
- Or: `lsof -ti:3000 | xargs kill -9`

### Stop Everything
```bash
source dev.sh
jh-kill-all         # Kill both backend and frontend
```

---

## 🔧 Dev Shortcuts Reference

After running `source dev.sh`, you have access to:

**Navigation:**
- `jh-be` - Go to backend/ and activate venv
- `jh-fe` - Go to frontend/

**Start Services (foreground):**
- `jh-start-be` - Start backend server (port 8000)
- `jh-start-fe` - Start frontend server (port 3000)

**Start Services (background - survives terminal close):**
- `jh-start-be-bg` - Start backend in background
- `jh-start-fe-bg` - Start frontend in background

**Stop Services:**
- `jh-kill-be` - Kill backend process
- `jh-kill-fe` - Kill frontend process
- `jh-kill-all` - Kill both backend and frontend

**Utilities:**
- `jh-status` - Check what's running
- `jh-help` - Show all available commands

**Example workflow:**
```bash
# Terminal 1
source dev.sh
jh-start-be-bg      # Start backend in background
jh-start-fe-bg      # Start frontend in background
jh-status           # Verify both running

# When done
jh-kill-all         # Stop everything
```

---

## 🔧 Common Commands (Manual)

### Backend Commands (in `backend/` directory)

```bash
# Create/activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --port 8000

# Run tests (requires server running separately)
python test_auth.py

# Test health endpoint
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs  # macOS
```

### Frontend Commands (in `frontend/` directory)

```bash
# Install dependencies
npm install

# Start dev server
npm start

# Build for production
npm run build

# Stop dev server
# Press Ctrl+C in terminal
```

---

## 📋 Testing Checklist

**Before testing:**
- [ ] Backend `.env.local` file exists with correct values (test database URL)
- [ ] Frontend `.env.local` file exists with correct values (localhost:8000)
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Frontend dependencies installed (`npm install`)

**Start services:**
- [ ] Backend running at http://localhost:8000
- [ ] Frontend running at http://localhost:3000

**Verify:**
- [ ] Backend health check: `curl http://localhost:8000/health`
- [ ] Backend API docs accessible: http://localhost:8000/docs
- [ ] Frontend loads: http://localhost:3000
- [ ] Run backend tests: `python test_auth.py`

---

## 🐛 Troubleshooting

### Port already in use

**Backend (port 8000):**
```bash
lsof -ti:8000 | xargs kill -9
```

**Frontend (port 3000):**
```bash
lsof -ti:3000 | xargs kill -9
```

### Backend won't start

```bash
# Check .env.local file exists
ls backend/.env.local

# Check dependencies installed
source venv/bin/activate
pip list | grep fastapi

# Reinstall dependencies
pip install -r requirements.txt

# Verify DATABASE_URL points to test/dev branch
grep DATABASE_URL backend/.env.local
# Should see: ep-aged-darkness-ahpqrn39-pooler (test branch)
```

### Frontend won't start

```bash
# Check .env.local file exists
ls frontend/.env.local

# Verify API URL is localhost
grep REACT_APP_API_URL frontend/.env.local
# Should see: http://localhost:8000

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Test script fails

**Error:** `Connection refused`
- **Cause:** Backend not running
- **Solution:** Start backend first, then run tests

**Error:** `Module not found`
- **Cause:** Not in virtual environment or missing dependencies
- **Solution:** `source venv/bin/activate && pip install -r requirements.txt`

---

## 📝 Test Script Details

### Does the test script start the backend?

**No.** The test script (`test_auth.py`) does NOT start a backend server.

**Why:**
- Tests are designed to run against a live server
- Allows testing the actual server configuration
- Can test against local OR deployed backend (just change URL)

**To run tests:**
1. **Start backend manually** in one terminal
2. **Run tests** in another terminal
3. Tests connect to `http://localhost:8000`

**Example workflow:**
```bash
# Terminal 1: Start backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: Run tests
cd backend
source venv/bin/activate
python test_auth.py
```

---

## 🎯 Quick Test Commands

**Full end-to-end test:**
```bash
# Terminal 1
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm start

# Terminal 3
cd backend && source venv/bin/activate && python test_auth.py
```

**Quick backend verification:**
```bash
curl http://localhost:8000/health && echo " Backend OK!"
curl http://localhost:8000/docs | grep -q swagger && echo "API Docs OK!"
```

**Quick frontend verification:**
```bash
curl -s http://localhost:3000 | grep -q "root" && echo "Frontend OK!"
```
