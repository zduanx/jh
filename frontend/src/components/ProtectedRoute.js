import React from 'react';
import { Navigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';

function ProtectedRoute({ children }) {
  const { loading } = useUser();

  // Check if user has a JWT token from our backend
  const token = localStorage.getItem('access_token');

  if (!token) {
    // No token → redirect to login
    return <Navigate to="/login" replace />;
  }

  // Wait for UserContext to finish loading before rendering children
  // This prevents the race condition where children mount before user data is fetched
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div className="spinner"></div>
      </div>
    );
  }

  // Has token and context is ready → show protected content
  return children;
}

export default ProtectedRoute;
