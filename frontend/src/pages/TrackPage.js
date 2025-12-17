import React from 'react';
import './PlaceholderPage.css';

function TrackPage() {
  return (
    <div className="placeholder-container">
      <div className="placeholder-content">
        <div className="placeholder-icon">📋</div>
        <h1>Track</h1>
        <p className="placeholder-description">
          Manage your applications from applied to offer.
        </p>
        <div className="placeholder-features">
          <h3>Coming Soon:</h3>
          <ul>
            <li>Kanban board view (Applied, Interview, Offer, Rejected)</li>
            <li>Add notes and follow-up reminders</li>
            <li>Track application status and timeline</li>
            <li>Analytics and insights on your job search</li>
          </ul>
        </div>
        <div className="placeholder-badge">Under Development</div>
      </div>
    </div>
  );
}

export default TrackPage;
