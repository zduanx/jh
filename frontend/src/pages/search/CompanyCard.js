import React, { useState, useMemo } from 'react';

function CompanyCard({ company, totalCount, selectedJobId, onJobSelect, apiUrl, onReExtractComplete, trackedJobs }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedLocations, setExpandedLocations] = useState({});
  const [isReExtracting, setIsReExtracting] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [reExtractResult, setReExtractResult] = useState(null);

  // Group jobs by location
  const jobsByLocation = useMemo(() => {
    const jobs = company.jobs || [];
    const groups = {};
    jobs.forEach((job) => {
      const location = job.location || 'Location not specified';
      if (!groups[location]) {
        groups[location] = [];
      }
      groups[location].push(job);
    });
    // Sort locations alphabetically, but put "Location not specified" at the end
    const sortedLocations = Object.keys(groups).sort((a, b) => {
      if (a === 'Location not specified') return 1;
      if (b === 'Location not specified') return -1;
      return a.localeCompare(b);
    });
    return sortedLocations.map((loc) => ({ location: loc, jobs: groups[loc] }));
  }, [company.jobs]);

  const handleHeaderClick = () => {
    setIsExpanded(!isExpanded);
  };

  const handleLocationToggle = (location, e) => {
    e.stopPropagation();
    setExpandedLocations((prev) => ({
      ...prev,
      [location]: !prev[location],
    }));
  };

  const handleJobClick = (job) => {
    onJobSelect(job.id);
  };

  const handleReExtractClick = (e) => {
    e.stopPropagation();
    setShowConfirmModal(true);
  };

  const handleConfirmReExtract = async () => {
    setShowConfirmModal(false);
    setIsReExtracting(true);
    setReExtractResult(null);

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${apiUrl}/api/jobs/re-extract`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ company: company.name }),
      });

      const data = await res.json();

      if (res.ok) {
        setReExtractResult({
          success: true,
          message: `Re-extracted ${data.successful}/${data.total_jobs} jobs`,
        });
        // Notify parent to refresh data
        if (onReExtractComplete) {
          onReExtractComplete(company.name);
        }
      } else {
        setReExtractResult({
          success: false,
          message: data.detail || 'Re-extraction failed',
        });
      }
    } catch (err) {
      setReExtractResult({
        success: false,
        message: err.message || 'Network error',
      });
    } finally {
      setIsReExtracting(false);
      // Auto-dismiss toast after 5 seconds
      setTimeout(() => setReExtractResult(null), 5000);
    }
  };

  const handleCancelReExtract = () => {
    setShowConfirmModal(false);
  };

  return (
    <div className={`company-card ${isExpanded ? 'expanded' : ''} ${isReExtracting ? 'extracting' : ''}`}>
      <div className="company-card-header" onClick={handleHeaderClick}>
        <div className="company-logo">
          {company.logo_url ? (
            <img src={company.logo_url} alt={company.display_name} />
          ) : (
            company.display_name.charAt(0).toUpperCase()
          )}
        </div>
        <div className="company-info">
          <div className="company-name">{company.display_name}</div>
          <div className="company-count">{company.ready_count}/{totalCount}</div>
        </div>
        <div className="company-actions">
          <button
            className="company-re-extract-btn"
            onClick={handleReExtractClick}
            disabled={isReExtracting || company.ready_count === 0}
            title="Re-extract all jobs for this company"
          >
            {isReExtracting ? 'Extracting...' : 'Re-Extract'}
          </button>
        </div>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {/* Toast notification */}
      {reExtractResult && (
        <div className={`company-re-extract-toast ${reExtractResult.success ? 'success' : 'error'}`}>
          {reExtractResult.success ? '✓' : '✗'} {reExtractResult.message}
        </div>
      )}

      {isExpanded && (
        <div className="job-list">
          {jobsByLocation.map(({ location, jobs: locationJobs }) => (
            <div key={location} className="location-group">
              <div
                className="location-header"
                onClick={(e) => handleLocationToggle(location, e)}
              >
                <span className="location-expand-icon">
                  {expandedLocations[location] ? '▾' : '▸'}
                </span>
                <span className="location-name">{location}</span>
                <span className="location-count">({locationJobs.length})</span>
              </div>

              {expandedLocations[location] && (
                <div className="location-jobs">
                  {locationJobs.map((job) => {
                    const isTracked = trackedJobs && trackedJobs[job.id];
                    return (
                      <div
                        key={job.id}
                        className={`job-item ${selectedJobId === job.id ? 'selected' : ''} ${isTracked ? 'tracked' : ''}`}
                        onClick={() => handleJobClick(job)}
                      >
                        <div className="job-radio">
                          <div className="job-radio-inner" />
                        </div>
                        <span className="job-title">{job.title || 'Untitled'}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="modal-overlay" onClick={handleCancelReExtract}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Confirm Re-Extract</h2>
            <p>
              Re-extract all <strong>{company.ready_count}</strong> jobs for{' '}
              <strong>{company.display_name}</strong>?
            </p>
            <p className="modal-subtitle">
              This will re-process raw HTML from S3 and update job descriptions and requirements.
            </p>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={handleCancelReExtract}>
                Cancel
              </button>
              <button className="btn-confirm" onClick={handleConfirmReExtract}>
                Re-Extract
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CompanyCard;
