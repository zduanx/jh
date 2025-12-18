import React, { useState } from 'react';
import './TokenInput.css';

/**
 * Token-based input component for tags/keywords
 * Displays tokens as removable pills and allows adding new ones
 */
function TokenInput({ tokens, onChange, placeholder }) {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addToken();
    } else if (e.key === 'Backspace' && inputValue === '' && tokens.length > 0) {
      // Remove last token when backspace on empty input
      removeToken(tokens.length - 1);
    }
  };

  const addToken = () => {
    const value = inputValue.trim().toLowerCase();
    if (value && !tokens.includes(value)) {
      onChange([...tokens, value]);
    }
    setInputValue('');
  };

  const removeToken = (index) => {
    onChange(tokens.filter((_, i) => i !== index));
  };

  const handleBlur = () => {
    if (inputValue.trim()) {
      addToken();
    }
  };

  return (
    <div className="token-input-container">
      <div className="token-input-wrapper">
        {tokens.map((token, index) => (
          <span key={index} className="token">
            {token}
            <button
              type="button"
              className="token-remove"
              onClick={() => removeToken(index)}
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder={tokens.length === 0 ? placeholder : ''}
          className="token-input"
        />
      </div>
    </div>
  );
}

export default TokenInput;
