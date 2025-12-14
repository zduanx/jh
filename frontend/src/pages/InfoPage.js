import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './InfoPage.css';

function InfoPage() {
  const navigate = useNavigate();
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch user data from backend
    const fetchUserData = async () => {
      try {
        const token = localStorage.getItem('access_token');

        if (!token) {
          navigate('/login');
          return;
        }

        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/user`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          }
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            // Token is invalid or expired
            localStorage.removeItem('access_token');
            navigate('/login');
            return;
          }
          throw new Error('Failed to fetch user data');
        }

        const data = await response.json();
        setUserData(data);
      } catch (err) {
        console.error('Error fetching user data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
  }, [navigate]);

  const handleLogout = () => {
    // Clear token and navigate to login
    localStorage.removeItem('access_token');
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="info-container">
        <div className="info-card">
          <h1>Loading...</h1>
          <p>Fetching your information...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="info-container">
        <div className="info-card">
          <h1>Error</h1>
          <p className="error">{error}</p>
          <button onClick={handleLogout} className="logout-button">
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="info-container">
      <div className="info-card">
        <h1>Welcome!</h1>

        {userData && (
          <div className="user-info">
            <img
              src={userData.picture}
              alt="Profile"
              className="profile-picture"
            />
            <h2>{userData.name}</h2>
            <p className="email">{userData.email}</p>
          </div>
        )}

        <div className="info-section">
          <h3>Authentication Complete!</h3>
          <p>You've successfully logged in with Google and authenticated with our backend.</p>
          <p className="next-step">
            ✅ Google OAuth verified<br />
            ✅ Backend JWT issued<br />
            ✅ User data fetched from backend
          </p>
        </div>

        {userData && (
          <details className="token-details">
            <summary>View User Data (for debugging)</summary>
            <pre>{JSON.stringify(userData, null, 2)}</pre>
          </details>
        )}

        <button onClick={handleLogout} className="logout-button">
          Logout
        </button>
      </div>
    </div>
  );
}

export default InfoPage;
