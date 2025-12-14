# Job Hunt Tracker - Frontend

React frontend with Google OAuth integration.

---

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Get Google OAuth Client ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized JavaScript origins:
   - `http://localhost:3000` (for development)
   - Your Vercel domain (for production)
7. Copy the **Client ID**

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your Google Client ID:

```bash
REACT_APP_GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
REACT_APP_API_URL=http://localhost:8000
```

### 4. Run Development Server

```bash
npm start
```

App will open at [http://localhost:3000](http://localhost:3000)

---

## Features

**Current (Phase 1 - POC):**
- Google OAuth login button
- Protected routes (redirect to login if not authenticated)
- User info display (name, email, profile picture)
- Token stored in localStorage
- Logout functionality

**Coming Next (Phase 2):**
- Exchange Google token with backend for JWT
- Call backend API with JWT
- Full authentication flow

---

## Project Structure

```
frontend/
├── public/                 # Static files
├── src/
│   ├── components/         # Reusable components
│   │   └── ProtectedRoute.js
│   ├── pages/             # Page components
│   │   ├── LoginPage.js   # Google login
│   │   └── InfoPage.js    # Protected user info page
│   ├── App.js             # Main app with routing
│   └── index.js           # Entry point
├── .env                   # Environment variables (not committed)
├── .env.example           # Example env file
└── package.json           # Dependencies
```

---

## Available Scripts

### `npm start`
Runs the app in development mode.

### `npm run build`
Builds the app for production to the `build/` folder.

### `npm test`
Launches the test runner.

---

## How It Works

### 1. User visits app
```
GET http://localhost:3000
→ Redirects to /login
```

### 2. User clicks "Login with Google"
```
Google OAuth popup appears
User logs in with Google account
Google returns credential token
```

### 3. Frontend stores token
```javascript
localStorage.setItem('google_token', credentialResponse.credential);
```

### 4. User navigates to /info
```
ProtectedRoute checks for token
If token exists → show InfoPage
If no token → redirect to /login
```

### 5. InfoPage displays user info
```javascript
// Decode JWT to get user data
const payload = token.split('.')[1];
const decoded = JSON.parse(atob(payload));
// Show: name, email, picture
```

---

## Next Steps

1. Get Google Client ID from Google Cloud Console
2. Add Client ID to `.env` file
3. Run `npm start`
4. Click "Login with Google"
5. See your info on /info page!

After this works, we'll build the backend to exchange the Google token for our own JWT.

---

## Troubleshooting

**"Login button doesn't appear"**
- Check that `REACT_APP_GOOGLE_CLIENT_ID` is set in `.env`
- Restart dev server after changing `.env`

**"Popup blocked"**
- Allow popups for localhost:3000
- Or use One Tap login (already enabled)

**"Invalid client ID"**
- Verify Client ID in `.env` matches Google Cloud Console
- Make sure `http://localhost:3000` is in authorized origins

---

## Deployment

This will be deployed to **Vercel**:

1. Push code to GitHub
2. Connect GitHub repo to Vercel
3. Add environment variables in Vercel dashboard
4. Vercel auto-deploys on every push!

---

Built with React + Google OAuth for authentication.
