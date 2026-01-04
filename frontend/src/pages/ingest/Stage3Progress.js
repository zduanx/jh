import React, { useState, useEffect, useRef, useCallback } from 'react';
import './Stage3Progress.css';

/**
 * Stage 3: Ingestion Progress
 *
 * Layout:
 * - Header row: Run ID (left) | Abort button (right)
 * - Status section: Current run status with SSE updates
 * - Log Viewer: Real-time CloudWatch logs (polling every 3s)
 */
function Stage3Progress({ runId, onAbort, onTerminal, onNewRun, isCompleted = false }) {
  const [aborting, setAborting] = useState(false);
  const [abortError, setAbortError] = useState(null);

  // SSE progress state
  const [progress, setProgress] = useState({
    status: 'pending',
    total_jobs: null,
    jobs_ready: 0,
    jobs_skipped: 0,
    jobs_expired: 0,
    jobs_failed: 0,
    error_message: null,
  });
  const [sseConnected, setSseConnected] = useState(false);

  // Log viewer state
  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState(null);
  const logContainerRef = useRef(null);
  const lastTimestampRef = useRef(null);
  const pollingRef = useRef(null);

  const apiUrl = process.env.REACT_APP_API_URL;

  // SSE connection for progress updates
  useEffect(() => {
    if (!runId) return;

    const token = localStorage.getItem('access_token');
    const eventSource = new EventSource(
      `${apiUrl}/api/ingestion/progress/${runId}?token=${token}`
    );

    eventSource.onopen = () => {
      setSseConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          console.error('SSE error:', data.error);
          eventSource.close();
          return;
        }
        setProgress(data);

        // If terminal status, close connection and notify parent
        if (['finished', 'error', 'aborted'].includes(data.status)) {
          eventSource.close();
          onTerminal && onTerminal(data.status);
        }
      } catch (err) {
        console.error('Failed to parse SSE data:', err);
      }
    };

    eventSource.onerror = () => {
      setSseConnected(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [runId, apiUrl, onTerminal]);

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

        // Auto-scroll to bottom
        if (logContainerRef.current) {
          setTimeout(() => {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
          }, 50);
        }
      }

      setLogsError(null);
    } catch (err) {
      setLogsError(err.message);
    } finally {
      setLogsLoading(false);
    }
  }, [runId, apiUrl]);

  // Poll for logs every 3 seconds while run is active
  useEffect(() => {
    if (!runId) return;

    // Initial fetch
    fetchLogs();

    // Poll every 3 seconds
    pollingRef.current = setInterval(() => {
      // Stop polling if run is finished
      if (['finished', 'error', 'aborted'].includes(progress.status)) {
        clearInterval(pollingRef.current);
        return;
      }
      fetchLogs();
    }, 3000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [runId, fetchLogs, progress.status]);

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

  const isTerminal = ['finished', 'error', 'aborted'].includes(progress.status);

  // Get summary icon and message based on status
  const getSummaryContent = () => {
    switch (progress.status) {
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

  return (
    <div className="stage-content">
      {/* Summary Banner - only shown in Stage 4 (isCompleted) */}
      {isCompleted && summaryContent && (
        <div className={`s3-summary-banner ${summaryContent.className}`}>
          <div className="s3-summary-icon">{summaryContent.icon}</div>
          <div className="s3-summary-content">
            <h2 className="s3-summary-title">{summaryContent.title}</h2>
            <div className="s3-summary-stats">
              {progress.jobs_ready > 0 && <span>{progress.jobs_ready} jobs ready</span>}
              {progress.jobs_expired > 0 && <span>{progress.jobs_expired} expired</span>}
              {progress.jobs_failed > 0 && <span>{progress.jobs_failed} failed</span>}
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

      {/* Status Row */}
      <div className="s3-status-row">
        <span className="s3-status-label">Status:</span>
        <span className={`s3-status-value ${getStatusClass(progress.status)}`}>
          {progress.status}
        </span>
        {progress.total_jobs !== null && (
          <span className="s3-status-jobs">
            {progress.jobs_ready}/{progress.total_jobs} jobs ready
          </span>
        )}
        {progress.jobs_expired > 0 && (
          <span className="s3-status-expired">
            ({progress.jobs_expired} expired)
          </span>
        )}
      </div>

      {progress.error_message && (
        <div className="s3-error-banner">
          {progress.error_message}
        </div>
      )}

      {/* Log Viewer Section */}
      <div className="s3-section">
        <div className="s3-section-header">
          <span>IngestionWorker Logs</span>
          {logsLoading && <span className="s3-loading-indicator">Loading...</span>}
        </div>
        <div className="s3-log-container" ref={logContainerRef}>
          {logs.length === 0 && !logsLoading && (
            <div className="s3-log-empty">
              Waiting for logs...
            </div>
          )}
          {logsError && (
            <div className="s3-log-error">
              Error: {logsError}
            </div>
          )}
          {logs.map((log, index) => (
            <div key={`${log.timestamp}-${index}`} className="s3-log-entry">
              <span className="s3-log-time">{formatTimestamp(log.timestamp)}</span>
              <span className="s3-log-message">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Stage3Progress;
