import React from 'react';
import { Navigate } from 'react-router-dom';

function ProtectedRoute({ children }) {
  // Check if user has a JWT token from our backend
  const token = localStorage.getItem('access_token');

  if (!token) {
    // No token → redirect to login
    return <Navigate to="/login" replace />;
  }

  // Has token → show protected content
  return children;
}

export default ProtectedRoute;
