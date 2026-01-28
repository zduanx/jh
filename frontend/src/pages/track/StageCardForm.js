import React, { useState, useEffect, useMemo } from 'react';
import { STAGE_FIELDS } from '../../types/trackingSchema';

/**
 * StageCardForm - Modal form for adding/editing stage data.
 *
 * Props:
 * - stageName: string - stage being edited
 * - event: object | null - existing event with note as JSONB (null if adding new)
 * - isOpen: boolean - whether modal is open
 * - onClose: () => void - close modal
 * - onSave: (stageName, eventData, existingEventId) => Promise - save callback
 * - disabled: boolean - disable form during save
 */
function StageCardForm({
  stageName,
  event,
  isOpen,
  onClose,
  onSave,
  disabled,
}) {
  const fields = useMemo(() => STAGE_FIELDS[stageName] || {}, [stageName]);
  const isEditing = !!event;

  // Form state
  const [formData, setFormData] = useState({});
  const [eventDate, setEventDate] = useState('');
  const [eventTime, setEventTime] = useState('');
  const [eventLocation, setEventLocation] = useState('');
  const [eventNote, setEventNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // Initialize form when opening
  useEffect(() => {
    if (isOpen) {
      // event.note is now JSONB containing all stage data including text note
      const noteData = event?.note || {};

      // Initialize stage data fields from event.note
      const initialData = {};
      Object.keys(fields).forEach((fieldName) => {
        if (fieldName === 'datetime') return; // Handle separately
        if (fieldName === 'note') return; // Handle as text note field
        initialData[fieldName] = noteData[fieldName] ?? fields[fieldName]?.default ?? '';
      });
      setFormData(initialData);

      // Initialize event fields
      if (event) {
        setEventDate(event.event_date || '');
        setEventTime(event.event_time?.slice(0, 5) || ''); // HH:MM format
        setEventLocation(event.location || '');
        setEventNote(noteData.note || ''); // Text note is inside the JSONB
      } else {
        // Default to today and current time for new events
        const now = new Date();
        const today = now.toISOString().split('T')[0];
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        setEventDate(today);
        setEventTime(`${hours}:${minutes}`);
        setEventLocation('');
        setEventNote('');
      }
    }
  }, [isOpen, stageName, event, fields]);

  const handleFieldChange = (fieldName, value) => {
    setFormData((prev) => ({ ...prev, [fieldName]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSaving || disabled) return;

    setIsSaving(true);
    try {
      // Build note as JSONB containing all stage-specific data including text note
      const noteData = {
        ...formData,
        note: eventNote || null,
      };

      // Build event data with note as JSONB
      const eventData = {
        event_type: stageName,
        event_date: eventDate,
        event_time: eventTime || null,
        location: eventLocation || null,
        note: noteData,
      };

      await onSave(stageName, eventData, event?.id);
      onClose();
    } catch (err) {
      console.error('Failed to save stage:', err);
      alert(`Error: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  // Check if field should be shown (for conditional fields like referrer_name)
  const shouldShowField = (fieldName, fieldConfig) => {
    if (typeof fieldConfig.showIf === 'function') {
      return fieldConfig.showIf(formData);
    }
    return true;
  };

  return (
    <div className="trk-modal-overlay" onClick={onClose}>
      <div className="trk-stage-form-modal" onClick={(e) => e.stopPropagation()}>
        <h3>{isEditing ? `Edit ${stageName}` : `Add ${stageName}`}</h3>

        <form onSubmit={handleSubmit}>
          {/* Date field (always first) */}
          <div className="trk-form-field">
            <label>Date *</label>
            <input
              type="date"
              value={eventDate}
              onChange={(e) => setEventDate(e.target.value)}
              required
              disabled={isSaving}
            />
          </div>

          {/* Time field (required) */}
          <div className="trk-form-field">
            <label>Time *</label>
            <input
              type="time"
              value={eventTime}
              onChange={(e) => setEventTime(e.target.value)}
              required
              disabled={isSaving}
            />
          </div>

          {/* Location field (optional, not for accepted/declined/rejected) */}
          {!['accepted', 'declined', 'rejected'].includes(stageName) && (
            <div className="trk-form-field">
              <label>Location</label>
              <input
                type="text"
                value={eventLocation}
                onChange={(e) => setEventLocation(e.target.value)}
                placeholder="e.g., Video call, Office, Phone"
                disabled={isSaving}
              />
            </div>
          )}

          {/* Stage-specific fields */}
          {Object.entries(fields).map(([fieldName, fieldConfig]) => {
            // Skip datetime and note (handled separately)
            if (fieldName === 'datetime' || fieldName === 'note') return null;

            // Check conditional display
            if (!shouldShowField(fieldName, fieldConfig)) return null;

            return (
              <div key={fieldName} className="trk-form-field">
                <label>{fieldConfig.label}</label>

                {fieldConfig.type === 'select' ? (
                  <select
                    value={formData[fieldName] || ''}
                    onChange={(e) => handleFieldChange(fieldName, e.target.value)}
                    disabled={isSaving}
                  >
                    {!formData[fieldName] && <option value="">Select...</option>}
                    {fieldConfig.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={formData[fieldName] || ''}
                    onChange={(e) => handleFieldChange(fieldName, e.target.value)}
                    placeholder={fieldConfig.label}
                    disabled={isSaving}
                  />
                )}
              </div>
            );
          })}

          {/* Note field (always last) */}
          <div className="trk-form-field">
            <label>Note</label>
            <textarea
              value={eventNote}
              onChange={(e) => setEventNote(e.target.value)}
              placeholder="Optional notes..."
              rows={2}
              disabled={isSaving}
            />
          </div>

          {/* Actions */}
          <div className="trk-form-actions">
            <button
              type="button"
              className="trk-form-btn cancel"
              onClick={onClose}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="trk-form-btn save"
              disabled={isSaving || !eventDate || !eventTime}
            >
              {isSaving ? 'Saving...' : isEditing ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default StageCardForm;
