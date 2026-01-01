import React, { useState } from 'react';
import './Stage3Progress.css';

/**
 * Stage 3: Ingestion Progress
 *
 * Layout:
 * - Header row: Run ID (left) | Abort button (right)
 * - Status section: Current run status (placeholder for SSE)
 * - Details section: Per-job status (placeholder for future)
 */
function Stage3Progress({ runId, onAbort }) {
  const [aborting, setAborting] = useState(false);
  const [abortError, setAbortError] = useState(null);

  const apiUrl = process.env.REACT_APP_API_URL;

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

  return (
    <div className="stage-content">
      {/* Header with Run ID and Abort */}
      <div className="s3-header">
        <div className="s3-run-info">
          <span className="s3-run-label">Run ID:</span>
          <span className="s3-run-id">{runId}</span>
        </div>
        <button
          className="s3-abort-btn"
          onClick={handleAbort}
          disabled={aborting}
        >
          {aborting ? 'Aborting...' : 'Abort'}
        </button>
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
        <span className="s3-status-value s3-status-pending">Pending</span>
        <span className="s3-status-hint">(SSE not connected)</span>
      </div>

      {/* Details Section */}
      <div className="s3-section">
        <div className="s3-section-header">Details</div>
        <div className="s3-details-placeholder">
          <div className="s3-placeholder-icon">📋</div>
          <p>Job details will appear here</p>
          <p className="s3-placeholder-hint">Per-job status breakdown coming soon</p>
        </div>
      </div>
    </div>
  );
}

export default Stage3Progress;
