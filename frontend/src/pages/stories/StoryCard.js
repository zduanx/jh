import React, { useState, useEffect } from 'react';
import './StoryCard.css';

/**
 * StoryCard - Individual story card with STAR format.
 *
 * Features:
 * - Overview section (read-only, concatenated STAR)
 * - Editable fields: question, type, tags, situation, task, action, result
 * - Cancel/Save buttons when dirty
 * - Delete button with confirmation
 */
function StoryCard({ story, isActive, onUpdate, onDelete }) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Local form state
  const [formData, setFormData] = useState({
    question: story.question || '',
    type: story.type || '',
    tags: story.tags || [],
    situation: story.situation || '',
    task: story.task || '',
    action: story.action || '',
    result: story.result || '',
  });

  // Tag input state
  const [tagInput, setTagInput] = useState('');

  // Reset form when story changes
  useEffect(() => {
    setFormData({
      question: story.question || '',
      type: story.type || '',
      tags: story.tags || [],
      situation: story.situation || '',
      task: story.task || '',
      action: story.action || '',
      result: story.result || '',
    });
    setIsEditing(false);
  }, [story]);

  // Check if form is dirty
  const isDirty = () => {
    return (
      formData.question !== (story.question || '') ||
      formData.type !== (story.type || '') ||
      formData.situation !== (story.situation || '') ||
      formData.task !== (story.task || '') ||
      formData.action !== (story.action || '') ||
      formData.result !== (story.result || '') ||
      JSON.stringify(formData.tags) !== JSON.stringify(story.tags || [])
    );
  };

  // Generate overview from STAR fields
  const getOverview = () => {
    const parts = [
      formData.situation,
      formData.task,
      formData.action,
      formData.result,
    ].filter(Boolean);
    return parts.join('\n\n');
  };

  // Handle field change
  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (!isEditing) setIsEditing(true);
  };

  // Handle tag add (Enter or Space creates a token)
  const handleAddTag = (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && tagInput.trim()) {
      e.preventDefault();
      const newTag = tagInput.trim().toLowerCase();
      if (!formData.tags.includes(newTag)) {
        handleChange('tags', [...formData.tags, newTag]);
      }
      setTagInput('');
    }
  };

  // Handle tag remove
  const handleRemoveTag = (tagToRemove) => {
    handleChange('tags', formData.tags.filter(t => t !== tagToRemove));
  };

  // Handle save
  const handleSave = async () => {
    setIsSaving(true);
    const success = await onUpdate(story.id, formData);
    setIsSaving(false);
    if (success) {
      setIsEditing(false);
    }
  };

  // Handle cancel
  const handleCancel = () => {
    setFormData({
      question: story.question || '',
      type: story.type || '',
      tags: story.tags || [],
      situation: story.situation || '',
      task: story.task || '',
      action: story.action || '',
      result: story.result || '',
    });
    setIsEditing(false);
  };

  // Handle delete
  const handleDelete = () => {
    setShowDeleteConfirm(true);
  };

  const confirmDelete = () => {
    onDelete(story.id);
    setShowDeleteConfirm(false);
  };

  const overview = getOverview();

  return (
    <div className={`stc-card ${isActive ? 'active' : ''}`}>
      {/* Header - Question */}
      <div className="stc-header">
        <div className="stc-question-field">
          <label>Question:</label>
          <input
            type="text"
            className="stc-question-input"
            value={formData.question}
            onChange={(e) => handleChange('question', e.target.value)}
            placeholder="Enter your behavioral question..."
          />
        </div>
        <button
          className="stc-delete-btn"
          onClick={handleDelete}
          title="Delete story"
        >
          ×
        </button>
      </div>

      {/* Type and Tags */}
      <div className="stc-meta">
        <div className="stc-type-row">
          <label>Type:</label>
          <select
            value={formData.type}
            onChange={(e) => handleChange('type', e.target.value)}
          >
            <option value="">Select type...</option>
            <option value="leadership">Leadership</option>
            <option value="conflict">Conflict</option>
            <option value="teamwork">Teamwork</option>
            <option value="problem-solving">Problem Solving</option>
            <option value="failure">Failure</option>
            <option value="success">Success</option>
            <option value="communication">Communication</option>
            <option value="time-management">Time Management</option>
          </select>
        </div>

        <div className="stc-tags-row">
          <label>Tags:</label>
          <div className="stc-tags-container">
            {formData.tags.map(tag => (
              <span key={tag} className="stc-tag">
                {tag}
                <button onClick={() => handleRemoveTag(tag)}>×</button>
              </span>
            ))}
            <input
              type="text"
              className="stc-tag-input"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleAddTag}
              placeholder="Add tag..."
            />
          </div>
        </div>
      </div>

      {/* Overview - Read Only */}
      {overview && (
        <div className="stc-overview">
          <label>Overview</label>
          <div className="stc-overview-content">
            {overview}
          </div>
        </div>
      )}

      {/* STAR Fields */}
      <div className="stc-star-fields">
        <div className="stc-field">
          <label>Situation</label>
          <textarea
            value={formData.situation}
            onChange={(e) => handleChange('situation', e.target.value)}
            placeholder="Describe the context and background..."
            rows={3}
          />
        </div>

        <div className="stc-field">
          <label>Task</label>
          <textarea
            value={formData.task}
            onChange={(e) => handleChange('task', e.target.value)}
            placeholder="What was your responsibility?"
            rows={3}
          />
        </div>

        <div className="stc-field">
          <label>Action</label>
          <textarea
            value={formData.action}
            onChange={(e) => handleChange('action', e.target.value)}
            placeholder="What steps did you take?"
            rows={4}
          />
        </div>

        <div className="stc-field">
          <label>Result</label>
          <textarea
            value={formData.result}
            onChange={(e) => handleChange('result', e.target.value)}
            placeholder="What was the outcome?"
            rows={3}
          />
        </div>
      </div>

      {/* Action Buttons */}
      {isDirty() && (
        <div className="stc-actions">
          <button
            className="stc-cancel-btn"
            onClick={handleCancel}
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            className="stc-save-btn"
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="stc-modal-overlay" onClick={() => setShowDeleteConfirm(false)}>
          <div className="stc-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Delete Story?</h3>
            <p>This action cannot be undone.</p>
            <div className="stc-modal-actions">
              <button
                className="stc-cancel-btn"
                onClick={() => setShowDeleteConfirm(false)}
              >
                Cancel
              </button>
              <button
                className="stc-delete-confirm-btn"
                onClick={confirmDelete}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default StoryCard;
