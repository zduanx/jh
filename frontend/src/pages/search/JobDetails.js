import React, { useState } from 'react';

function JobDetails({ job, loading, onReExtract, trackingInfo, onTrack, onUntrack }) {
  const [reExtracting, setReExtracting] = useState(false);
  const [reExtractResult, setReExtractResult] = useState(null);
  const [trackingAction, setTrackingAction] = useState(false); // true while track/untrack in progress

  const apiUrl = process.env.REACT_APP_API_URL;

  // Track/Untrack handler (Phase 4A)
  const handleTrackToggle = async () => {
    if (!job || trackingAction) return;

    setTrackingAction(true);
    try {
      if (trackingInfo) {
        // Only allow untrack if stage is "interested"
        if (trackingInfo.stage === 'interested') {
          await onUntrack(job.id);
        }
      } else {
        await onTrack(job.id);
      }
    } finally {
      setTrackingAction(false);
    }
  };

  // Get tracking button text and state
  const getTrackingButton = () => {
    if (!trackingInfo) {
      // Not tracked - show "Interested" to add to tracking
      return { text: 'Interested', canClick: true, className: 'track-btn' };
    }
    if (trackingInfo.stage === 'interested') {
      // Already interested - show "Untrack" to remove
      return { text: 'Untrack', canClick: true, className: 'track-btn tracked interested' };
    }
    // Other stages are read-only
    const stageText = trackingInfo.stage.charAt(0).toUpperCase() + trackingInfo.stage.slice(1);
    return { text: stageText, canClick: false, className: 'track-btn tracked readonly' };
  };

  const handleReExtract = async () => {
    if (!job) return;

    setReExtracting(true);
    setReExtractResult(null);

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${apiUrl}/api/jobs/re-extract`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ job_id: job.id }),
      });

      const data = await res.json();

      if (data.successful > 0 && data.results?.length > 0) {
        const result = data.results[0];
        const descLen = result.description_length || 0;
        const reqLen = result.requirements_length || 0;
        setReExtractResult({
          success: true,
          message: `Re-extracted: ${descLen} desc, ${reqLen} req chars`
        });
        // Notify parent to refresh job details
        if (onReExtract) {
          onReExtract(job.id);
        }
      } else {
        const errorMsg = data.results?.[0]?.error || data.detail || 'Re-extraction failed';
        setReExtractResult({ success: false, message: errorMsg });
      }
    } catch (err) {
      setReExtractResult({ success: false, message: err.message || 'Re-extraction failed' });
    } finally {
      setReExtracting(false);
      // Auto-dismiss result after 5 seconds
      setTimeout(() => setReExtractResult(null), 5000);
    }
  };

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
      <div className={`job-details-content ${trackingInfo ? 'tracked' : ''}`}>
        <div className="job-details-header">
          <div className="job-details-title-row">
            <h2 className="job-details-title">
              <a href={job.url} target="_blank" rel="noopener noreferrer">
                {job.title || 'Untitled Position'}
              </a>
              <span className="external-icon">↗</span>
            </h2>
            <div className="job-details-actions">
              {(() => {
                const btn = getTrackingButton();
                return (
                  <button
                    className={btn.className}
                    onClick={handleTrackToggle}
                    disabled={!btn.canClick || trackingAction}
                  >
                    {trackingAction ? '...' : btn.text}
                  </button>
                );
              })()}
              <button
                className="re-extract-btn"
                onClick={handleReExtract}
                disabled={reExtracting}
              >
                {reExtracting ? 'Re-Extracting...' : 'Re-Extract'}
              </button>
            </div>
          </div>
          <p className="job-details-subtitle">
            ID: {job.id} | {job.company}:{job.external_id}
          </p>
          {reExtractResult && (
            <div className={`re-extract-toast ${reExtractResult.success ? 'success' : 'error'}`}>
              <span className="re-extract-toast-icon">{reExtractResult.success ? '✓' : '✗'}</span>
              <span>{reExtractResult.message}</span>
            </div>
          )}
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

      </div>
    </div>
  );
}

export default JobDetails;
