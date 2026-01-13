import React, { useState, useEffect, useCallback } from 'react';
import './SearchPage.css';
import CompanyCard from './CompanyCard';
import JobDetails from './JobDetails';

function SearchPage() {
  const [companies, setCompanies] = useState([]);
  const [totalReady, setTotalReady] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobLoading, setJobLoading] = useState(false);

  const apiUrl = process.env.REACT_APP_API_URL;

  // Fetch jobs list on mount
  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Not authenticated');
      }

      const res = await fetch(`${apiUrl}/api/jobs`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to fetch jobs');
      }

      const data = await res.json();
      setCompanies(data.companies || []);
      setTotalReady(data.total_ready || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Fetch job details when selection changes
  const fetchJobDetails = useCallback(async (jobId) => {
    if (!jobId) {
      setSelectedJob(null);
      return;
    }

    setJobLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${apiUrl}/api/jobs/${jobId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to fetch job details');
      }

      const data = await res.json();
      setSelectedJob(data);
    } catch (err) {
      console.error('Error fetching job details:', err);
      setSelectedJob(null);
    } finally {
      setJobLoading(false);
    }
  }, [apiUrl]);

  const handleJobSelect = (jobId) => {
    setSelectedJobId(jobId);
    fetchJobDetails(jobId);
  };

  // Loading state
  if (loading) {
    return (
      <div className="search-container">
        <div className="search-header">
          <h1>Search Jobs</h1>
          <p>Browse and search your extracted job postings</p>
        </div>
        <div className="search-loading">
          <div className="spinner" />
          <span>Loading jobs...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="search-container">
        <div className="search-header">
          <h1>Search Jobs</h1>
          <p>Browse and search your extracted job postings</p>
        </div>
        <div className="search-error">
          <div className="search-error-icon">⚠️</div>
          <p>{error}</p>
          <button onClick={fetchJobs}>Try Again</button>
        </div>
      </div>
    );
  }

  // Empty state - no jobs
  if (companies.length === 0) {
    return (
      <div className="search-container">
        <div className="search-header">
          <h1>Search Jobs</h1>
          <p>Browse and search your extracted job postings</p>
        </div>
        <div className="search-empty">
          <div className="search-empty-icon">📭</div>
          <h2>No Jobs Found</h2>
          <p>Run an ingestion to extract job postings from company career pages.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="search-container">
      <div className="search-header">
        <h1>Search Jobs</h1>
        <p>Browse and search your extracted job postings</p>
      </div>

      {/* Top Bar - Search + Sync All */}
      <div className="search-top-bar">
        <div className="search-input-wrapper">
          <input
            type="text"
            placeholder="Search jobs by title, company, or location..."
            disabled
            title="Coming in Phase 3C"
          />
          <button className="search-btn" disabled title="Coming in Phase 3C">
            Search
          </button>
        </div>
        <button className="sync-all-btn" disabled title="Coming in Phase 3B">
          Sync All
        </button>
      </div>

      {/* Main Content - 1:3 Layout */}
      <div className="search-main">
        {/* Left Column - Companies */}
        <div className="companies-column">
          {companies.map((company) => (
            <CompanyCard
              key={company.name}
              company={company}
              selectedJobId={selectedJobId}
              onJobSelect={handleJobSelect}
            />
          ))}
        </div>

        {/* Right Column - Job Details */}
        <JobDetails job={selectedJob} loading={jobLoading} />
      </div>

      {/* Footer - Total Count */}
      <div className="search-footer">
        Total: {totalReady} ready {totalReady === 1 ? 'job' : 'jobs'}
      </div>
    </div>
  );
}

export default SearchPage;
