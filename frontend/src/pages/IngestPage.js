import React from 'react';
import './PlaceholderPage.css';

function IngestPage() {
  return (
    <div className="placeholder-container">
      <div className="placeholder-content">
        <div className="placeholder-icon">⬇️</div>
        <h1>Ingest</h1>
        <p className="placeholder-description">
          Fetch and import job postings from company career pages.
        </p>
        <div className="placeholder-features">
          <h3>Coming Soon:</h3>
          <ul>
            <li>Trigger job scraping from multiple job boards</li>
            <li>Monitor ingestion pipeline status</li>
            <li>View ingestion logs and statistics</li>
            <li>Configure scraping schedules</li>
          </ul>
        </div>
        <div className="placeholder-badge">Under Development</div>
      </div>
    </div>
  );
}

export default IngestPage;
