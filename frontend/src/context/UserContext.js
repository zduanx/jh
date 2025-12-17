import { createContext, useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';

const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Shared fetch logic (DRY principle)
  const fetchUserData = async (redirectOnError = true) => {
    try {
      const token = localStorage.getItem('access_token');

      if (!token) {
        setLoading(false);
        return;
      }

      const apiUrl = process.env.REACT_APP_API_URL;
      const response = await fetch(`${apiUrl}/api/user`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          // Token is invalid - clear and redirect to login
          localStorage.removeItem('access_token');
          setUserData(null);
          if (redirectOnError) {
            navigate('/login');
          }
          return;
        }
        throw new Error('Failed to fetch user data');
      }

      const data = await response.json();
      setUserData(data);
    } catch (err) {
      console.error('Error fetching user data:', err);
      // Don't redirect on error - user might be offline
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserData();
  }, [navigate]);

  const logout = () => {
    localStorage.removeItem('access_token');
    setUserData(null);
    navigate('/login');
  };

  const refreshUserData = async () => {
    setLoading(true);
    await fetchUserData(false); // Don't redirect on refresh errors
  };

  return (
    <UserContext.Provider value={{ userData, loading, logout, refreshUserData }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === null) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
