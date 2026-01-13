import React, { useState, useMemo } from 'react';

function CompanyCard({ company, selectedJobId, onJobSelect }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedLocations, setExpandedLocations] = useState({});

  const jobs = company.jobs || [];

  // Group jobs by location
  const jobsByLocation = useMemo(() => {
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
  }, [jobs]);

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

  return (
    <div className={`company-card ${isExpanded ? 'expanded' : ''}`}>
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
          <div className="company-count">Ready: {company.ready_count}</div>
        </div>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

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
                  {locationJobs.map((job) => (
                    <div
                      key={job.id}
                      className={`job-item ${selectedJobId === job.id ? 'selected' : ''}`}
                      onClick={() => handleJobClick(job)}
                    >
                      <div className="job-radio">
                        <div className="job-radio-inner" />
                      </div>
                      <span className="job-title">{job.title || 'Untitled'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default CompanyCard;
