# Local Testing Guide

Quick reference for running and testing the application locally.

---

## 🚀 Quick Start

### Start Backend (Terminal 1)

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Start server
uvicorn main:app --reload --port 8000
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

```bash
# Navigate to frontend directory
cd frontend

# Start React dev server
npm start
```

**URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend API Docs: http://localhost:8000/docs

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
Press `Ctrl+C` in the terminal running uvicorn

### Stop Frontend
Press `Ctrl+C` in the terminal running npm

### Kill by Port (if needed)

**Find process on port 8000 (backend):**
```bash
lsof -ti:8000 | xargs kill -9
```

**Find process on port 3000 (frontend):**
```bash
lsof -ti:3000 | xargs kill -9
```

---

## 🔧 Common Commands

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
- [ ] Backend `.env` file exists with correct values
- [ ] Frontend `.env` file exists with correct values
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
# Check .env file exists
ls backend/.env

# Check dependencies installed
source venv/bin/activate
pip list | grep fastapi

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend won't start

```bash
# Check .env file exists
ls frontend/.env

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
