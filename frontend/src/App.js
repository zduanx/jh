import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import LoginPage from './pages/LoginPage';
import InfoPage from './pages/InfoPage';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

// TODO: Replace with your actual Google Client ID
// Get this from https://console.cloud.google.com/
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID_HERE';

function App() {
  // Smart root redirect: check if user is already logged in
  const RootRedirect = () => {
    const token = localStorage.getItem('access_token');
    return <Navigate to={token ? "/info" : "/login"} replace />;
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <Router>
        <Routes>
          {/* Smart redirect: go to /info if logged in, /login otherwise */}
          <Route path="/" element={<RootRedirect />} />

          {/* Public route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected route */}
          <Route
            path="/info"
            element={
              <ProtectedRoute>
                <InfoPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </GoogleOAuthProvider>
  );
}

export default App;
