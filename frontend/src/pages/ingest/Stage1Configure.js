import React, { useState, useEffect, useMemo, useCallback } from 'react';
import FilterModal from './components/FilterModal';
import './Stage1Configure.css';

/**
 * Normalize filters for consistent comparison:
 * - Sort arrays so order doesn't affect equality
 */
const normalizeFilters = (filters) => {
  const include = filters?.include ? [...filters.include].sort() : [];
  const exclude = filters?.exclude ? [...filters.exclude].sort() : [];
  return { include, exclude };
};

/**
 * Create a comparable snapshot of a company setting
 */
const createSnapshot = (item) => ({
  company_name: item.company_name,
  is_enabled: item.is_enabled,
  filters: normalizeFilters(item.title_filters),
});

/**
 * Compare two snapshots for equality
 */
const snapshotsEqual = (a, b) => {
  if (a.company_name !== b.company_name) return false;
  if (a.is_enabled !== b.is_enabled) return false;
  if (JSON.stringify(a.filters) !== JSON.stringify(b.filters)) return false;
  return true;
};

/**
 * Stage 1: Configure companies and filters
 *
 * Two-column layout:
 * - Left (1/4): Available companies (not yet selected)
 * - Right (3/4): Selected companies with filter config
 *
 * Local state management with snapshot comparison - API calls only on Save
 */
function Stage1Configure({
  companies,
  savedSettings,
  loading,
  error,
  onError,
  onSettingsUpdate,
  onNext
}) {
  // Local state for selected companies (modified from savedSettings)
  const [localSelected, setLocalSelected] = useState([]);
  const [originalSnapshot, setOriginalSnapshot] = useState({}); // Map of company_name -> snapshot
  const [modalOpen, setModalOpen] = useState(false);
  const [modalCompany, setModalCompany] = useState(null);
  const [editingIndex, setEditingIndex] = useState(null); // null = adding new, number = editing
  const [saving, setSaving] = useState(false);

  const apiUrl = process.env.REACT_APP_API_URL;

  // Initialize local state from saved settings
  useEffect(() => {
    if (savedSettings && companies.length > 0) {
      const selected = savedSettings
        .map(s => {
          const company = companies.find(c => c.name === s.company_name);
          return {
            id: s.id,
            company_name: s.company_name,
            display_name: company?.display_name || s.company_name,
            logo_url: company?.logo_url,
            title_filters: normalizeFilters(s.title_filters),
            is_enabled: s.is_enabled !== false, // default true
            updated_at: s.updated_at, // From DB
          };
        })
        .sort((a, b) => a.display_name.localeCompare(b.display_name));
      setLocalSelected(selected);
      // Create snapshot map for comparison
      const snapshot = {};
      selected.forEach(item => {
        snapshot[item.company_name] = createSnapshot(item);
      });
      setOriginalSnapshot(snapshot);
    }
  }, [savedSettings, companies]);

  // Compute available companies (not in selected)
  const availableCompanies = useMemo(() => {
    const selectedNames = new Set(localSelected.map(s => s.company_name));
    return companies.filter(c => !selectedNames.has(c.name));
  }, [companies, localSelected]);

  // Check if a specific item is new (not in original)
  const isItemNew = useCallback((item) => {
    return !originalSnapshot[item.company_name];
  }, [originalSnapshot]);

  // Check if a specific item is modified (different from original)
  const isItemModified = useCallback((item) => {
    const original = originalSnapshot[item.company_name];
    if (!original) return false; // New items are not "modified"
    return !snapshotsEqual(createSnapshot(item), original);
  }, [originalSnapshot]);

  // Check if there are unsaved changes (any additions, deletions, or modifications)
  const isDirty = useMemo(() => {
    // Check for deletions
    const currentNames = new Set(localSelected.map(s => s.company_name));
    const hasDeletes = Object.keys(originalSnapshot).some(name => !currentNames.has(name));
    if (hasDeletes) return true;

    // Check for additions or modifications
    return localSelected.some(item => isItemNew(item) || isItemModified(item));
  }, [localSelected, originalSnapshot, isItemNew, isItemModified]);

  // Count enabled companies (for Next button validation)
  const enabledCount = useMemo(() => {
    return localSelected.filter(item => item.is_enabled).length;
  }, [localSelected]);

  // Open modal to add a new company
  const handleAddCompany = (company) => {
    setModalCompany(company);
    setEditingIndex(null);
    setModalOpen(true);
  };

  // Open modal to edit existing selection
  const handleEditCompany = (index) => {
    const selected = localSelected[index];
    const company = companies.find(c => c.name === selected.company_name);
    setModalCompany(company);
    setEditingIndex(index);
    setModalOpen(true);
  };

  // Save from modal (add or update)
  const handleModalSave = (modalData) => {
    const { is_enabled, ...filters } = modalData;
    const normalizedFilters = normalizeFilters(filters);

    if (editingIndex !== null) {
      // Editing existing
      setLocalSelected(prev => prev.map((item, idx) => {
        if (idx === editingIndex) {
          return {
            ...item,
            title_filters: normalizedFilters,
            is_enabled,
          };
        }
        return item;
      }));
    } else {
      // Adding new
      setLocalSelected(prev => [...prev, {
        id: null,
        company_name: modalCompany.name,
        display_name: modalCompany.display_name,
        logo_url: modalCompany.logo_url,
        title_filters: normalizedFilters,
        is_enabled,
      }]);
    }
    setModalOpen(false);
    setModalCompany(null);
    setEditingIndex(null);
  };

  // Remove company from selected
  const handleRemoveCompany = (index) => {
    setLocalSelected(prev => prev.filter((_, idx) => idx !== index));
  };

  // Toggle enabled state directly on card
  const handleToggleEnabled = (index) => {
    setLocalSelected(prev => prev.map((item, idx) => {
      if (idx === index) {
        return {
          ...item,
          is_enabled: !item.is_enabled,
        };
      }
      return item;
    }));
  };

  // Cancel all changes - restore from original snapshot
  const handleCancel = () => {
    if (savedSettings && companies.length > 0) {
      const selected = savedSettings
        .map(s => {
          const company = companies.find(c => c.name === s.company_name);
          return {
            id: s.id,
            company_name: s.company_name,
            display_name: company?.display_name || s.company_name,
            logo_url: company?.logo_url,
            title_filters: normalizeFilters(s.title_filters),
            is_enabled: s.is_enabled !== false,
          };
        })
        .sort((a, b) => a.display_name.localeCompare(b.display_name));
      setLocalSelected(selected);
    }
  };

  // Save all changes to API
  const handleSave = async () => {
    setSaving(true);
    onError(null);

    try {
      const token = localStorage.getItem('access_token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      // Build operations array
      const operations = [];

      // Find items to delete (in original but not in local)
      const localNames = new Set(localSelected.map(s => s.company_name));
      const originalNames = Object.keys(originalSnapshot);
      const toDeleteNames = originalNames.filter(name => !localNames.has(name));

      // Add delete operations
      for (const name of toDeleteNames) {
        operations.push({ op: 'delete', company_name: name });
      }

      // Find items to create or update (new or modified)
      const toSave = localSelected.filter(item => isItemNew(item) || isItemModified(item));

      // Add upsert operations
      for (const item of toSave) {
        operations.push({
          op: 'upsert',
          company_name: item.company_name,
          title_filters: item.title_filters,
          is_enabled: item.is_enabled,
        });
      }

      // Skip API call if no operations
      if (operations.length === 0) {
        setSaving(false);
        return;
      }

      // Execute batch operation
      const res = await fetch(`${apiUrl}/api/ingestion/settings`, {
        method: 'POST',
        headers,
        body: JSON.stringify(operations),
      });

      if (!res.ok) throw new Error('Failed to save settings');

      const results = await res.json();

      // Check for failures
      const failures = results.filter(r => !r.success);
      if (failures.length > 0) {
        throw new Error(`Failed: ${failures.map(f => f.company_name).join(', ')}`);
      }

      // Merge results into local state - update id and updated_at for upserts
      const updatedLocal = localSelected.map(item => {
        const result = results.find(r => r.op === 'upsert' && r.company_name === item.company_name);
        if (result) {
          return {
            ...item,
            id: result.id,
            updated_at: result.updated_at,
          };
        }
        return item;
      });

      // Update parent state with new settings
      const newSavedSettings = updatedLocal.map(item => ({
        id: item.id,
        company_name: item.company_name,
        title_filters: item.title_filters,
        is_enabled: item.is_enabled,
        updated_at: item.updated_at,
      }));
      onSettingsUpdate(newSavedSettings);

      // Update local state and snapshot
      setLocalSelected(updatedLocal);
      const newSnapshot = {};
      updatedLocal.forEach(item => {
        newSnapshot[item.company_name] = createSnapshot(item);
      });
      setOriginalSnapshot(newSnapshot);

    } catch (err) {
      onError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // Format timestamp for display
  const formatUpdatedAt = (timestamp) => {
    if (!timestamp) return null;
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  // Render filter tokens
  const renderFilterTokens = (terms, emptyText) => {
    if (!terms || terms.length === 0) {
      return <span className="s1-filter-empty">{emptyText}</span>;
    }
    return (
      <span className="s1-filter-tokens">
        {terms.map((term, i) => (
          <span key={i} className="s1-filter-token">{term}</span>
        ))}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="stage-content">
        <div className="s1-loading-state">
          <div className="s1-spinner"></div>
          <p>Loading companies...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="stage-content">
      {error && (
        <div className="s1-error-banner">
          {error}
          <button onClick={() => onError(null)}>Dismiss</button>
        </div>
      )}

      <div className="s1-layout">
        {/* Left Column: Available Companies */}
        <div className="s1-available-column">
          <div className="s1-column-header">
            <h3>Available Companies</h3>
            <span className="s1-column-count">{availableCompanies.length}</span>
          </div>
          <div className="s1-available-list">
            {availableCompanies.map(company => (
              <div
                key={company.name}
                className="s1-available-card"
                onClick={() => handleAddCompany(company)}
              >
                <img
                  src={company.logo_url}
                  alt={company.display_name}
                  className="s1-available-logo"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
                <span className="s1-available-name">{company.display_name}</span>
                <span className="s1-add-icon">+</span>
              </div>
            ))}
            {availableCompanies.length === 0 && (
              <div className="s1-empty-state">
                All companies selected
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Selected Companies */}
        <div className="s1-selected-column">
          <div className="s1-column-header">
            <div className="s1-column-title-row">
              <h3>Selected Companies</h3>
              <span className="s1-column-count">{localSelected.length}</span>
            </div>
            <div className="s1-column-actions">
              {isDirty && (
                <>
                  <button
                    className="s1-cancel-btn"
                    onClick={handleCancel}
                    disabled={saving}
                  >
                    Cancel
                  </button>
                  <button
                    className="s1-save-btn"
                    onClick={handleSave}
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="s1-selected-grid">
            {localSelected.map((item, index) => {
              const itemIsNew = isItemNew(item);
              const itemIsModified = isItemModified(item);
              return (
              <div
                key={item.company_name}
                className={`s1-selected-card ${itemIsNew ? 'is-new' : ''} ${itemIsModified ? 'is-modified' : ''} ${!item.is_enabled ? 'is-disabled' : ''}`}
              >
                <div className="s1-selected-card-header">
                  <div className="s1-selected-card-info">
                    <button
                      type="button"
                      className={`s1-card-toggle ${item.is_enabled ? 's1-toggle-on' : ''}`}
                      onClick={() => handleToggleEnabled(index)}
                      title={item.is_enabled ? 'Disable' : 'Enable'}
                    >
                      <span className="s1-toggle-knob" />
                    </button>
                    <img
                      src={item.logo_url}
                      alt={item.display_name}
                      className="s1-selected-logo"
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                    <span className="s1-selected-name">{item.display_name}</span>
                    {itemIsNew && <span className="s1-status-badge new">New</span>}
                    {itemIsModified && <span className="s1-status-badge modified">Modified</span>}
                  </div>
                  <div className="s1-selected-card-actions">
                    <button
                      className="s1-edit-btn"
                      onClick={() => handleEditCompany(index)}
                      title="Edit filters"
                    >
                      Edit
                    </button>
                    <button
                      className="s1-remove-btn"
                      onClick={() => handleRemoveCompany(index)}
                      title="Remove"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className="s1-selected-card-filters">
                  <div className="s1-filter-row">
                    <span className="s1-filter-label">Include:</span>
                    {renderFilterTokens(item.title_filters?.include, 'All jobs')}
                  </div>
                  <div className="s1-filter-row">
                    <span className="s1-filter-label">Exclude:</span>
                    {renderFilterTokens(item.title_filters?.exclude, '')}
                  </div>
                </div>
                <div className="s1-selected-card-footer">
                  <span className="s1-updated-at">
                    {item.updated_at ? `Updated ${formatUpdatedAt(item.updated_at)}` : ''}
                  </span>
                </div>
              </div>
              );
            })}
            {localSelected.length === 0 && (
              <div className="s1-empty-state large">
                <div className="s1-empty-icon">📋</div>
                <p>No companies selected</p>
                <span>Click a company on the left to add it</span>
              </div>
            )}
          </div>

          {/* Footer with Next button */}
          <div className="s1-footer">
            <div className="s1-selection-summary">
              {enabledCount} of {localSelected.length} {localSelected.length === 1 ? 'company' : 'companies'} enabled
              {isDirty && <span className="s1-unsaved-indicator"> • Unsaved changes</span>}
            </div>
            <button
              className="s1-next-btn"
              disabled={enabledCount === 0 || isDirty}
              onClick={onNext}
              title={
                isDirty ? 'Save changes before proceeding' :
                enabledCount === 0 ? 'Enable at least one company' : ''
              }
            >
              Next: Preview →
            </button>
          </div>
        </div>
      </div>

      {/* Filter Modal */}
      {modalOpen && modalCompany && (
        <FilterModal
          company={modalCompany}
          initialFilters={editingIndex !== null ? localSelected[editingIndex].title_filters : null}
          initialEnabled={editingIndex !== null ? localSelected[editingIndex].is_enabled : true}
          onSave={handleModalSave}
          onCancel={() => {
            setModalOpen(false);
            setModalCompany(null);
            setEditingIndex(null);
          }}
        />
      )}
    </div>
  );
}

export default Stage1Configure;
