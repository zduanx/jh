import { useRef, useState, useEffect, useCallback } from 'react';
import './ProfileResume.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * ProfileResume (Phase 7A) — upload/replace the user's profile resume (one per user)
 * for the chat assistant. Direct-to-S3 presigned flow (mirrors 4C, ADR-024):
 *   GET /api/resume/upload-url -> PUT file to S3 -> POST /api/resume/confirm
 * On confirm, the backend extracts text + embeds it (Voyage).
 *
 * Shown on the Search page so the user can set the resume the assistant reasons over.
 */
function ProfileResume() {
  const fileInputRef = useRef(null);
  const [status, setStatus] = useState(null); // {has_resume, has_embedding, chars}
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [debug, setDebug] = useState(null); // debug payload (text + vector) or null

  const token = () => localStorage.getItem('access_token');

  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/resume/`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (res.ok) setStatus(await res.json());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  const handleUpload = async (file) => {
    if (file.type !== 'application/pdf') { setError('Please upload a PDF.'); return; }
    if (file.size > 5 * 1024 * 1024) { setError('File must be under 5MB.'); return; }
    setBusy(true);
    setError(null);
    try {
      // 1. presigned URL
      const u = await fetch(`${API_URL}/api/resume/upload-url`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!u.ok) throw new Error('Could not get upload URL');
      const { upload_url, s3_key } = await u.json();

      // 2. PUT directly to S3
      const put = await fetch(upload_url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/pdf' },
        body: file,
      });
      if (!put.ok) throw new Error('S3 upload failed');

      // 3. confirm (backend extracts text + embeds)
      const c = await fetch(`${API_URL}/api/resume/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` },
        body: JSON.stringify({ s3_key, filename: file.name }),
      });
      if (!c.ok) {
        const d = await c.json().catch(() => ({}));
        throw new Error(d.detail || 'Confirm failed');
      }
      setStatus(await c.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const onFileChange = (e) => {
    const f = e.target.files?.[0];
    if (f) handleUpload(f);
  };

  const handleDownload = async () => {
    try {
      const res = await fetch(`${API_URL}/api/resume/url`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!res.ok) throw new Error('Could not get download URL');
      const { url } = await res.json();
      window.open(url, '_blank');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDebug = async () => {
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/resume/debug`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!res.ok) throw new Error('Could not load debug data');
      setDebug(await res.json());
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete your assistant resume? This cannot be undone.')) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/resume/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!res.ok) throw new Error('Delete failed');
      setStatus({ has_resume: false });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="pr-box">
      <span className="pr-label">Assistant resume:</span>
      {status?.has_resume ? (
        <span className="pr-status">
          ✓ {status.filename || 'resume.pdf'} ({status.chars} chars{status.has_embedding ? ', embedded' : ''})
        </span>
      ) : (
        <span className="pr-status pr-none">none</span>
      )}
      <button className="pr-btn" onClick={() => fileInputRef.current?.click()} disabled={busy}>
        {busy ? 'Working…' : status?.has_resume ? 'Replace' : 'Upload PDF'}
      </button>
      {status?.has_resume && (
        <>
          <button className="pr-btn pr-btn-secondary" onClick={handleDownload} disabled={busy}>
            Download
          </button>
          <button className="pr-btn pr-btn-danger" onClick={handleDelete} disabled={busy}>
            Delete
          </button>
        </>
      )}
      {/* Debug is always available — shows empty when no resume. */}
      <button className="pr-btn pr-btn-secondary" onClick={handleDebug} disabled={busy} title="Debug: extracted text + vector">
        🐛 Debug
      </button>
      {error && <span className="pr-error">{error}</span>}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={onFileChange}
        style={{ display: 'none' }}
      />

      {debug && (
        <div className="pr-debug-overlay" onClick={() => setDebug(null)}>
          <div className="pr-debug-modal" onClick={(e) => e.stopPropagation()}>
            <div className="pr-debug-header">
              <span>🐛 Resume debug — {debug.filename || 'resume'} ({debug.chars} chars,
                {' '}embedding dim {debug.embedding_dim})</span>
              <button className="pr-debug-close" onClick={() => setDebug(null)}>✕</button>
            </div>
            <div className="pr-debug-section-label">Extracted text</div>
            <pre className="pr-debug-text">{debug.extracted_text}</pre>
            <div className="pr-debug-section-label">
              Embedding ({debug.embedding_dim} dims{debug.embedding_dim === 0 ? ' — not embedded yet (Step 3)' : ''})
            </div>
            <pre className="pr-debug-text">
              {debug.embedding ? JSON.stringify(debug.embedding) : '(none)'}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfileResume;
