# Frontend Development

React, routing, state management, and frontend-backend communication.

---

## Table of Contents

1. [Why React](#why-react)
2. [Component Architecture](#component-architecture)
3. [Protected Routes](#protected-routes)
4. [Frontend Serving](#frontend-serving)
5. [First Visit Flow](#first-visit-flow)
6. [Bootstrap Process](#bootstrap-process)
7. [API Calls](#api-calls)
8. [Token in Requests](#token-in-requests)
9. [Bootstrap Library](#bootstrap-library)

---

## Why React

### What is React?

**= JavaScript library for building user interfaces**

Created by Facebook (Meta), most popular frontend framework.

### Why We Chose React

1. ✅ **Industry standard** - Most companies use React
2. ✅ **Job market** - Highly demanded skill
3. ✅ **Component-based** - Reusable UI pieces
4. ✅ **Large ecosystem** - Libraries for everything
5. ✅ **Great with APIs** - Perfect for our FastAPI backend

### Alternatives

- **Vue.js** - Progressive framework, easier learning curve
- **Angular** - Full-featured, more opinionated
- **Svelte** - Compiled framework, very fast
- **Vanilla JS** - No framework (for simple projects)

---

## Component Architecture

### Components = Reusable UI Pieces

```javascript
// LoginButton.js - Component
function LoginButton() {
  return <button onClick={handleLogin}>Login with Google</button>;
}

// App.js - Use component
function App() {
  return (
    <div>
      <LoginButton />
      <LoginButton />  {/* Reuse! */}
    </div>
  );
}
```

### Our App Structure

```
App
├── LoginPage
│   └── GoogleLoginButton
└── InfoPage (protected)
    ├── UserProfile
    └── LogoutButton
```

---

## Protected Routes

### What are Protected Routes?

**= Pages that require authentication**

```javascript
// Without protection - anyone can access
<Route path="/info" element={<InfoPage />} />

// With protection - only authenticated users
<Route path="/info" element={
  <ProtectedRoute>
    <InfoPage />
  </ProtectedRoute>
} />
```

### How Protection Works

```javascript
function ProtectedRoute({ children }) {
  const token = localStorage.getItem('access_token');

  if (!token) {
    // No token → redirect to login
    return <Navigate to="/login" />;
  }

  // Has token → verify with backend
  const isValid = verifyTokenWithBackend(token);

  if (!isValid) {
    // Invalid token → clear and redirect
    localStorage.removeItem('access_token');
    return <Navigate to="/login" />;
  }

  // Valid token → show protected content
  return children;
}
```

### Our Route Setup

```javascript
<Routes>
  <Route path="/login" element={<LoginPage />} />

  <Route path="/info" element={
    <ProtectedRoute>
      <InfoPage />
    </ProtectedRoute>
  } />
</Routes>
```

---

## Frontend Serving

### How Does Frontend Get to Users?

**Step 1:** User visits your website

**Step 2:** Browser downloads static files from hosting (Vercel/S3):
- `index.html` (entry point)
- `bundle.js` (React code compiled to JavaScript)
- `styles.css` (styling)
- Images, fonts, etc.

**Step 3:** Browser runs React app locally

**Step 4:** React app calls your backend API

### Architecture

```
Vercel/S3 (Static File Hosting)
    ↓ (User downloads once)
User's Browser (React runs here)
    ↓ (Makes API calls when needed)
Backend API (FastAPI on EC2)
```

### Key Point

**Frontend is NOT a server!**
- It's just files downloaded to user's browser
- React runs in the browser (client-side)
- Backend is the actual server

---

## First Visit Flow

### What Happens on First Visit?

**User types:** `yourapp.vercel.app`

**Yes, it's a GET request!** Here's the complete flow:

---

### Step-by-Step: Initial GET Requests

**Request 1: Get HTML**

```http
Browser → GET https://yourapp.vercel.app/ → Vercel CDN

Response:
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
  <head>
    <title>Job Tracker</title>
  </head>
  <body>
    <div id="root"></div>
    <script src="/static/js/bundle.js"></script>
  </body>
</html>
```

**Key point:** HTML is almost empty! Just `<div id="root">` and JavaScript link.

---

**Request 2: Get JavaScript**

Browser sees `<script src="/static/js/bundle.js">` and makes another GET:

```http
Browser → GET https://yourapp.vercel.app/static/js/bundle.js → Vercel

Response: Your React code (compiled JavaScript)
```

**Request 3: Get CSS**

```http
Browser → GET https://yourapp.vercel.app/static/css/main.css → Vercel

Response: Styles
```

---

### Summary of Initial GET Requests

| # | Request | To Where? | Response | Purpose |
|---|---------|-----------|----------|---------|
| 1 | `GET /` | Vercel | `index.html` | Entry point |
| 2 | `GET /static/js/bundle.js` | Vercel | JavaScript | React code |
| 3 | `GET /static/css/main.css` | Vercel | CSS | Styles |

**ALL requests go to Vercel!** Backend (Lambda) not called yet.

---

### When Does Backend Get Called?

**Only when user interacts with the app:**

```javascript
// User clicks "Login with Google" button
// React makes FIRST request to Lambda
fetch('https://api-gateway-url.amazonaws.com/api/auth/google', {
  method: 'POST',  // This is a POST, not GET!
  body: JSON.stringify({ token: googleToken })
})
```

**This is the FIRST request to your Lambda function!**

---

### Complete First Visit Timeline

```
1. User types: yourapp.vercel.app
        ↓ (GET request)
2. Vercel sends: index.html
        ↓
3. Browser sees <script src="bundle.js">
        ↓ (GET request)
4. Vercel sends: bundle.js (React code)
        ↓ (GET request)
5. Vercel sends: main.css (styles)
        ↓
6. Browser executes JavaScript
        ↓
7. React renders login page
        ↓
8. User sees "Login with Google" button ✅
        ↓ (USER IS HERE - backend never called yet!)
9. User clicks "Login"
        ↓ (First POST request to Lambda!)
10. Lambda validates Google token
        ↓
11. Lambda returns JWT
        ↓
12. React stores JWT in localStorage
        ↓
13. React redirects to /info page
```

---

### Key Insights

**Frontend serving = Static file GET requests**
- Downloads HTML, JS, CSS files
- Like downloading a file from Google Drive
- Vercel is a fancy file server

**Backend API = Dynamic logic**
- Only called when app needs data
- POST/GET/PUT/DELETE to Lambda
- First called when user logs in

**No backend on initial load!**
- React app downloads and runs completely in browser
- Backend only called when needed

---

## Bootstrap Process

### What is "Bootstrapping"?

**= The initial loading/startup of the React app**

**Not related to Bootstrap.js library!**

### Step-by-Step Process

```
1. User types: yourapp.vercel.app
        ↓
2. Browser requests files from Vercel
        ↓
3. Vercel sends: index.html + bundle.js (~500KB)
        ↓
4. Browser downloads JavaScript
        ↓
5. Browser parses and executes bundle.js
        ↓
6. React library starts up
        ↓
7. React renders components (Login button, etc.)
        ↓
8. App is now interactive! ✅
        ↓
9. User clicks "Login" → React calls backend API
```

**Time:** ~1-3 seconds for first visit

### What Gets Downloaded?

The `bundle.js` file contains:
- React library code
- Your components
- Routing logic
- API call logic
- All your JavaScript

**Size:** ~200KB - 2MB (compressed)

---

## API Calls

### Making Backend Requests

```javascript
// GET request
const response = await fetch('https://api.example.com/jobs');
const jobs = await response.json();

// POST request with data
const response = await fetch('https://api.example.com/auth/google', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ token: googleToken })
});
const data = await response.json();
```

### With Error Handling

```javascript
async function loginWithGoogle(googleToken) {
  try {
    const response = await fetch(`${API_URL}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: googleToken })
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    return data;

  } catch (error) {
    console.error('Login error:', error);
    alert('Login failed. Please try again.');
  }
}
```

---

## Token in Requests

### Including JWT in API Calls

**Industry standard:** `Authorization: Bearer <token>` header

```javascript
// Get token from localStorage
const token = localStorage.getItem('access_token');

// Include in request
const response = await fetch('https://api.example.com/api/user', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Complete Authentication Flow

```javascript
// 1. Login - get JWT
async function login(googleToken) {
  const res = await fetch('/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: googleToken })
  });

  const data = await res.json();

  // 2. Store JWT
  localStorage.setItem('access_token', data.access_token);
}

// 3. Use JWT for all subsequent requests
async function getUser() {
  const token = localStorage.getItem('access_token');

  const res = await fetch('/api/user', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  return await res.json();
}

// 4. Logout - clear token
function logout() {
  localStorage.removeItem('access_token');
}
```

### Why Include Token?

Backend needs to know:
1. **Who is making the request?** (user identification)
2. **Are they authorized?** (permission check)

Token provides both!

---

## Bootstrap Library

### What is Bootstrap.js?

**DIFFERENT from "bootstrapping" concept!**

**Bootstrap.js = CSS/UI framework** (made by Twitter)

```bash
npm install bootstrap
```

**What it provides:**
- Pre-built CSS styles
- UI components (buttons, modals, forms, navbars)
- Responsive grid system
- JavaScript for interactive components

### Example Usage

```javascript
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  return (
    <div className="container">
      <button className="btn btn-primary">
        Styled Button
      </button>
    </div>
  );
}
```

### Bootstrap vs "Bootstrapping"

| Term | What It Is |
|------|-----------|
| **"Bootstrapping"** | Process of loading/starting app |
| **Bootstrap.js** | CSS framework for styling |

**Confusion:** Same word, totally different meanings!

### Do We Need Bootstrap.js?

**Optional!** It's just for styling.

**Alternatives:**
- **Tailwind CSS** (modern utility-first CSS)
- **Material-UI** (Google's design system)
- **Plain CSS** (full control, no library)

**For POC:** Plain CSS is fine. Focus on functionality first.

---

**Next:** See [security.md](./security.md) for security best practices.
