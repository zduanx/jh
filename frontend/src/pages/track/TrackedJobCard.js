import React, { useState } from 'react';
import { MdExpandMore, MdExpandLess, MdArchive, MdUnarchive, MdDelete } from 'react-icons/md';
import JobMetadataInputs from './JobMetadataInputs';
import ResumeSection from './ResumeSection';
import ProgressStepper from './ProgressStepper';
import StageCard from './StageCard';
import StageCardForm from './StageCardForm';
import RejectModal from './RejectModal';

// Stage workflow order (updated for Phase 4C)
const MAIN_STAGES = ['applied', 'screening', 'interview', 'reference', 'offer'];
const TERMINAL_STAGES = ['accepted', 'declined'];

/**
 * TrackedJobCard - Expandable card for a tracked job.
 *
 * Props:
 * - tracking: { id, job_id, stage, is_archived, notes, events, job: { title, company, company_logo_url, location, description, url } }
 * - onArchive: (trackingId) => void
 * - onUnarchive: (trackingId) => void
 * - onDelete: (trackingId) => void
 * - onUpdateTracking: (trackingId, updates) => Promise - for saving metadata
 * - onCreateEvent: (trackingId, eventData) => Promise - create new event
 * - onUpdateEvent: (trackingId, eventId, eventData) => Promise - update event
 * - onDeleteEvent: (trackingId, eventId) => Promise - delete event
 * - onReject: (trackingId, rejectionData) => Promise - mark as rejected
 * - onUploadResume: (trackingId, file) => Promise - upload resume (re-upload overwrites)
 * - disabled: boolean (when action is in progress)
 */
function TrackedJobCard({
  tracking,
  onArchive,
  onUnarchive,
  onDelete,
  onUpdateTracking,
  onCreateEvent,
  onUpdateEvent,
  onDeleteEvent,
  onReject,
  onUploadResume,
  disabled,
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Form modal state
  const [formModal, setFormModal] = useState({
    isOpen: false,
    stageName: null,
    event: null,
    stageData: null,
  });

  // Reject modal state
  const [rejectModalOpen, setRejectModalOpen] = useState(false);

  const { id, stage, is_archived, notes, events = [], has_resume, job } = tracking;
  const resume_filename = notes?.resume_filename || null;
  const { title, company, company_logo_url, location, description, url } = job;

  const isRejected = stage === 'rejected';
  const isTerminalStage = ['offer', 'accepted', 'declined'].includes(stage);

  const toggleExpand = () => setIsExpanded(!isExpanded);

  const handleArchive = (e) => {
    e.stopPropagation();
    if (onArchive) onArchive(id);
  };

  const handleUnarchive = (e) => {
    e.stopPropagation();
    if (onUnarchive) onUnarchive(id);
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (onDelete) onDelete(id);
  };

  // Build a map of events by type
  const eventsByType = {};
  events.forEach((e) => {
    eventsByType[e.event_type] = e;
  });

  // Get stage data from notes
  const getStageData = (stageName) => {
    return notes?.stages?.[stageName] || null;
  };

  // Determine stage state
  const getStageState = (stageName) => {
    // Completed stages should still show as completed (even if rejected - StageCard handles readonly)
    if (eventsByType[stageName]) return 'completed';

    // If rejected, all non-completed stages are locked
    if (isRejected) return 'locked';

    // Check if this is the next available stage
    const mainIndex = MAIN_STAGES.indexOf(stageName);
    const currentMainIndex = MAIN_STAGES.indexOf(stage);

    // Terminal stages
    if (TERMINAL_STAGES.includes(stageName)) {
      if (eventsByType[stageName]) return 'completed';
      if (eventsByType['offer'] && !eventsByType['accepted'] && !eventsByType['declined']) {
        return 'next';
      }
      return 'locked';
    }

    // If current stage is interested, applied is next
    if (stage === 'interested' && stageName === 'applied') {
      return 'next';
    }

    // Next stage in main flow
    if (mainIndex === currentMainIndex + 1) {
      return 'next';
    }

    // If we're on a terminal stage, nothing else is next
    if (TERMINAL_STAGES.includes(stage)) {
      return 'locked';
    }

    return 'locked';
  };

  // Handle stage click from stepper
  const handleStageClick = (stageName) => {
    const state = getStageState(stageName);
    if (state === 'completed') {
      // Open edit form
      setFormModal({
        isOpen: true,
        stageName,
        event: eventsByType[stageName],
        stageData: getStageData(stageName),
      });
    } else if (state === 'next') {
      // Open add form
      setFormModal({
        isOpen: true,
        stageName,
        event: null,
        stageData: null,
      });
    }
  };

  // Handle stage card add
  const handleStageAdd = (stageName) => {
    setFormModal({
      isOpen: true,
      stageName,
      event: null,
      stageData: null,
    });
  };

  // Handle stage card edit
  const handleStageEdit = (stageName, event, stageData) => {
    setFormModal({
      isOpen: true,
      stageName,
      event,
      stageData,
    });
  };

  // Handle stage card delete (rollback)
  const handleStageDelete = async (eventId) => {
    if (onDeleteEvent) {
      await onDeleteEvent(id, eventId);
    }
  };

  // Handle form save
  const handleFormSave = async (stageName, eventData, stageData, existingEventId) => {
    // Save stage data to notes
    if (stageData && Object.keys(stageData).length > 0) {
      const notesUpdate = {
        stages: {
          ...(notes?.stages || {}),
          [stageName]: stageData,
        },
      };
      await onUpdateTracking(id, { notes: notesUpdate });
    }

    // Create or update event
    if (existingEventId) {
      // Update existing event
      if (onUpdateEvent) {
        await onUpdateEvent(id, existingEventId, {
          event_date: eventData.event_date,
          event_time: eventData.event_time,
          note: eventData.note,
        });
      }
    } else {
      // Create new event
      if (onCreateEvent) {
        await onCreateEvent(id, eventData);
      }
    }
  };

  // Handle rejection
  const handleReject = async (rejectionData) => {
    if (onReject) {
      await onReject(id, rejectionData);
    }
  };

  // Handle undo rejection (delete the rejected event)
  const handleUndoReject = async () => {
    const rejectedEvent = eventsByType['rejected'];
    if (rejectedEvent && onDeleteEvent) {
      await onDeleteEvent(id, rejectedEvent.id);
    }
  };

  // Close form modal
  const closeFormModal = () => {
    setFormModal({ isOpen: false, stageName: null, event: null, stageData: null });
  };

  return (
    <div className={`trk-card ${is_archived ? 'archived' : ''} ${isRejected ? 'rejected' : ''}`}>
      {/* Header - always visible */}
      <div className="trk-card-header">
        <div className="trk-card-main">
          <div className="trk-card-logo">
            {company_logo_url ? (
              <img src={company_logo_url} alt={company} />
            ) : (
              <span>{company.charAt(0)}</span>
            )}
          </div>
          <div className="trk-card-title">
            <a href={url} target="_blank" rel="noopener noreferrer">
              {title || 'Untitled Position'}
            </a>
          </div>
          <div className="trk-card-location">{location || 'Location N/A'}</div>
          <div className={`trk-card-stage ${stage}`}>{stage}</div>
        </div>

        <div className="trk-card-actions">
          {/* Expand/Collapse */}
          <button
            className="trk-action-btn expand"
            onClick={toggleExpand}
            title={isExpanded ? 'Collapse' : 'Expand'}
            disabled={disabled}
          >
            {isExpanded ? <MdExpandLess size={20} /> : <MdExpandMore size={20} />}
          </button>

          {/* Archive / Unarchive */}
          {is_archived ? (
            <button
              className="trk-action-btn unarchive"
              onClick={handleUnarchive}
              title="Unarchive"
              disabled={disabled}
            >
              <MdUnarchive size={18} />
            </button>
          ) : (
            <button
              className="trk-action-btn archive"
              onClick={handleArchive}
              title="Archive"
              disabled={disabled}
            >
              <MdArchive size={18} />
            </button>
          )}

          {/* Delete - only show for "interested" stage */}
          {stage === 'interested' && (
            <button
              className="trk-action-btn delete"
              onClick={handleDelete}
              title="Delete"
              disabled={disabled}
            >
              <MdDelete size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Body - expanded content */}
      {isExpanded && (
        <div className="trk-card-body">
          {/* Job Description */}
          {description && (
            <div className="trk-card-description">
              <h4>Description</h4>
              <p>{description}</p>
            </div>
          )}

          {/* Resume Section */}
          <ResumeSection
            trackingId={id}
            hasResume={has_resume}
            resumeFilename={resume_filename}
            onUpload={onUploadResume}
            disabled={disabled}
          />

          {/* Job Metadata Inputs (salary, location, note) */}
          <JobMetadataInputs
            trackingId={id}
            notes={notes}
            onUpdate={onUpdateTracking}
            disabled={disabled}
            isRejected={isRejected}
          />

          {/* Progress Section */}
          <div className="trk-progress-section">
            <div className="trk-progress-header">
              <h4>Progress</h4>
              {!isRejected && !isTerminalStage && (
                <button
                  className="trk-reject-btn"
                  onClick={() => setRejectModalOpen(true)}
                  disabled={disabled}
                >
                  Mark Rejected
                </button>
              )}
              {isRejected && (
                <div className="trk-rejected-actions">
                  <span className="trk-rejected-badge">Rejected</span>
                  <button
                    className="trk-undo-reject-btn"
                    onClick={handleUndoReject}
                    disabled={disabled}
                    title="Undo rejection"
                  >
                    Undo
                  </button>
                </div>
              )}
            </div>

            {/* Progress Stepper */}
            <ProgressStepper
              currentStage={stage}
              events={events}
              isRejected={isRejected}
              onStageClick={handleStageClick}
            />

            {/* Stage Cards */}
            <div className="trk-stage-cards">
              <div className="trk-stage-cards-main">
                {MAIN_STAGES.map((stageName) => (
                  <StageCard
                    key={stageName}
                    stageName={stageName}
                    event={eventsByType[stageName]}
                    stageData={getStageData(stageName)}
                    state={getStageState(stageName)}
                    isRejected={isRejected}
                    onAdd={handleStageAdd}
                    onEdit={handleStageEdit}
                    onDelete={handleStageDelete}
                    disabled={disabled}
                  />
                ))}
              </div>
              {/* Terminal stages */}
              <div className="trk-stage-cards-terminal">
                {TERMINAL_STAGES.map((stageName) => (
                  <StageCard
                    key={stageName}
                    stageName={stageName}
                    event={eventsByType[stageName]}
                    stageData={getStageData(stageName)}
                    state={getStageState(stageName)}
                    isRejected={isRejected}
                    onAdd={handleStageAdd}
                    onEdit={handleStageEdit}
                    onDelete={handleStageDelete}
                    disabled={disabled}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stage Form Modal */}
      <StageCardForm
        stageName={formModal.stageName}
        event={formModal.event}
        stageData={formModal.stageData}
        isOpen={formModal.isOpen}
        onClose={closeFormModal}
        onSave={handleFormSave}
        disabled={disabled}
      />

      {/* Reject Modal */}
      <RejectModal
        isOpen={rejectModalOpen}
        jobTitle={title}
        onClose={() => setRejectModalOpen(false)}
        onConfirm={handleReject}
        disabled={disabled}
      />
    </div>
  );
}

export default TrackedJobCard;
