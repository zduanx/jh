import React, { useState, useEffect, useRef, useCallback } from 'react';
import './Stage3Progress.css';

/**
 * Stage 3: Ingestion Progress
 *
 * Layout:
 * - Header row: Run ID (left) | Abort button (right)
 * - Status section: Current run status with SSE updates
 * - Jobs by Company: Real-time job-level progress cards
 * - Log Viewer: Real-time CloudWatch logs (polling every 3s)
 *
 * SSE Events:
 * - status: Run status (pending, initializing, finished, error, aborted)
 * - all_jobs: Full job map {company: [{external_id, title, status}, ...]}
 * - update: Diff of changed jobs {company: {external_id: status, ...}}
 * - error: Error message
 */
function Stage3Progress({ runId, onAbort, onTerminal, onNewRun, isCompleted = false }) {
  const [aborting, setAborting] = useState(false);
  const [abortError, setAbortError] = useState(null);

  // SSE progress state
  const [status, setStatus] = useState('pending');
  const [sseError, setSseError] = useState(null);
  const [sseConnected, setSseConnected] = useState(false);

  // Jobs state: {company: [{external_id, title, status}, ...]}
  const [jobs, setJobs] = useState({});
  // Track which company cards are expanded
  const [expandedCompanies, setExpandedCompanies] = useState({});

  // Log viewer state
  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState(null);
  const [logViewMode, setLogViewMode] = useState('merged'); // 'merged' | 'tabs' | 'cards'
  const [activeLogTab, setActiveLogTab] = useState('ingestion'); // For tabs mode
  const logContainerRef = useRef(null);
  const ingestionLogRef = useRef(null);
  const crawlerLogRef = useRef(null);
  const extractorLogRef = useRef(null);
  const lastTimestampRef = useRef(null);
  const pollingRef = useRef(null);

  // Track if user is at bottom of log containers (for smart auto-scroll)
  const isAtBottomRef = useRef({ merged: true, ingestion: true, crawler: true, extractor: true });

  const apiUrl = process.env.REACT_APP_API_URL;

  // Check if a scroll container is at the bottom (within 20px threshold)
  const isScrolledToBottom = (element) => {
    if (!element) return true;
    const threshold = 20;
    return element.scrollHeight - element.scrollTop - element.clientHeight < threshold;
  };

  // Handle scroll events to track user position
  const handleLogScroll = useCallback((containerType) => (e) => {
    isAtBottomRef.current[containerType] = isScrolledToBottom(e.target);
  }, []);

  // Smart auto-scroll: only scroll if user was already at bottom
  const autoScrollIfAtBottom = useCallback((containerRef, containerType) => {
    if (containerRef.current && isAtBottomRef.current[containerType]) {
      setTimeout(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      }, 50);
    }
  }, []);

  // Apply diff updates to jobs state
  const applyJobDiffs = useCallback((diff) => {
    // diff = {company: {external_id: status, ...}}
    setJobs((prevJobs) => {
      const newJobs = { ...prevJobs };
      for (const [company, updates] of Object.entries(diff)) {
        if (newJobs[company]) {
          newJobs[company] = newJobs[company].map((job) => {
            if (updates[job.external_id] !== undefined) {
              return { ...job, status: updates[job.external_id] };
            }
            return job;
          });
        }
      }
      return newJobs;
    });
  }, []);

  // SSE connection for progress updates
  // Uses a reconnect counter to trigger re-connection when server closes stream
  const [reconnectCount, setReconnectCount] = useState(0);

  useEffect(() => {
    if (!runId) return;

    const token = localStorage.getItem('access_token');
    const eventSource = new EventSource(
      `${apiUrl}/api/ingestion/progress/${runId}?token=${token}`
    );

    let isTerminalStatus = false;

    eventSource.onopen = () => {
      console.log('SSE connected');
      setSseConnected(true);
      setSseError(null);
    };

    // Handle 'status' event: pending, initializing, finished, error, aborted
    eventSource.addEventListener('status', (event) => {
      const newStatus = event.data;
      setStatus(newStatus);

      // If terminal status, close connection and notify parent
      if (['finished', 'error', 'aborted'].includes(newStatus)) {
        isTerminalStatus = true;
        eventSource.close();
        setSseConnected(false);
        onTerminal && onTerminal(newStatus);
      }
    });

    // Handle 'all_jobs' event: full job map on first poll/reconnect
    eventSource.addEventListener('all_jobs', (event) => {
      try {
        const jobsData = JSON.parse(event.data);
        setJobs(jobsData);
      } catch (err) {
        console.error('Failed to parse all_jobs:', err);
      }
    });

    // Handle 'update' event: diff of changed job statuses
    eventSource.addEventListener('update', (event) => {
      try {
        const diff = JSON.parse(event.data);
        applyJobDiffs(diff);
      } catch (err) {
        console.error('Failed to parse update:', err);
      }
    });

    // Handle 'error' event from server
    eventSource.addEventListener('error', (event) => {
      // Check if this is a server-sent error event (has data) or connection error
      if (event.data) {
        setSseError(event.data);
        eventSource.close();
        setSseConnected(false);
      }
    });

    // Handle 'reconnect' event - server closing due to timeout, should reconnect
    eventSource.addEventListener('reconnect', () => {
      console.log('SSE received reconnect signal, reconnecting in 1s...');
      eventSource.close();
      setSseConnected(false);
      setTimeout(() => {
        setReconnectCount((c) => c + 1);
      }, 1000);
    });

    // Handle connection errors and reconnection
    eventSource.onerror = () => {
      console.log('SSE connection error, readyState:', eventSource.readyState);
      setSseConnected(false);

      // If connection closed and not terminal, schedule reconnect
      if (eventSource.readyState === EventSource.CLOSED && !isTerminalStatus) {
        console.log('SSE connection closed, will reconnect in 1s...');
        setTimeout(() => {
          setReconnectCount((c) => c + 1);
        }, 1000);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [runId, apiUrl, onTerminal, applyJobDiffs, reconnectCount]);

  // Fetch logs from CloudWatch
  const fetchLogs = useCallback(async () => {
    if (!runId) return;

    const token = localStorage.getItem('access_token');
    const params = new URLSearchParams({ token });

    // If we have previous logs, only fetch new ones
    if (lastTimestampRef.current) {
      params.append('start_time', lastTimestampRef.current + 1);
    }

    try {
      setLogsLoading(true);
      const response = await fetch(
        `${apiUrl}/api/ingestion/logs/${runId}?${params.toString()}`
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to fetch logs');
      }

      const data = await response.json();

      if (data.logs && data.logs.length > 0) {
        // Append new logs
        setLogs((prevLogs) => [...prevLogs, ...data.logs]);

        // Track last timestamp for next poll
        const lastLog = data.logs[data.logs.length - 1];
        lastTimestampRef.current = lastLog.timestamp;

        // Smart auto-scroll: only scroll if user was already at bottom
        autoScrollIfAtBottom(logContainerRef, 'merged');
        autoScrollIfAtBottom(ingestionLogRef, 'ingestion');
        autoScrollIfAtBottom(crawlerLogRef, 'crawler');
        autoScrollIfAtBottom(extractorLogRef, 'extractor');
      }

      setLogsError(null);
    } catch (err) {
      setLogsError(err.message);
    } finally {
      setLogsLoading(false);
    }
  }, [runId, apiUrl, autoScrollIfAtBottom]);

  // Track if we've done a final fetch after terminal status
  const finalFetchDoneRef = useRef(false);

  // Poll for logs every 3 seconds while run is active
  useEffect(() => {
    if (!runId) return;

    const isTerminalStatus = ['finished', 'error', 'aborted'].includes(status);

    // If terminal and we haven't done final fetch, do it now
    if (isTerminalStatus && !finalFetchDoneRef.current) {
      finalFetchDoneRef.current = true;
      // Delay slightly to allow CloudWatch to ingest final logs
      setTimeout(() => fetchLogs(), 1000);
      return;
    }

    // Don't start polling if already terminal
    if (isTerminalStatus) return;

    // Initial fetch
    fetchLogs();

    // Poll every 3 seconds
    pollingRef.current = setInterval(() => {
      fetchLogs();
    }, 3000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [runId, fetchLogs, status]);

  const handleAbort = async () => {
    if (aborting) return;

    setAborting(true);
    setAbortError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${apiUrl}/api/ingestion/abort/${runId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to abort');
      }

      const data = await response.json();
      if (data.success) {
        onAbort();
      } else {
        setAbortError(data.message);
      }
    } catch (err) {
      setAbortError(err.message);
    } finally {
      setAborting(false);
    }
  };

  // Format timestamp for display
  const formatTimestamp = (ts) => {
    const date = new Date(ts);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Get status class for styling
  const getStatusClass = (status) => {
    switch (status) {
      case 'pending':
        return 's3-status-pending';
      case 'initializing':
        return 's3-status-initializing';
      case 'ingesting':
        return 's3-status-ingesting';
      case 'finished':
        return 's3-status-finished';
      case 'error':
        return 's3-status-error';
      case 'aborted':
        return 's3-status-aborted';
      default:
        return '';
    }
  };

  const isTerminal = ['finished', 'error', 'aborted'].includes(status);

  // Compute job counts from jobs state
  const jobCounts = React.useMemo(() => {
    let total = 0;
    let ready = 0;
    let pending = 0;
    let error = 0;
    let expired = 0;
    let skipped = 0;

    for (const companyJobs of Object.values(jobs)) {
      for (const job of companyJobs) {
        total++;
        switch (job.status) {
          case 'ready': ready++; break;
          case 'pending': pending++; break;
          case 'error': error++; break;
          case 'expired': expired++; break;
          case 'skipped': skipped++; break;
          default: break;
        }
      }
    }

    // done = all terminal statuses (not pending)
    const done = ready + error + expired + skipped;

    return { total, ready, pending, error, expired, skipped, done };
  }, [jobs]);

  // Get summary icon and message based on status
  const getSummaryContent = () => {
    switch (status) {
      case 'finished':
        return { icon: '✓', title: 'Ingestion Complete', className: 's3-summary-success' };
      case 'error':
        return { icon: '✗', title: 'Ingestion Failed', className: 's3-summary-error' };
      case 'aborted':
        return { icon: '⊘', title: 'Ingestion Aborted', className: 's3-summary-aborted' };
      default:
        return null;
    }
  };

  const summaryContent = isCompleted ? getSummaryContent() : null;

  // Get job status class for styling
  const getJobStatusClass = (jobStatus) => {
    switch (jobStatus) {
      case 'pending': return 's3-job-pending';
      case 'ready': return 's3-job-ready';
      case 'error': return 's3-job-error';
      case 'expired': return 's3-job-expired';
      case 'skipped': return 's3-job-skipped';
      default: return '';
    }
  };

  return (
    <div className="stage-content">
      {/* Summary Banner - only shown in Stage 4 (isCompleted) */}
      {isCompleted && summaryContent && (
        <div className={`s3-summary-banner ${summaryContent.className}`}>
          <div className="s3-summary-icon">{summaryContent.icon}</div>
          <div className="s3-summary-content">
            <h2 className="s3-summary-title">{summaryContent.title}</h2>
            <div className="s3-summary-stats">
              {jobCounts.ready > 0 && <span>{jobCounts.ready} jobs ready</span>}
              {jobCounts.expired > 0 && <span>{jobCounts.expired} expired</span>}
              {jobCounts.error > 0 && <span>{jobCounts.error} failed</span>}
            </div>
          </div>
          {onNewRun && (
            <button className="s3-new-run-btn" onClick={onNewRun}>
              Start New Run
            </button>
          )}
        </div>
      )}

      {/* Header with Run ID and Abort */}
      <div className="s3-header">
        <div className="s3-run-info">
          <span className="s3-run-label">Run ID:</span>
          <span className="s3-run-id">{runId}</span>
          {sseConnected && !isCompleted && <span className="s3-connected-badge">Live</span>}
        </div>
        {!isTerminal && !isCompleted && (
          <button
            className="s3-abort-btn"
            onClick={handleAbort}
            disabled={aborting}
          >
            {aborting ? 'Aborting...' : 'Abort'}
          </button>
        )}
      </div>

      {abortError && (
        <div className="s3-error-banner">
          {abortError}
          <button onClick={() => setAbortError(null)}>Dismiss</button>
        </div>
      )}

      {sseError && (
        <div className="s3-error-banner">
          SSE Error: {sseError}
        </div>
      )}

      {/* Status Row */}
      <div className="s3-status-row">
        <span className="s3-status-label">Status:</span>
        <span className={`s3-status-value ${getStatusClass(status)}`}>
          {status}
        </span>
        {jobCounts.total > 0 && (
          <span className="s3-status-jobs">
            {jobCounts.done}/{jobCounts.total} done
          </span>
        )}
        {jobCounts.ready > 0 && (
          <span className="s3-status-detail s3-status-ready">
            {jobCounts.ready} ready
          </span>
        )}
        {jobCounts.skipped > 0 && (
          <span className="s3-status-detail s3-status-skipped">
            {jobCounts.skipped} skipped
          </span>
        )}
        {jobCounts.error > 0 && (
          <span className="s3-status-detail s3-status-error-count">
            {jobCounts.error} error
          </span>
        )}
      </div>

      {/* Jobs by Company Section */}
      {Object.keys(jobs).length > 0 && (
        <div className="s3-section">
          <div className="s3-section-header">
            <span>Jobs by Company</span>
            <span className="s3-jobs-summary">
              {jobCounts.done}/{jobCounts.total} done
            </span>
          </div>
          <div className="s3-companies-grid">
            {Object.entries(jobs).map(([company, companyJobs]) => {
              const companyCounts = {
                total: companyJobs.length,
                ready: companyJobs.filter(j => j.status === 'ready').length,
                pending: companyJobs.filter(j => j.status === 'pending').length,
                error: companyJobs.filter(j => j.status === 'error').length,
                expired: companyJobs.filter(j => j.status === 'expired').length,
              };
              const progressPct = companyCounts.total > 0
                ? Math.round((companyCounts.ready / companyCounts.total) * 100)
                : 0;

              const isExpanded = expandedCompanies[company];
              const displayJobs = isExpanded ? companyJobs : companyJobs.slice(0, 5);
              const hasMore = companyJobs.length > 5;

              return (
                <div key={company} className="s3-company-card">
                  <div className="s3-company-header">
                    <span className="s3-company-name">{company}</span>
                    <span className="s3-company-count">
                      {companyCounts.ready}/{companyCounts.total}
                    </span>
                  </div>
                  <div className="s3-company-progress-bar">
                    <div
                      className="s3-company-progress-fill"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                  <div className="s3-company-jobs">
                    {displayJobs.map((job) => (
                      <div
                        key={job.external_id}
                        className={`s3-job-item ${getJobStatusClass(job.status)}`}
                        title={`${job.title} (${job.status})`}
                      >
                        <span className="s3-job-title">{job.title || job.external_id}</span>
                        <span className="s3-job-status">{job.status}</span>
                      </div>
                    ))}
                    {hasMore && (
                      <button
                        className="s3-job-more-btn"
                        onClick={() => setExpandedCompanies(prev => ({
                          ...prev,
                          [company]: !prev[company]
                        }))}
                      >
                        {isExpanded ? 'Show less' : `+${companyJobs.length - 5} more`}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Log Viewer Section */}
      <div className="s3-section">
        <div className="s3-section-header">
          <span>Worker Logs</span>
          <div className="s3-log-controls">
            {logsLoading && <span className="s3-loading-indicator">Loading...</span>}
            <div className="s3-log-mode-toggle">
              <button
                className={`s3-log-mode-btn ${logViewMode === 'merged' ? 'active' : ''}`}
                onClick={() => setLogViewMode('merged')}
                title="Merged view - all logs sorted by time"
              >
                Merged
              </button>
              <button
                className={`s3-log-mode-btn ${logViewMode === 'tabs' ? 'active' : ''}`}
                onClick={() => setLogViewMode('tabs')}
                title="Tabs view - switch between workers"
              >
                Tabs
              </button>
              <button
                className={`s3-log-mode-btn ${logViewMode === 'cards' ? 'active' : ''}`}
                onClick={() => setLogViewMode('cards')}
                title="Cards view - side by side"
              >
                Cards
              </button>
            </div>
          </div>
        </div>

        {/* Merged View - all logs sorted by timestamp */}
        {logViewMode === 'merged' && (
          <div className="s3-log-container" ref={logContainerRef} onScroll={handleLogScroll('merged')}>
            {logs.length === 0 && !logsLoading && (
              <div className="s3-log-empty">Waiting for logs...</div>
            )}
            {logsError && <div className="s3-log-error">Error: {logsError}</div>}
            {logs.map((log, index) => (
              <div key={`${log.timestamp}-${index}`} className="s3-log-entry">
                <span className="s3-log-time">{formatTimestamp(log.timestamp)}</span>
                <span className={`s3-log-source s3-log-source-${log.source || 'ingestion'}`}>
                  {log.source === 'crawler' ? 'CRL' : log.source === 'extractor' ? 'EXT' : 'ING'}
                </span>
                <span className="s3-log-message">{log.message}</span>
              </div>
            ))}
          </div>
        )}

        {/* Tabs View - separate tabs per worker */}
        {logViewMode === 'tabs' && (
          <div className="s3-log-tabs-container">
            <div className="s3-log-tabs">
              <button
                className={`s3-log-tab ${activeLogTab === 'ingestion' ? 'active' : ''}`}
                onClick={() => setActiveLogTab('ingestion')}
              >
                <span className="s3-log-source s3-log-source-ingestion">ING</span>
                Ingestion
                <span className="s3-log-tab-count">
                  {logs.filter(l => (l.source || 'ingestion') === 'ingestion').length}
                </span>
              </button>
              <button
                className={`s3-log-tab ${activeLogTab === 'crawler' ? 'active' : ''}`}
                onClick={() => setActiveLogTab('crawler')}
              >
                <span className="s3-log-source s3-log-source-crawler">CRL</span>
                Crawler
                <span className="s3-log-tab-count">
                  {logs.filter(l => l.source === 'crawler').length}
                </span>
              </button>
              <button
                className={`s3-log-tab ${activeLogTab === 'extractor' ? 'active' : ''}`}
                onClick={() => setActiveLogTab('extractor')}
              >
                <span className="s3-log-source s3-log-source-extractor">EXT</span>
                Extractor
                <span className="s3-log-tab-count">
                  {logs.filter(l => l.source === 'extractor').length}
                </span>
              </button>
            </div>
            <div className="s3-log-container" ref={logContainerRef} onScroll={handleLogScroll('merged')}>
              {logs.filter(l => (l.source || 'ingestion') === activeLogTab).length === 0 && !logsLoading && (
                <div className="s3-log-empty">No {activeLogTab} logs yet...</div>
              )}
              {logsError && <div className="s3-log-error">Error: {logsError}</div>}
              {logs
                .filter(l => (l.source || 'ingestion') === activeLogTab)
                .map((log, index) => (
                  <div key={`${log.timestamp}-${index}`} className="s3-log-entry">
                    <span className="s3-log-time">{formatTimestamp(log.timestamp)}</span>
                    <span className="s3-log-message">{log.message}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Cards View - side by side */}
        {logViewMode === 'cards' && (
          <div className="s3-log-cards">
            <div className="s3-log-card">
              <div className="s3-log-card-header">
                <span className="s3-log-source s3-log-source-ingestion">ING</span>
                <span>Ingestion Worker</span>
                <span className="s3-log-card-count">
                  {logs.filter(l => (l.source || 'ingestion') === 'ingestion').length}
                </span>
              </div>
              <div className="s3-log-container s3-log-card-content" ref={ingestionLogRef} onScroll={handleLogScroll('ingestion')}>
                {logs.filter(l => (l.source || 'ingestion') === 'ingestion').length === 0 && !logsLoading && (
                  <div className="s3-log-empty">Waiting...</div>
                )}
                {logs
                  .filter(l => (l.source || 'ingestion') === 'ingestion')
                  .map((log, index) => (
                    <div key={`${log.timestamp}-${index}`} className="s3-log-entry">
                      <span className="s3-log-time">{formatTimestamp(log.timestamp)}</span>
                      <span className="s3-log-message">{log.message}</span>
                    </div>
                  ))}
              </div>
            </div>
            <div className="s3-log-card">
              <div className="s3-log-card-header">
                <span className="s3-log-source s3-log-source-crawler">CRL</span>
                <span>Crawler Worker</span>
                <span className="s3-log-card-count">
                  {logs.filter(l => l.source === 'crawler').length}
                </span>
              </div>
              <div className="s3-log-container s3-log-card-content" ref={crawlerLogRef} onScroll={handleLogScroll('crawler')}>
                {logs.filter(l => l.source === 'crawler').length === 0 && !logsLoading && (
                  <div className="s3-log-empty">Waiting...</div>
                )}
                {logs
                  .filter(l => l.source === 'crawler')
                  .map((log, index) => (
                    <div key={`${log.timestamp}-${index}`} className="s3-log-entry">
                      <span className="s3-log-time">{formatTimestamp(log.timestamp)}</span>
                      <span className="s3-log-message">{log.message}</span>
                    </div>
                  ))}
              </div>
            </div>
            <div className="s3-log-card">
              <div className="s3-log-card-header">
                <span className="s3-log-source s3-log-source-extractor">EXT</span>
                <span>Extractor Worker</span>
                <span className="s3-log-card-count">
                  {logs.filter(l => l.source === 'extractor').length}
                </span>
              </div>
              <div className="s3-log-container s3-log-card-content" ref={extractorLogRef} onScroll={handleLogScroll('extractor')}>
                {logs.filter(l => l.source === 'extractor').length === 0 && !logsLoading && (
                  <div className="s3-log-empty">Waiting...</div>
                )}
                {logs
                  .filter(l => l.source === 'extractor')
                  .map((log, index) => (
                    <div key={`${log.timestamp}-${index}`} className="s3-log-entry">
                      <span className="s3-log-time">{formatTimestamp(log.timestamp)}</span>
                      <span className="s3-log-message">{log.message}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Stage3Progress;
