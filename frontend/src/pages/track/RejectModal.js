import React, { useState } from 'react';

/**
 * RejectModal - Confirmation modal for marking a job as rejected.
 *
 * Rejection is a terminal state that locks all stage editing.
 *
 * Props:
 * - isOpen: boolean - whether modal is open
 * - jobTitle: string - job title for display
 * - onClose: () => void - close modal
 * - onConfirm: (rejectionData) => Promise - callback with { datetime, note }
 * - disabled: boolean - disable during save
 */
function RejectModal({ isOpen, jobTitle, onClose, onConfirm, disabled }) {
  const [rejectionDate, setRejectionDate] = useState('');
  const [rejectionNote, setRejectionNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // Reset form when opening
  React.useEffect(() => {
    if (isOpen) {
      const today = new Date().toISOString().split('T')[0];
      setRejectionDate(today);
      setRejectionNote('');
    }
  }, [isOpen]);

  const handleConfirm = async () => {
    if (isSaving || disabled) return;

    setIsSaving(true);
    try {
      await onConfirm({
        datetime: rejectionDate,
        note: rejectionNote || null,
      });
      onClose();
    } catch (err) {
      console.error('Failed to mark as rejected:', err);
      alert(`Error: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="trk-modal-overlay" onClick={onClose}>
      <div className="trk-modal reject-modal" onClick={(e) => e.stopPropagation()}>
        <h3>Mark as Rejected</h3>
        <p className="trk-reject-warning">
          Mark "{jobTitle}" as rejected? This will lock all stage editing.
        </p>

        <div className="trk-form-field">
          <label>Rejection Date</label>
          <input
            type="date"
            value={rejectionDate}
            onChange={(e) => setRejectionDate(e.target.value)}
            disabled={isSaving}
          />
        </div>

        <div className="trk-form-field">
          <label>Reason (optional)</label>
          <textarea
            value={rejectionNote}
            onChange={(e) => setRejectionNote(e.target.value)}
            placeholder="e.g., Position filled, not a good fit..."
            rows={2}
            disabled={isSaving}
          />
        </div>

        <div className="trk-modal-actions">
          <button
            className="trk-modal-btn cancel"
            onClick={onClose}
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            className="trk-modal-btn confirm danger"
            onClick={handleConfirm}
            disabled={isSaving || !rejectionDate}
          >
            {isSaving ? 'Processing...' : 'Mark Rejected'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default RejectModal;
