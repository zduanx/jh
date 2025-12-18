# Frontend Login Race Condition

**Date**: December 18, 2025
**Status**: Resolved

---

## Symptom

After logging in via Google OAuth, user navigates to dashboard but nothing loads except the navbar. Refreshing the page fixes it - all requests fire correctly.

## Root Cause

Race condition between navigation and UserContext initialization.

### The Problem Flow

```
1. LoginPage: User logs in successfully
   - Token stored: localStorage.setItem('access_token', data.access_token)
   - Navigate immediately: navigate('/dashboard')

2. ProtectedRoute: Checks token synchronously
   - Token exists in localStorage → allows through
   - NO waiting for UserContext to initialize

3. UserProvider: Now tries to initialize
   - Starts with loading = true
   - DashboardPage already mounting

4. DashboardPage: Renders while UserContext is initializing
   - userData = null (not set yet)
   - loading = true (just started)
   - Shows loading spinner forever
```

### Why Refresh Worked

On refresh:
1. Page reloads completely
2. UserProvider initializes BEFORE any child components mount
3. Has time to fetch user data before DashboardPage renders
4. Data is available when DashboardPage needs it

## Technical Details

### App.js Structure
```javascript
<GoogleOAuthProvider>
  <Router>
    <UserProvider>  // Wraps everything
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        } />
      </Routes>
    </UserProvider>
  </Router>
</GoogleOAuthProvider>
```

### Old ProtectedRoute (Buggy)
```javascript
function ProtectedRoute({ children }) {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;  // Renders immediately, no context awareness
}
```

### Old LoginPage (Buggy)
```javascript
localStorage.setItem('access_token', data.access_token);
navigate('/dashboard');  // Navigates immediately, context not ready
```

## Solution

Two-part fix:

### 1. ProtectedRoute - Wait for Context
```javascript
function ProtectedRoute({ children }) {
  const { loading } = useUser();  // Now context-aware
  const token = localStorage.getItem('access_token');

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Wait for UserContext to finish loading
  if (loading) {
    return <div className="spinner"></div>;
  }

  return children;
}
```

### 2. LoginPage - Fetch Before Navigate
```javascript
localStorage.setItem('access_token', data.access_token);

// Fetch user data BEFORE navigating
await refreshUserData();

navigate('/dashboard');
```

## Files Changed

- `frontend/src/components/ProtectedRoute.js` - Added context awareness
- `frontend/src/pages/LoginPage.js` - Added refreshUserData before navigate

## Lessons Learned

1. **React effects run after paint** - useEffect in UserProvider runs after DashboardPage has already rendered
2. **Route guards should be context-aware** - Checking localStorage alone is insufficient
3. **Navigation timing matters** - Ensure async operations complete before route changes
4. **Classic anti-pattern** - Route changes outpacing async initialization

## Related

- Similar issue could occur with any protected route if context isn't ready
- Consider adding suspense boundaries for more complex cases
