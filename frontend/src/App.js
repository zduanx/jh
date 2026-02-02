import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { UserProvider } from './context/UserContext';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import IngestPage from './pages/IngestPage';
import SearchPage from './pages/SearchPage';
import TrackPage from './pages/track/TrackPage';
import StoriesPage from './pages/stories/StoriesPage';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

function App() {
  // Smart root redirect: check if user is already logged in
  const RootRedirect = () => {
    const token = localStorage.getItem('access_token');
    return <Navigate to={token ? "/dashboard" : "/login"} replace />;
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <Router>
        <UserProvider>
          <Routes>
            {/* Smart redirect: go to /dashboard if logged in, /login otherwise */}
            <Route path="/" element={<RootRedirect />} />

            {/* Public route - no layout */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected routes - with sidebar layout */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Layout>
                    <DashboardPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/ingest"
              element={
                <ProtectedRoute>
                  <Layout>
                    <IngestPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/search"
              element={
                <ProtectedRoute>
                  <Layout>
                    <SearchPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/track"
              element={
                <ProtectedRoute>
                  <Layout>
                    <TrackPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/stories"
              element={
                <ProtectedRoute>
                  <Layout>
                    <StoriesPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </UserProvider>
      </Router>
    </GoogleOAuthProvider>
  );
}

export default App;
