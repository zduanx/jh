import React from 'react';
import './PlaceholderPage.css';

function SearchPage() {
  return (
    <div className="placeholder-container">
      <div className="placeholder-content">
        <div className="placeholder-icon">🔍</div>
        <h1>Search Jobs</h1>
        <p className="placeholder-description">
          Search and filter through ingested job postings to find opportunities that match your criteria.
        </p>
        <div className="placeholder-features">
          <h3>Coming Soon:</h3>
          <ul>
            <li>Advanced search with filters (company, title, location, salary)</li>
            <li>Save jobs to your tracking list</li>
            <li>View detailed job descriptions</li>
            <li>Compare similar positions</li>
          </ul>
        </div>
        <div className="placeholder-badge">Under Development</div>
      </div>
    </div>
  );
}

export default SearchPage;
