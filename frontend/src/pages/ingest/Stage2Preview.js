import React, { useState, useEffect, useCallback } from 'react';
import FilterModal from './components/FilterModal';
import './Stage2Preview.css';

/**
 * Normalize filters for consistent comparison:
 * - Sort arrays so order doesn't affect equality
 */
const normalizeFilters = (filters) => {
  const include = filters?.include ? [...filters.include].sort() : [];
  const exclude = filters?.exclude ? [...filters.exclude].sort() : [];
  return { include, exclude };
};

/**
 * Stage 2 Action Bar - rendered separately in IngestPage
 */
export function Stage2ActionBar({
  isDirty,
  saving,
  loading,
  hasResults,
  resultsStale,
  canStartIngestion,
  onBack,
  onSave,
  onDryRun,
  onConfirmOpen,
  onForceConfirmOpen,
}) {
  const canDryRun = !isDirty && !loading && !saving;

  return (
    <>
      <div className="s2-action-bar-left">
        <button className="s2-back-btn" onClick={onBack} disabled={loading || saving}>
          ← Back
        </button>
      </div>

      <div className="s2-action-bar-center">
        {isDirty && (
          <button
            className="s2-save-btn"
            onClick={onSave}
            disabled={saving || loading}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        )}

        <button
          className="s2-dryrun-btn"
          onClick={onDryRun}
          disabled={!canDryRun}
          title={isDirty ? 'Save settings first' : ''}
        >
          {loading ? 'Running...' : hasResults ? 'Rerun' : 'Dry Run'}
        </button>
      </div>

      <div className="s2-action-bar-right">
        <button
          className="s2-force-btn"
          onClick={onForceConfirmOpen}
          disabled={!canStartIngestion}
          title="Force re-crawl all jobs (bypass content check)"
        >
          Force Ingestion
        </button>
        <button
          className="s2-next-btn"
          onClick={onConfirmOpen}
          disabled={!canStartIngestion}
          title={
            !hasResults ? 'Run dry-run first' :
            resultsStale ? 'Rerun dry-run - settings changed' :
            isDirty ? 'Save settings first' : ''
          }
        >
          Start Ingestion →
        </button>
      </div>
    </>
  );
}

/**
 * Stage 2: Preview dry-run results
 *
 * Layout:
 * - Header: "Dry-run Result" card with summary stats
 * - Main: 1:3 columns - company cards (left) | job details (right)
 * - Footer: Back / Save Settings / Dry Run or Rerun / Start Ingestion
 *
 * States:
 * - Dirty (unsaved changes): Save Settings enabled, Dry Run disabled
 * - Clean (saved): Dry Run enabled
 * - Has results & no changes since: Start Ingestion enabled
 */
function Stage2Preview({
  companies,  // Array of { company_name, display_name, logo_url, title_filters } from enabled settings
  savedSettings,  // Full settings array from parent (for save API)
  onSettingsUpdate,  // Callback to update parent settings after save
  onActionBarChange,
  onNext,  // Called when user confirms ingestion start
  startingIngestion = false,  // True while /start API call is in progress
}) {
  // Local editable copy of companies (for filter editing)
  const [localCompanies, setLocalCompanies] = useState([]);
  const [isDirty, setIsDirty] = useState(false);
  const [resultsStale, setResultsStale] = useState(false);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [expandedIncluded, setExpandedIncluded] = useState(false);
  const [expandedExcluded, setExpandedExcluded] = useState(false);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [forceConfirmModalOpen, setForceConfirmModalOpen] = useState(false);

  const apiUrl = process.env.REACT_APP_API_URL;

  // Initialize local companies from props
  useEffect(() => {
    setLocalCompanies(companies.map(c => ({ ...c })));
  }, [companies]);

  // Open edit modal for a company
  const handleEditClick = (e, company) => {
    e.stopPropagation(); // Don't trigger card selection
    setEditingCompany(company);
    setModalOpen(true);
  };

  // Handle modal save (local only - no API call yet)
  const handleModalSave = (filterData) => {
    const newFilters = normalizeFilters(filterData);
    const originalFilters = normalizeFilters(editingCompany.title_filters);

    // Check if filters actually changed (ignore order)
    const filtersChanged =
      JSON.stringify(newFilters) !== JSON.stringify(originalFilters);

    if (!filtersChanged) {
      // No real change, just close modal
      setModalOpen(false);
      setEditingCompany(null);
      return;
    }

    const updatedCompanies = localCompanies.map(c => {
      if (c.company_name === editingCompany.company_name) {
        return {
          ...c,
          title_filters: newFilters,
        };
      }
      return c;
    });
    setLocalCompanies(updatedCompanies);
    setIsDirty(true);
    setResultsStale(true); // Results no longer match current filters
    setModalOpen(false);
    setEditingCompany(null);
  };

  // Save settings to API
  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');

      // Build upsert operations for changed companies
      const operations = localCompanies.map(local => {
        const original = companies.find(c => c.company_name === local.company_name);
        // Check if filters changed (normalized comparison)
        const localNorm = normalizeFilters(local.title_filters);
        const originalNorm = normalizeFilters(original?.title_filters);
        const filtersChanged =
          JSON.stringify(localNorm) !== JSON.stringify(originalNorm);

        if (filtersChanged) {
          return {
            op: 'upsert',
            company_name: local.company_name,
            title_filters: local.title_filters,
            is_enabled: true,
          };
        }
        return null;
      }).filter(Boolean);

      if (operations.length === 0) {
        setIsDirty(false);
        setSaving(false);
        return;
      }

      const res = await fetch(`${apiUrl}/api/ingestion/settings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(operations),
      });

      if (!res.ok) throw new Error('Failed to save settings');

      const results = await res.json();
      const failures = results.filter(r => !r.success);
      if (failures.length > 0) {
        throw new Error(`Failed: ${failures.map(f => f.company_name).join(', ')}`);
      }

      // Update parent savedSettings with new filter values
      const updatedSettings = savedSettings.map(s => {
        const local = localCompanies.find(c => c.company_name === s.company_name);
        if (local) {
          const result = results.find(r => r.company_name === s.company_name);
          return {
            ...s,
            title_filters: local.title_filters,
            updated_at: result?.updated_at || s.updated_at,
          };
        }
        return s;
      });
      onSettingsUpdate(updatedSettings);

      setIsDirty(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }, [apiUrl, companies, localCompanies, savedSettings, onSettingsUpdate]);

  // Run dry-run API call
  const handleDryRun = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${apiUrl}/api/ingestion/dry-run`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Dry run failed');
      }

      const data = await response.json();
      setResults(data);
      setResultsStale(false); // Results are now fresh

      // Auto-select first company with results
      const firstCompany = localCompanies.find(c => data[c.company_name]);
      if (firstCompany) {
        setSelectedCompany(firstCompany.company_name);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, localCompanies]);

  // Calculate summary stats
  const getSummaryStats = () => {
    if (!results) {
      return {
        companyCount: localCompanies.length,
        totalUrls: '--',
        statusText: 'Ready to preview',
      };
    }

    let totalUrls = 0;
    let errorCount = 0;
    let successCount = 0;

    Object.values(results).forEach(result => {
      if (result.status === 'success') {
        totalUrls += result.urls_count || 0;
        successCount++;
      } else {
        errorCount++;
      }
    });

    const statusText = errorCount > 0
      ? `${errorCount} error${errorCount > 1 ? 's' : ''}`
      : 'All successful';

    return {
      companyCount: localCompanies.length,
      totalUrls,
      statusText,
      errorCount,
      successCount,
    };
  };

  // Get status for a company
  const getCompanyStatus = (companyName) => {
    if (!results) return 'pending';
    const result = results[companyName];
    if (!result) return 'pending';
    return result.status; // 'success' or 'error'
  };

  // Get found/excluded counts for a company
  const getCompanyInfo = (companyName) => {
    if (!results) return 'Pending';
    const result = results[companyName];
    if (!result) return 'Pending';
    if (result.status === 'error') return 'Error';
    const included = result.included_jobs?.length || 0;
    const excluded = result.excluded_jobs?.length || 0;
    return `${included} / ${excluded}`;
  };

  // Render the right panel content
  const renderDetailPanel = () => {
    if (!selectedCompany) {
      return (
        <div className="s2-detail-empty">
          <div className="s2-detail-empty-icon">📋</div>
          <p>Select a company to view details</p>
        </div>
      );
    }

    const result = results?.[selectedCompany];

    // No result yet (pending)
    if (!result) {
      return (
        <div className="s2-detail-empty">
          <div className="s2-detail-empty-icon">⏳</div>
          <p>Run dry-run to see results</p>
        </div>
      );
    }

    // Error state
    if (result.status === 'error') {
      return (
        <div className="s2-detail-error">
          <div className="s2-detail-error-header">Error</div>
          <div className="s2-detail-error-message">
            {result.error_message || 'Unknown error occurred'}
          </div>
          <p className="s2-detail-error-hint">
            Try running again or check your network connection.
          </p>
        </div>
      );
    }

    // Success state - show included/excluded columns
    const includedJobs = result.included_jobs || [];
    const excludedJobs = result.excluded_jobs || [];
    const maxDisplay = 10;
    const includedToShow = expandedIncluded ? includedJobs : includedJobs.slice(0, maxDisplay);
    const excludedToShow = expandedExcluded ? excludedJobs : excludedJobs.slice(0, maxDisplay);

    return (
      <div className="s2-detail-content">
        <div className="s2-detail-column">
          <div className="s2-detail-column-header">
            Included ({includedJobs.length})
          </div>
          <div className="s2-detail-jobs">
            {includedToShow.map((job, idx) => (
              <a
                key={idx}
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="s2-job-link"
              >
                <span className="s2-job-title">{job.title}</span>
                {job.location && (
                  <span className="s2-job-location">- {job.location}</span>
                )}
              </a>
            ))}
            {includedJobs.length > maxDisplay && !expandedIncluded && (
              <button
                className="s2-jobs-more"
                onClick={() => setExpandedIncluded(true)}
              >
                ... and {includedJobs.length - maxDisplay} more
              </button>
            )}
            {expandedIncluded && includedJobs.length > maxDisplay && (
              <button
                className="s2-jobs-more"
                onClick={() => setExpandedIncluded(false)}
              >
                Show less
              </button>
            )}
            {includedJobs.length === 0 && (
              <div className="s2-jobs-empty">No jobs included</div>
            )}
          </div>
        </div>

        <div className="s2-detail-column">
          <div className="s2-detail-column-header">
            Excluded ({excludedJobs.length})
          </div>
          <div className="s2-detail-jobs">
            {excludedToShow.map((job, idx) => (
              <a
                key={idx}
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="s2-job-link excluded"
              >
                <span className="s2-job-title">{job.title}</span>
                {job.location && (
                  <span className="s2-job-location">- {job.location}</span>
                )}
              </a>
            ))}
            {excludedJobs.length > maxDisplay && !expandedExcluded && (
              <button
                className="s2-jobs-more"
                onClick={() => setExpandedExcluded(true)}
              >
                ... and {excludedJobs.length - maxDisplay} more
              </button>
            )}
            {expandedExcluded && excludedJobs.length > maxDisplay && (
              <button
                className="s2-jobs-more"
                onClick={() => setExpandedExcluded(false)}
              >
                Show less
              </button>
            )}
            {excludedJobs.length === 0 && (
              <div className="s2-jobs-empty">No jobs excluded</div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const stats = getSummaryStats();
  const hasResults = results !== null;
  const canStartIngestion = hasResults && !resultsStale && !isDirty && !loading;

  // Update action bar state in parent
  useEffect(() => {
    onActionBarChange({
      isDirty,
      saving,
      loading,
      hasResults,
      resultsStale,
      canStartIngestion,
      onSave: handleSave,
      onDryRun: handleDryRun,
      onConfirmOpen: () => setConfirmModalOpen(true),
      onForceConfirmOpen: () => setForceConfirmModalOpen(true),
    });
  }, [isDirty, saving, loading, hasResults, resultsStale, canStartIngestion, onActionBarChange, handleSave, handleDryRun]);

  return (
    <div className="stage-content">
      {error && (
        <div className="s2-error-banner">
          {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {isDirty && (
        <div className="s2-warning-banner">
          You have unsaved changes. Save settings before running dry-run.
        </div>
      )}

      {resultsStale && hasResults && !isDirty && (
        <div className="s2-warning-banner">
          Settings have changed since last dry-run. Please rerun to update results.
        </div>
      )}

      {/* Summary Card */}
      <div className="s2-summary-card">
        <div className="s2-summary-title">Dry-run Result</div>
        <div className="s2-summary-stats">
          <span>{stats.companyCount} companies</span>
          <span className="s2-summary-dot">•</span>
          <span>{stats.totalUrls} Jobs</span>
          <span className="s2-summary-dot">•</span>
          <span className={stats.errorCount > 0 ? 's2-summary-error' : ''}>
            {stats.statusText}
          </span>
        </div>
      </div>

      {/* Main Content: 1:3 columns */}
      <div className="s2-main-layout">
        {/* Left: Company cards */}
        <div className="s2-company-column">
          {localCompanies.map(company => {
            const status = getCompanyStatus(company.company_name);
            const info = getCompanyInfo(company.company_name);
            const isSelected = selectedCompany === company.company_name;

            return (
              <div
                key={company.company_name}
                className={`s2-company-card ${status} ${isSelected ? 'selected' : ''}`}
                onClick={() => {
                  setSelectedCompany(company.company_name);
                  setExpandedIncluded(false);
                  setExpandedExcluded(false);
                }}
              >
                <div className="s2-company-row">
                  <div className="s2-company-status-icon">
                    {status === 'pending' && '⚪'}
                    {status === 'success' && '🟢'}
                    {status === 'error' && '🔴'}
                  </div>
                  <div className="s2-company-info">
                    <img
                      src={company.logo_url}
                      alt={company.display_name}
                      className="s2-company-logo"
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                    <span className="s2-company-name">{company.display_name}</span>
                  </div>
                  <button
                    className="s2-edit-btn"
                    onClick={(e) => handleEditClick(e, company)}
                    title="Edit filters"
                  >
                    ✏️
                  </button>
                  <div className="s2-company-count" title="Found / Excluded">{info}</div>
                </div>
                <div className="s2-company-filters">
                  <div className="s2-filter-line">
                    <span className="s2-filter-label">Include:</span>
                    <span className="s2-filter-value">
                      {company.title_filters?.include?.length > 0
                        ? company.title_filters.include.join(', ')
                        : 'All'}
                    </span>
                  </div>
                  {company.title_filters?.exclude?.length > 0 && (
                    <div className="s2-filter-line">
                      <span className="s2-filter-label">Exclude:</span>
                      <span className="s2-filter-value">
                        {company.title_filters.exclude.join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Detail panel */}
        <div className="s2-detail-column-wrapper">
          {renderDetailPanel()}
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmModalOpen && (
        <div className="s2-confirm-overlay" onClick={() => setConfirmModalOpen(false)}>
          <div className="s2-confirm-modal" onClick={e => e.stopPropagation()}>
            <div className="s2-confirm-header">
              <h3>Start Ingestion?</h3>
              <button
                className="s2-confirm-close"
                onClick={() => setConfirmModalOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="s2-confirm-body">
              <p>You are about to start ingestion for:</p>
              <ul className="s2-confirm-list">
                <li><strong>{stats.companyCount}</strong> {stats.companyCount === 1 ? 'company' : 'companies'}</li>
                <li><strong>{stats.totalUrls}</strong> jobs to process</li>
              </ul>
              <p className="s2-confirm-note">
                This will crawl full job details and may take several minutes.
              </p>
            </div>
            <div className="s2-confirm-footer">
              <button
                className="s2-confirm-cancel"
                onClick={() => setConfirmModalOpen(false)}
                disabled={startingIngestion}
              >
                Cancel
              </button>
              <button
                className="s2-confirm-proceed"
                onClick={() => {
                  onNext(false);
                }}
                disabled={startingIngestion}
              >
                {startingIngestion ? 'Starting...' : 'Start Ingestion'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Force Confirmation Modal */}
      {forceConfirmModalOpen && (
        <div className="s2-confirm-overlay" onClick={() => setForceConfirmModalOpen(false)}>
          <div className="s2-confirm-modal s2-confirm-force" onClick={e => e.stopPropagation()}>
            <div className="s2-confirm-header">
              <h3>Force Ingestion?</h3>
              <button
                className="s2-confirm-close"
                onClick={() => setForceConfirmModalOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="s2-confirm-body">
              <p className="s2-confirm-warning">
                This will re-crawl ALL jobs regardless of content changes.
              </p>
              <ul className="s2-confirm-list">
                <li><strong>{stats.companyCount}</strong> {stats.companyCount === 1 ? 'company' : 'companies'}</li>
                <li><strong>{stats.totalUrls}</strong> jobs to process</li>
              </ul>
              <p className="s2-confirm-note">
                Use this for testing or when you need to re-extract all job details.
              </p>
            </div>
            <div className="s2-confirm-footer">
              <button
                className="s2-confirm-cancel"
                onClick={() => setForceConfirmModalOpen(false)}
                disabled={startingIngestion}
              >
                Cancel
              </button>
              <button
                className="s2-confirm-force-proceed"
                onClick={() => {
                  onNext(true);
                }}
                disabled={startingIngestion}
              >
                {startingIngestion ? 'Starting...' : 'Force Ingestion'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter Modal */}
      {modalOpen && editingCompany && (
        <FilterModal
          company={{
            display_name: editingCompany.display_name,
            logo_url: editingCompany.logo_url,
          }}
          initialFilters={editingCompany.title_filters}
          initialEnabled={true}
          showEnabledToggle={false}
          saveButtonText="Update"
          onSave={handleModalSave}
          onCancel={() => {
            setModalOpen(false);
            setEditingCompany(null);
          }}
        />
      )}
    </div>
  );
}

export default Stage2Preview;
