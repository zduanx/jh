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

  // Sync state
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [syncError, setSyncError] = useState(null);

  // Search state (Phase 3C)
  const [searchQuery, setSearchQuery] = useState('');
  const [activeQuery, setActiveQuery] = useState(null); // Query currently applied
  const [isSearching, setIsSearching] = useState(false);
  const [companyTotals, setCompanyTotals] = useState({}); // Original totals per company

  // Tracking state (Phase 4A)
  // { job_id: { tracking_id, stage } }
  const [trackedJobs, setTrackedJobs] = useState({});

  const apiUrl = process.env.REACT_APP_API_URL;

  // Fetch tracked job IDs on mount (Phase 4A)
  const fetchTrackedIds = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const res = await fetch(`${apiUrl}/api/tracked/ids`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        // Convert string keys to numbers for consistency
        const tracked = {};
        Object.entries(data.tracked || {}).forEach(([jobId, info]) => {
          tracked[parseInt(jobId, 10)] = info;
        });
        setTrackedJobs(tracked);
      }
    } catch (err) {
      console.error('Error fetching tracked IDs:', err);
    }
  }, [apiUrl]);

  // Track a job (Phase 4A)
  const handleTrackJob = async (jobId) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${apiUrl}/api/tracked`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ job_id: jobId }),
      });

      if (res.ok) {
        const data = await res.json();
        // Update cache
        setTrackedJobs(prev => ({
          ...prev,
          [jobId]: { tracking_id: data.tracking_id, stage: data.stage }
        }));
        return { success: true };
      } else {
        const data = await res.json();
        return { success: false, error: data.detail || 'Failed to track job' };
      }
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  // Untrack a job (Phase 4A)
  const handleUntrackJob = async (jobId) => {
    const trackingInfo = trackedJobs[jobId];
    if (!trackingInfo) return { success: false, error: 'Job not tracked' };

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${apiUrl}/api/tracked/${trackingInfo.tracking_id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (res.ok) {
        // Remove from cache
        setTrackedJobs(prev => {
          const updated = { ...prev };
          delete updated[jobId];
          return updated;
        });
        return { success: true };
      } else {
        const data = await res.json();
        return { success: false, error: data.detail || 'Failed to untrack job' };
      }
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  // Fetch jobs list (optionally filtered by search query)
  const fetchJobs = useCallback(async (query = null) => {
    // Use isSearching for search requests, loading for initial load
    if (query !== null) {
      setIsSearching(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Not authenticated');
      }

      // Build URL with optional query parameter
      let url = `${apiUrl}/api/jobs`;
      if (query && query.trim().length >= 2) {
        url += `?q=${encodeURIComponent(query.trim())}`;
      }

      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to fetch jobs');
      }

      const data = await res.json();
      setCompanies(data.companies || []);
      setTotalReady(data.total_ready || 0);
      // Normalize whitespace: trim and collapse internal whitespace/newlines to single space
      const normalizedQuery = data.query?.trim().replace(/\s+/g, ' ') || null;
      setActiveQuery(normalizedQuery);

      // Store original totals when not searching (for "X/Y" display)
      if (!data.query) {
        const totals = {};
        (data.companies || []).forEach(c => {
          totals[c.name] = c.ready_count;
        });
        setCompanyTotals(totals);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setIsSearching(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchJobs();
    fetchTrackedIds();
  }, [fetchJobs, fetchTrackedIds]);

  // Search handler (Phase 3C)
  const handleSearch = () => {
    if (searchQuery.trim().length >= 2) {
      fetchJobs(searchQuery);
    } else if (searchQuery.trim().length === 0 && activeQuery) {
      // Clear search if input is empty and there was an active query
      fetchJobs();
    }
  };

  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  };

  // Clear search
  const handleClearSearch = () => {
    setSearchQuery('');
    fetchJobs();
  };

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

  // Sync All handler
  const handleSyncAll = async () => {
    setSyncing(true);
    setSyncError(null);
    setSyncResult(null);

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${apiUrl}/api/jobs/sync`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Sync failed');
      }

      const data = await res.json();
      setSyncResult(data);

      // Refresh jobs list after sync
      await fetchJobs();

      // Clear selection if the selected job might have been expired
      setSelectedJobId(null);
      setSelectedJob(null);
    } catch (err) {
      setSyncError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  // Close sync result popup
  const closeSyncResult = () => {
    setSyncResult(null);
    setSyncError(null);
  };

  // Handler for company-level re-extract completion
  const handleCompanyReExtractComplete = useCallback(async (companyName) => {
    // Refresh jobs list to reflect updated extractions
    await fetchJobs();
    // If a job from this company is selected, refresh its details
    if (selectedJob && selectedJob.company === companyName) {
      fetchJobDetails(selectedJobId);
    }
  }, [fetchJobs, selectedJob, selectedJobId, fetchJobDetails]);

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
  if (companies.length === 0 && !syncing) {
    return (
      <div className="search-container">
        <div className="search-header">
          <h1>Search Jobs</h1>
          <p>Browse and search your extracted job postings</p>
        </div>

        {/* Top Bar - still show Sync All for empty state */}
        <div className="search-top-bar">
          <div className="search-input-wrapper">
            <input
              type="text"
              placeholder="Search jobs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              onFocus={(e) => e.target.select()}
              disabled={syncing}
            />
            {searchQuery && (
              <button
                className="search-clear-btn"
                onClick={handleClearSearch}
                title="Clear search"
              >
                ×
              </button>
            )}
            {isSearching && <span className="search-spinner" />}
          </div>
          <button
            className="search-btn"
            onClick={handleSearch}
            disabled={syncing || searchQuery.trim().length < 2}
          >
            Search
          </button>
          <button className="sync-all-btn" onClick={handleSyncAll}>
            Sync All
          </button>
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
      {/* Sync Overlay */}
      {syncing && (
        <div className="sync-overlay">
          <div className="sync-overlay-content">
            <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
            <p>Syncing jobs...</p>
            <p className="sync-overlay-subtext">Checking for updates and expired jobs</p>
          </div>
        </div>
      )}

      {/* Sync Result Popup */}
      {(syncResult || syncError) && (
        <div className="sync-popup-overlay" onClick={closeSyncResult}>
          <div className="sync-popup" onClick={(e) => e.stopPropagation()}>
            {syncError ? (
              <>
                <div className="sync-popup-header error">
                  <span className="sync-popup-icon">✗</span>
                  <h3>Sync Failed</h3>
                </div>
                <div className="sync-popup-body">
                  <p className="sync-error-message">{syncError}</p>
                </div>
              </>
            ) : (
              <>
                <div className="sync-popup-header">
                  <span className="sync-popup-icon">✓</span>
                  <h3>Sync Complete</h3>
                </div>
                <div className="sync-popup-body">
                  <table className="sync-results-table">
                    <thead>
                      <tr>
                        <th>Company</th>
                        <th>Found</th>
                        <th>Existing</th>
                        <th>New</th>
                        <th>Expired</th>
                      </tr>
                    </thead>
                    <tbody>
                      {syncResult.companies.map((c) => (
                        <tr key={c.company} className={c.error ? 'error-row' : ''}>
                          <td className="company-name">{c.company}</td>
                          <td>{c.error ? '-' : c.found}</td>
                          <td>{c.error ? '-' : c.existing}</td>
                          <td className={c.new > 0 ? 'highlight-new' : ''}>{c.error ? '-' : c.new}</td>
                          <td className={c.expired > 0 ? 'highlight-expired' : ''}>{c.error ? '-' : c.expired}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td><strong>Total</strong></td>
                        <td><strong>{syncResult.total_found}</strong></td>
                        <td><strong>{syncResult.total_existing}</strong></td>
                        <td className={syncResult.total_new > 0 ? 'highlight-new' : ''}><strong>{syncResult.total_new}</strong></td>
                        <td className={syncResult.total_expired > 0 ? 'highlight-expired' : ''}><strong>{syncResult.total_expired}</strong></td>
                      </tr>
                    </tfoot>
                  </table>
                  {syncResult.companies.some(c => c.error) && (
                    <div className="sync-errors">
                      {syncResult.companies.filter(c => c.error).map(c => (
                        <p key={c.company} className="sync-company-error">
                          <strong>{c.company}:</strong> {c.error}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
            <div className="sync-popup-footer">
              <button className="sync-popup-close" onClick={closeSyncResult}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="search-header">
        <h1>Search Jobs</h1>
        <p>Browse and search your extracted job postings</p>
      </div>

      {/* Top Bar - Search + Sync All */}
      <div className="search-top-bar">
        <div className="search-input-wrapper">
          <input
            type="text"
            placeholder="Search jobs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            onFocus={(e) => e.target.select()}
            disabled={syncing}
          />
          {searchQuery && (
            <button
              className="search-clear-btn"
              onClick={handleClearSearch}
              title="Clear search"
            >
              ×
            </button>
          )}
          {isSearching && <span className="search-spinner" />}
        </div>
        <button
          className="search-btn"
          onClick={handleSearch}
          disabled={syncing || searchQuery.trim().length < 2}
        >
          Search
        </button>
        <button
          className="sync-all-btn"
          onClick={handleSyncAll}
          disabled={syncing}
        >
          {syncing ? 'Syncing...' : 'Sync All'}
        </button>
      </div>

      {/* Search Status */}
      {activeQuery && (
        <div className="search-status">
          <span>Showing results for "<strong>{activeQuery}</strong>"</span>
          <button className="search-status-clear" onClick={handleClearSearch}>Clear</button>
        </div>
      )}

      {/* Main Content - 1:3 Layout */}
      <div className="search-main">
        {/* Left Column - Companies */}
        <div className="companies-column">
          {companies.map((company) => (
            <CompanyCard
              key={company.name}
              company={company}
              totalCount={companyTotals[company.name] || company.ready_count}
              selectedJobId={selectedJobId}
              onJobSelect={handleJobSelect}
              apiUrl={apiUrl}
              onReExtractComplete={handleCompanyReExtractComplete}
              trackedJobs={trackedJobs}
            />
          ))}
        </div>

        {/* Right Column - Job Details */}
        <JobDetails
          job={selectedJob}
          loading={jobLoading}
          onReExtract={(jobId) => fetchJobDetails(jobId)}
          trackingInfo={selectedJob ? trackedJobs[selectedJob.id] : null}
          onTrack={handleTrackJob}
          onUntrack={handleUntrackJob}
        />
      </div>

      {/* Footer - Total Count */}
      <div className="search-footer">
        Total: {totalReady} ready {totalReady === 1 ? 'job' : 'jobs'}
      </div>
    </div>
  );
}

export default SearchPage;
