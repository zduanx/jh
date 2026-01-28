import React, { useState, useEffect, useCallback } from 'react';
import TrackedJobCard from './TrackedJobCard';
import CalendarView from './CalendarView';
import './TrackPage.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * TrackPage - View and manage tracked jobs.
 *
 * Features:
 * - Two tabs: Calendar (placeholder), Manage (active)
 * - Jobs grouped by company
 * - Archived section at bottom
 * - Archive/unarchive/delete with confirmation modals
 * - Event management (create, update, delete)
 */
function TrackPage() {
  const [activeTab, setActiveTab] = useState('manage');
  const [trackedJobs, setTrackedJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Modal state
  const [modal, setModal] = useState({
    isOpen: false,
    type: null, // 'archive' | 'unarchive' | 'delete'
    trackingId: null,
    jobTitle: '',
  });

  // Fetch tracked jobs
  const fetchTrackedJobs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/api/tracked`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch tracked jobs');
      }

      const data = await response.json();
      setTrackedJobs(data.tracked_jobs || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTrackedJobs();
  }, [fetchTrackedJobs]);

  // Group jobs by company - returns { company: { jobs: [], logoUrl: string } }
  const groupJobsByCompany = (jobs) => {
    const groups = {};
    jobs.forEach((tracking) => {
      const company = tracking.job.company;
      if (!groups[company]) {
        groups[company] = {
          jobs: [],
          logoUrl: tracking.job.company_logo_url || null,
        };
      }
      groups[company].jobs.push(tracking);
    });
    return groups;
  };

  // Separate active and archived jobs, both grouped by company
  const activeJobs = trackedJobs.filter((t) => !t.is_archived);
  const archivedJobs = trackedJobs.filter((t) => t.is_archived);
  const groupedActive = groupJobsByCompany(activeJobs);
  const groupedArchived = groupJobsByCompany(archivedJobs);

  // Modal handlers
  const openModal = (type, trackingId, jobTitle) => {
    setModal({ isOpen: true, type, trackingId, jobTitle });
  };

  const closeModal = () => {
    setModal({ isOpen: false, type: null, trackingId: null, jobTitle: '' });
  };

  // API actions
  const updateTracking = async (trackingId, updates) => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_URL}/api/tracked/${trackingId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Failed to update tracking');
    }

    return response.json();
  };

  const deleteTracking = async (trackingId) => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_URL}/api/tracked/${trackingId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Failed to delete tracking');
    }

    return response.json();
  };

  // Event API actions
  const createEvent = async (trackingId, eventData) => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_URL}/api/tracked/${trackingId}/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(eventData),
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Failed to create event');
    }

    return response.json();
  };

  const updateEvent = async (trackingId, eventId, eventData) => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_URL}/api/tracked/${trackingId}/events/${eventId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(eventData),
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Failed to update event');
    }

    return response.json();
  };

  const deleteEvent = async (trackingId, eventId) => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_URL}/api/tracked/${trackingId}/events/${eventId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Failed to delete event');
    }

    return response.json();
  };

  const handleConfirmAction = async () => {
    if (!modal.trackingId) return;

    setActionInProgress(true);
    try {
      if (modal.type === 'archive') {
        await updateTracking(modal.trackingId, { is_archived: true });
      } else if (modal.type === 'unarchive') {
        await updateTracking(modal.trackingId, { is_archived: false });
      } else if (modal.type === 'delete') {
        await deleteTracking(modal.trackingId);
      }

      // Refresh the list
      await fetchTrackedJobs();
      closeModal();
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  // Card action handlers (open confirmation modal)
  const handleArchive = (trackingId) => {
    const tracking = trackedJobs.find((t) => t.id === trackingId);
    openModal('archive', trackingId, tracking?.job?.title || 'this job');
  };

  const handleUnarchive = (trackingId) => {
    const tracking = trackedJobs.find((t) => t.id === trackingId);
    openModal('unarchive', trackingId, tracking?.job?.title || 'this job');
  };

  const handleDelete = (trackingId) => {
    const tracking = trackedJobs.find((t) => t.id === trackingId);
    openModal('delete', trackingId, tracking?.job?.title || 'this job');
  };

  // Handler for updating tracking metadata (used by JobMetadataInputs)
  const handleUpdateTracking = async (trackingId, updates) => {
    await updateTracking(trackingId, updates);
    // Update local state to reflect changes (deep merge for stages)
    setTrackedJobs((prev) =>
      prev.map((t) => {
        if (t.id !== trackingId) return t;

        // Deep merge notes, especially stages
        const existingNotes = t.notes || {};
        const newNotes = updates.notes || {};
        const mergedNotes = { ...existingNotes, ...newNotes };

        // If both have stages, merge them instead of replacing
        if (existingNotes.stages && newNotes.stages) {
          mergedNotes.stages = { ...existingNotes.stages, ...newNotes.stages };
        }

        return { ...t, notes: mergedNotes };
      })
    );
  };

  // Handler for creating events - updates local state instead of refetching
  const handleCreateEvent = async (trackingId, eventData) => {
    const newEvent = await createEvent(trackingId, eventData);

    // Update local state - note is now JSONB on the event itself
    setTrackedJobs((prev) =>
      prev.map((t) => {
        if (t.id !== trackingId) return t;

        // Mark all existing events as not deletable, add new event
        const updatedEvents = t.events.map((e) => ({ ...e, is_deletable: false }));
        updatedEvents.push({
          id: newEvent.id,
          event_type: newEvent.event_type,
          event_date: newEvent.event_date,
          event_time: newEvent.event_time,
          location: newEvent.location,
          note: newEvent.note, // JSONB containing all stage data
          is_deletable: true,
        });

        return {
          ...t,
          stage: newEvent.event_type, // Stage updates to match new event type
          events: updatedEvents,
        };
      })
    );

    return newEvent;
  };

  // Handler for updating events - updates local state instead of refetching
  const handleUpdateEvent = async (trackingId, eventId, eventData) => {
    const updatedEvent = await updateEvent(trackingId, eventId, eventData);

    // Update local state - note is now JSONB on the event itself
    setTrackedJobs((prev) =>
      prev.map((t) => {
        if (t.id !== trackingId) return t;

        const updatedEvents = t.events.map((e) =>
          e.id === eventId
            ? {
                ...e,
                event_date: updatedEvent.event_date,
                event_time: updatedEvent.event_time,
                location: updatedEvent.location,
                note: updatedEvent.note, // JSONB containing all stage data
                is_deletable: updatedEvent.is_deletable,
              }
            : e
        );

        return { ...t, events: updatedEvents };
      })
    );

    return updatedEvent;
  };

  // Handler for deleting events (rollback) - updates local state instead of refetching
  const handleDeleteEvent = async (trackingId, eventId) => {
    const result = await deleteEvent(trackingId, eventId);

    // Update local state
    setTrackedJobs((prev) =>
      prev.map((t) => {
        if (t.id !== trackingId) return t;

        // Remove deleted event
        const updatedEvents = t.events
          .filter((e) => e.id !== eventId)
          .map((e) => ({
            ...e,
            // Mark the next deletable event
            is_deletable: result.next_deletable_event?.id === e.id,
          }));

        return {
          ...t,
          stage: result.new_stage,
          events: updatedEvents,
        };
      })
    );

    return result;
  };

  // Handler for marking as rejected - uses handleCreateEvent for consistency
  const handleReject = async (trackingId, rejectionData) => {
    await handleCreateEvent(trackingId, {
      event_type: 'rejected',
      event_date: rejectionData.datetime,
      note: rejectionData.note,
    });
  };

  // Handler for uploading resume - uses presigned URL for direct S3 upload
  const handleUploadResume = async (trackingId, file) => {
    const token = localStorage.getItem('access_token');

    // Step 1: Get presigned upload URL from backend
    const urlResponse = await fetch(
      `${API_URL}/api/tracked/${trackingId}/resume/upload-url`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!urlResponse.ok) {
      const data = await urlResponse.json();
      throw new Error(data.detail || 'Failed to get upload URL');
    }

    const { upload_url, s3_key } = await urlResponse.json();

    // Step 2: Upload file directly to S3 using presigned URL
    const uploadResponse = await fetch(upload_url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/pdf',
      },
      body: file,
    });

    if (!uploadResponse.ok) {
      throw new Error('Failed to upload file to S3');
    }

    // Step 3: Confirm upload with backend to save S3 URL to DB
    const confirmResponse = await fetch(
      `${API_URL}/api/tracked/${trackingId}/resume/confirm`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          s3_key,
          filename: file.name || 'resume.pdf',
        }),
      }
    );

    if (!confirmResponse.ok) {
      const data = await confirmResponse.json();
      throw new Error(data.detail || 'Failed to confirm upload');
    }

    const result = await confirmResponse.json();

    // Update local state
    setTrackedJobs((prev) =>
      prev.map((t) =>
        t.id === trackingId
          ? {
              ...t,
              has_resume: true,
              notes: { ...t.notes, resume_filename: result.resume_filename },
            }
          : t
      )
    );
  };

  // Modal content based on type
  const getModalContent = () => {
    switch (modal.type) {
      case 'archive':
        return {
          title: 'Archive Job',
          message: `Archive "${modal.jobTitle}"? You can unarchive it later.`,
          confirmText: 'Archive',
          confirmClass: 'warning',
        };
      case 'unarchive':
        return {
          title: 'Unarchive Job',
          message: `Move "${modal.jobTitle}" back to active jobs?`,
          confirmText: 'Unarchive',
          confirmClass: '',
        };
      case 'delete':
        return {
          title: 'Delete Job',
          message: `Permanently delete "${modal.jobTitle}" from tracking? This cannot be undone.`,
          confirmText: 'Delete',
          confirmClass: 'danger',
        };
      default:
        return { title: '', message: '', confirmText: '', confirmClass: '' };
    }
  };

  const modalContent = getModalContent();

  // Render content based on tab
  const renderContent = () => {
    if (activeTab === 'calendar') {
      return <CalendarView />;
    }

    // Manage tab
    if (loading) {
      return (
        <div className="trk-loading">
          <div className="trk-spinner"></div>
          <p>Loading tracked jobs...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="trk-error">
          <div className="trk-error-icon">⚠️</div>
          <h3>Error Loading Jobs</h3>
          <p>{error}</p>
          <button className="trk-retry-btn" onClick={fetchTrackedJobs}>
            Try Again
          </button>
        </div>
      );
    }

    if (trackedJobs.length === 0) {
      return (
        <div className="trk-empty">
          <div className="trk-empty-icon">📋</div>
          <h3>No Tracked Jobs</h3>
          <p>Track jobs from the Search page to see them here.</p>
        </div>
      );
    }

    return (
      <>
        {/* Active jobs grouped by company */}
        {Object.entries(groupedActive)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([company, { jobs, logoUrl }]) => (
            <div key={company} className="trk-company-section">
              <div className="trk-company-header">
                <div className="trk-company-icon">
                  {logoUrl ? (
                    <img src={logoUrl} alt={company} />
                  ) : (
                    company.charAt(0)
                  )}
                </div>
                <span className="trk-company-name">{company}</span>
                <span className="trk-company-count">({jobs.length} jobs)</span>
              </div>
              {jobs.map((tracking) => (
                <TrackedJobCard
                  key={tracking.id}
                  tracking={tracking}
                  onArchive={handleArchive}
                  onUnarchive={handleUnarchive}
                  onDelete={handleDelete}
                  onUpdateTracking={handleUpdateTracking}
                  onCreateEvent={handleCreateEvent}
                  onUpdateEvent={handleUpdateEvent}
                  onDeleteEvent={handleDeleteEvent}
                  onReject={handleReject}
                  onUploadResume={handleUploadResume}
                  disabled={actionInProgress}
                />
              ))}
            </div>
          ))}

        {/* Archived section - grouped by company */}
        {archivedJobs.length > 0 && (
          <div className="trk-archived-section">
            <div className="trk-archived-header">
              <h3>Archived ({archivedJobs.length})</h3>
            </div>
            {Object.entries(groupedArchived)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([company, { jobs, logoUrl }]) => (
                <div key={`archived-${company}`} className="trk-company-section archived">
                  <div className="trk-company-header">
                    <div className="trk-company-icon">
                      {logoUrl ? (
                        <img src={logoUrl} alt={company} />
                      ) : (
                        company.charAt(0)
                      )}
                    </div>
                    <span className="trk-company-name">{company}</span>
                    <span className="trk-company-count">({jobs.length})</span>
                  </div>
                  {jobs.map((tracking) => (
                    <TrackedJobCard
                      key={tracking.id}
                      tracking={tracking}
                      onArchive={handleArchive}
                      onUnarchive={handleUnarchive}
                      onDelete={handleDelete}
                      onUpdateTracking={handleUpdateTracking}
                      onCreateEvent={handleCreateEvent}
                      onUpdateEvent={handleUpdateEvent}
                      onDeleteEvent={handleDeleteEvent}
                      onReject={handleReject}
                      onUploadResume={handleUploadResume}
                      disabled={actionInProgress}
                    />
                  ))}
                </div>
              ))}
          </div>
        )}
      </>
    );
  };

  return (
    <div className="trk-page">
      <div className="trk-header">
        <h1>Track</h1>
        <p>Manage your tracked job applications</p>
      </div>

      {/* Tabs */}
      <div className="trk-tabs">
        <button
          className={`trk-tab ${activeTab === 'calendar' ? 'active' : ''}`}
          onClick={() => setActiveTab('calendar')}
        >
          Calendar
        </button>
        <button
          className={`trk-tab ${activeTab === 'manage' ? 'active' : ''}`}
          onClick={() => setActiveTab('manage')}
        >
          Manage
        </button>
      </div>

      {/* Content */}
      <div className="trk-content">{renderContent()}</div>

      {/* Confirmation Modal */}
      {modal.isOpen && (
        <div className="trk-modal-overlay" onClick={closeModal}>
          <div className="trk-modal" onClick={(e) => e.stopPropagation()}>
            <h3>{modalContent.title}</h3>
            <p>{modalContent.message}</p>
            <div className="trk-modal-actions">
              <button
                className="trk-modal-btn cancel"
                onClick={closeModal}
                disabled={actionInProgress}
              >
                Cancel
              </button>
              <button
                className={`trk-modal-btn confirm ${modalContent.confirmClass}`}
                onClick={handleConfirmAction}
                disabled={actionInProgress}
              >
                {actionInProgress ? 'Processing...' : modalContent.confirmText}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TrackPage;
