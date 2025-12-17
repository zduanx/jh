import './DashboardPage.css';
import { useUser } from '../context/UserContext';

function DashboardPage() {
  const { userData, loading } = useUser();

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading-card">
          <div className="spinner"></div>
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!userData) {
    return null; // UserContext will handle redirect to login
  }

  return (
    <div className="dashboard-container">
      {/* Welcome Section */}
      <div className="welcome-section">
        <div className="welcome-header">
          {userData && (
            <>
              <img
                src={userData.picture}
                alt="Profile"
                className="profile-avatar"
              />
              <div className="welcome-text">
                <h1>Welcome back, {userData.name?.split(' ')[0]}!</h1>
                <p className="user-email">{userData.email}</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <h3>Total Applications</h3>
            <p className="stat-value">0</p>
            <span className="stat-label">No applications yet</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⏳</div>
          <div className="stat-content">
            <h3>In Progress</h3>
            <p className="stat-value">0</p>
            <span className="stat-label">Active applications</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <h3>Interviews</h3>
            <p className="stat-value">0</p>
            <span className="stat-label">Scheduled interviews</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-content">
            <h3>Offers</h3>
            <p className="stat-value">0</p>
            <span className="stat-label">Received offers</span>
          </div>
        </div>
      </div>

      {/* User Info Section */}
      {userData && (
        <div className="info-section">
          <h2>Account Information</h2>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Email</span>
              <span className="info-value">{userData.email}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Name</span>
              <span className="info-value">{userData.name}</span>
            </div>
            {userData.last_login && (
              <div className="info-item">
                <span className="info-label">Last Login</span>
                <span className="info-value">
                  {new Date(userData.last_login).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                  })}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default DashboardPage;
