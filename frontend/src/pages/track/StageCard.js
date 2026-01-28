import React from 'react';
import { MdEdit, MdAdd, MdDelete, MdLock } from 'react-icons/md';

/**
 * StageCard - Mini card for a single stage in the progress stepper.
 *
 * States:
 * - completed: Shows data + [Edit] button (+ [Delete] if latest)
 * - next: Shows [+ Add] button
 * - locked: Greyed out, shows lock icon
 *
 * Props:
 * - stageName: string - stage name (applied, screening, etc.)
 * - event: object | null - event data if completed { id, event_type, event_date, event_time, location, note, is_deletable }
 * - stageData: object | null - stage-specific data from notes.stages[stageName]
 * - state: 'completed' | 'next' | 'locked'
 * - isRejected: boolean - job is rejected, all cards locked
 * - onAdd: (stageName) => void - callback to add this stage
 * - onEdit: (stageName, event, stageData) => void - callback to edit
 * - onDelete: (eventId) => void - callback to delete (only for latest event)
 * - disabled: boolean - disable actions when request in progress
 */
function StageCard({
  stageName,
  event,
  stageData,
  state,
  isRejected,
  onAdd,
  onEdit,
  onDelete,
  disabled,
}) {
  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // Format time for display
  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    const [hours, minutes] = timeStr.split(':');
    const hour = parseInt(hours, 10);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
  };

  // Get summary text from stage data
  const getSummary = () => {
    if (!stageData) return null;

    const summaryParts = [];

    // Show type if available (applied, screening, interview)
    if (stageData.type) {
      summaryParts.push(stageData.type);
    }

    // Show round for interview
    if (stageData.round) {
      summaryParts.push(stageData.round);
    }

    // Show with_person for screening
    if (stageData.with_person) {
      summaryParts.push(`w/ ${stageData.with_person}`);
    }

    // Show referrer for referral type
    if (stageData.type === 'referral' && stageData.referrer_name) {
      summaryParts.push(`via ${stageData.referrer_name}`);
    }

    // Show amount for offer
    if (stageData.amount) {
      summaryParts.push(stageData.amount);
    }

    return summaryParts.length > 0 ? summaryParts.join(' - ') : null;
  };

  const handleAdd = () => {
    if (!disabled && onAdd) {
      onAdd(stageName);
    }
  };

  const handleEdit = () => {
    if (!disabled && onEdit) {
      onEdit(stageName, event, stageData);
    }
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (!disabled && onDelete && event?.is_deletable) {
      onDelete(event.id);
    }
  };

  // Locked state (but not completed stages when rejected - those still show data)
  if (state === 'locked') {
    return (
      <div className="trk-stage-card locked">
        <div className="trk-stage-card-lock">
          <MdLock size={16} />
        </div>
        <span className="trk-stage-card-name">{stageName}</span>
      </div>
    );
  }

  // Next available state - show Add button (but locked if rejected)
  if (state === 'next') {
    if (isRejected) {
      return (
        <div className="trk-stage-card locked">
          <div className="trk-stage-card-lock">
            <MdLock size={16} />
          </div>
          <span className="trk-stage-card-name">{stageName}</span>
        </div>
      );
    }
    return (
      <div className="trk-stage-card next" onClick={handleAdd}>
        <button
          className="trk-stage-card-add"
          disabled={disabled}
          title={`Add ${stageName}`}
        >
          <MdAdd size={20} />
        </button>
        <span className="trk-stage-card-name">{stageName}</span>
      </div>
    );
  }

  // Completed state - show data (read-only if rejected, editable otherwise)
  const summary = getSummary();

  return (
    <div
      className={`trk-stage-card completed ${isRejected ? 'readonly' : ''}`}
      onClick={isRejected ? undefined : handleEdit}
    >
      <div className="trk-stage-card-content">
        <div className="trk-stage-card-date">
          {formatDate(event?.event_date)}
          {event?.event_time && (
            <span className="trk-stage-card-time">{formatTime(event.event_time)}</span>
          )}
        </div>
        {summary && <div className="trk-stage-card-summary">{summary}</div>}
        {event?.note && <div className="trk-stage-card-note">{event.note}</div>}
      </div>
      {!isRejected && (
        <div className="trk-stage-card-actions">
          <button
            className="trk-stage-card-btn edit"
            onClick={handleEdit}
            disabled={disabled}
            title="Edit"
          >
            <MdEdit size={14} />
          </button>
          {event?.is_deletable && (
            <button
              className="trk-stage-card-btn delete"
              onClick={handleDelete}
              disabled={disabled}
              title="Delete (rollback)"
            >
              <MdDelete size={14} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default StageCard;
