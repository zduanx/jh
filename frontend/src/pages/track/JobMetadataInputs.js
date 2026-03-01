import React, { useState, useEffect, useCallback, useRef } from 'react';

/**
 * JobMetadataInputs - Editable metadata fields for a tracked job.
 *
 * Layout:
 *   Salary: [____]   Location: [____]
 *   Note:
 *   [____________________]
 *
 * Props:
 * - trackingId: number - tracking entry ID
 * - notes: object - current notes JSONB (contains salary, location, general_note)
 * - onUpdate: (trackingId, updates) => Promise - callback to save changes
 * - disabled: boolean - disable inputs when action in progress
 * - isRejected: boolean - make read-only if job is rejected
 */
function JobMetadataInputs({ trackingId, notes, onUpdate, disabled, isRejected }) {
  // Local state for input values
  const [salary, setSalary] = useState('');
  const [location, setLocation] = useState('');
  const [generalNote, setGeneralNote] = useState('');

  // Track which fields have been modified
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Initialize from notes prop
  useEffect(() => {
    setSalary(notes?.salary || '');
    setLocation(notes?.location || '');
    setGeneralNote(notes?.general_note || '');
    setIsDirty(false);
  }, [notes]);

  // Debounced save - save after user stops typing
  const saveChanges = useCallback(async () => {
    if (!isDirty || isSaving || isRejected) return;

    setIsSaving(true);
    try {
      await onUpdate(trackingId, {
        notes: {
          salary: salary || null,
          location: location || null,
          general_note: generalNote || null,
        }
      });
      setIsDirty(false);
    } catch (err) {
      console.error('Failed to save metadata:', err);
    } finally {
      setIsSaving(false);
    }
  }, [trackingId, salary, location, generalNote, isDirty, isSaving, isRejected, onUpdate]);

  // Save on blur
  const handleBlur = () => {
    if (isDirty) {
      saveChanges();
    }
  };

  // Mark as dirty on change
  const handleSalaryChange = (e) => {
    setSalary(e.target.value);
    setIsDirty(true);
  };

  const handleLocationChange = (e) => {
    setLocation(e.target.value);
    setIsDirty(true);
  };

  const handleNoteChange = (e) => {
    setGeneralNote(e.target.value);
    setIsDirty(true);
  };

  const noteRef = useRef(null);

  // Auto-resize textarea to fit content
  const autoResize = useCallback(() => {
    const el = noteRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }, []);

  useEffect(() => {
    autoResize();
  }, [generalNote, autoResize]);

  const isDisabled = disabled || isSaving || isRejected;

  return (
    <div className="trk-metadata">
      <div className="trk-metadata-row">
        <div className="trk-metadata-field">
          <label htmlFor={`salary-${trackingId}`}>Salary</label>
          <input
            id={`salary-${trackingId}`}
            type="text"
            value={salary}
            onChange={handleSalaryChange}
            onBlur={handleBlur}
            placeholder="e.g. $150k-180k"
            disabled={isDisabled}
          />
        </div>
        <div className="trk-metadata-field">
          <label htmlFor={`location-${trackingId}`}>Location</label>
          <input
            id={`location-${trackingId}`}
            type="text"
            value={location}
            onChange={handleLocationChange}
            onBlur={handleBlur}
            placeholder="e.g. Remote, Hybrid"
            disabled={isDisabled}
          />
        </div>
      </div>
      <div className="trk-metadata-note">
        <label htmlFor={`note-${trackingId}`}>Note</label>
        <textarea
          ref={noteRef}
          id={`note-${trackingId}`}
          value={generalNote}
          onChange={handleNoteChange}
          onBlur={handleBlur}
          placeholder="General notes about this opportunity..."
          disabled={isDisabled}
          rows={2}
        />
      </div>
      {isSaving && <span className="trk-metadata-saving">Saving...</span>}
    </div>
  );
}

export default JobMetadataInputs;
