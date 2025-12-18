import React, { useState, useEffect } from 'react';
import TokenInput from './TokenInput';
import './FilterModal.css';

/**
 * Modal for configuring company filters (include/exclude keywords)
 */
function FilterModal({ company, initialFilters, initialEnabled = true, onSave, onCancel }) {
  const [includeTokens, setIncludeTokens] = useState([]);
  const [excludeTokens, setExcludeTokens] = useState([]);
  const [isEnabled, setIsEnabled] = useState(true);

  useEffect(() => {
    if (initialFilters) {
      setIncludeTokens(initialFilters.include || []);
      setExcludeTokens(initialFilters.exclude || []);
    } else {
      setIncludeTokens([]);
      setExcludeTokens([]);
    }
    setIsEnabled(initialEnabled);
  }, [initialFilters, initialEnabled]);

  const handleSave = () => {
    onSave({
      include: includeTokens.length > 0 ? includeTokens : null,
      exclude: excludeTokens,
      is_enabled: isEnabled,
    });
  };

  return (
    <div className="fm-overlay" onClick={onCancel}>
      <div className="fm-content" onClick={e => e.stopPropagation()}>
        <div className="fm-header">
          <div className="fm-title-row">
            {company.logo_url && (
              <img
                src={company.logo_url}
                alt={company.display_name}
                className="fm-company-logo"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            )}
            <h3>Configure: {company.display_name}</h3>
          </div>
          <button className="fm-close-btn" onClick={onCancel}>×</button>
        </div>

        <div className="fm-body">
          <div className="fm-toggle-group">
            <label className="fm-toggle-label">
              <span className="fm-toggle-text">
                Enabled
                <span className="fm-filter-hint">
                  Include this company in job extraction
                </span>
              </span>
              <button
                type="button"
                className={`fm-toggle ${isEnabled ? 'fm-toggle-on' : ''}`}
                onClick={() => setIsEnabled(!isEnabled)}
                aria-pressed={isEnabled}
              >
                <span className="fm-toggle-knob" />
              </button>
            </label>
          </div>

          <div className="fm-filter-group">
            <label>
              Include Keywords
              <span className="fm-filter-hint">
                Only include jobs containing these keywords. Leave empty to include all.
              </span>
            </label>
            <TokenInput
              tokens={includeTokens}
              onChange={setIncludeTokens}
              placeholder="Type keyword and press Enter..."
            />
          </div>

          <div className="fm-filter-group">
            <label>
              Exclude Keywords
              <span className="fm-filter-hint">
                Exclude jobs containing these keywords.
              </span>
            </label>
            <TokenInput
              tokens={excludeTokens}
              onChange={setExcludeTokens}
              placeholder="Type keyword and press Enter..."
            />
          </div>
        </div>

        <div className="fm-footer">
          <button className="fm-cancel-btn" onClick={onCancel}>Cancel</button>
          <button className="fm-save-btn" onClick={handleSave}>Add to Selected</button>
        </div>
      </div>
    </div>
  );
}

export default FilterModal;
