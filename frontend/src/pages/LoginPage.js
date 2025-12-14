import React from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import './LoginPage.css';

function LoginPage() {
  const navigate = useNavigate();

  const handleSuccess = async (credentialResponse) => {
    console.log('Google login success!');
    console.log('Credential:', credentialResponse);

    try {
      // Exchange Google token with our backend for a JWT
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: credentialResponse.credential
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Authentication failed');
      }

      const data = await response.json();

      // Store our backend JWT token
      localStorage.setItem('access_token', data.access_token);

      // Navigate to info page
      navigate('/info');
    } catch (error) {
      console.error('Backend authentication error:', error);
      alert(`Login failed: ${error.message}`);
    }
  };

  const handleError = () => {
    console.error('Google login failed');
    alert('Login failed. Please try again.');
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Job Hunt Tracker</h1>
        <p>Track your job applications across multiple companies</p>

        <div className="login-button-wrapper">
          <GoogleLogin
            onSuccess={handleSuccess}
            onError={handleError}
            useOneTap
          />
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
