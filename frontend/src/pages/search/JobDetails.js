import React from 'react';

function JobDetails({ job, loading }) {
  if (loading) {
    return (
      <div className="job-details-column">
        <div className="job-details-empty">
          <div className="spinner" style={{ width: 24, height: 24, border: '2px solid #e2e8f0', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          <p>Loading job details...</p>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="job-details-column">
        <div className="job-details-empty">
          <div className="job-details-empty-icon">📋</div>
          <p>Select a company and job to view details</p>
        </div>
      </div>
    );
  }

  return (
    <div className="job-details-column">
      <div className="job-details-content">
        <div className="job-details-header">
          <h2 className="job-details-title">
            <a href={job.url} target="_blank" rel="noopener noreferrer">
              {job.title || 'Untitled Position'}
            </a>
            <span className="external-icon">↗</span>
          </h2>
          <p className="job-details-subtitle">
            ID: {job.id} | {job.company}:{job.external_id}
          </p>
        </div>

        <div className="job-details-body">
          <div className="job-details-section">
            <h3>Location</h3>
            <div className={`job-details-section-content ${!job.location ? 'empty' : ''}`}>
              {job.location || 'Location not specified'}
            </div>
          </div>

          <div className="job-details-section">
            <h3>Description</h3>
            <div className={`job-details-section-content ${!job.description ? 'empty' : ''}`}>
              {job.description || 'No description available'}
            </div>
          </div>

          <div className="job-details-section">
            <h3>Requirements</h3>
            <div className={`job-details-section-content ${!job.requirements ? 'empty' : ''}`}>
              {job.requirements || 'No requirements specified'}
            </div>
          </div>
        </div>

        <div className="job-details-footer">
          <button className="re-extract-btn" disabled title="Coming in Phase 3B">
            Re-Extract
          </button>
        </div>
      </div>
    </div>
  );
}

export default JobDetails;
