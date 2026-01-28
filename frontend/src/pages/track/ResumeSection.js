import { useRef, useState } from 'react';
import { MdUpload, MdDownload, MdVisibility } from 'react-icons/md';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * ResumeSection - Upload, download, and preview resume for a tracked job.
 *
 * Re-uploading a resume overwrites the existing file (no delete needed).
 *
 * Props:
 * - trackingId: number - tracking ID
 * - hasResume: boolean - whether a resume is uploaded
 * - resumeFilename: string | null - original filename (from notes.resume_filename)
 * - onUpload: (trackingId, file) => Promise - upload callback (re-upload overwrites)
 * - disabled: boolean - disable actions
 */
function ResumeSection({
  trackingId,
  hasResume,
  resumeFilename,
  onUpload,
  disabled,
}) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);

  const [isLoadingUrl, setIsLoadingUrl] = useState(false);

  const handleUploadClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !onUpload) return;

    // Validate file type (PDF only for now)
    if (file.type !== 'application/pdf') {
      alert('Please upload a PDF file');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('File size must be less than 5MB');
      return;
    }

    setIsUploading(true);
    try {
      await onUpload(trackingId, file);
    } catch (err) {
      console.error('Failed to upload resume:', err);
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      // Reset input so same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Get presigned URL from backend and open in new tab
  const handlePreview = async () => {
    if (!hasResume) return;

    setIsLoadingUrl(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/api/tracked/${trackingId}/resume/url`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Failed to get resume URL');
      }

      const { url } = await response.json();
      window.open(url, '_blank');
    } catch (err) {
      console.error('Failed to preview resume:', err);
      alert(`Preview failed: ${err.message}`);
    } finally {
      setIsLoadingUrl(false);
    }
  };

  // Get presigned URL and trigger download
  const handleDownload = async () => {
    if (!hasResume) return;

    setIsLoadingUrl(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/api/tracked/${trackingId}/resume/url?download=true`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Failed to get resume URL');
      }

      const { url } = await response.json();

      // Create a temporary link to trigger download
      const link = document.createElement('a');
      link.href = url;
      link.download = resumeFilename || 'resume.pdf';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Failed to download resume:', err);
      alert(`Download failed: ${err.message}`);
    } finally {
      setIsLoadingUrl(false);
    }
  };

  return (
    <div className="trk-resume-section">
      <div className="trk-resume-header">
        <h4>Resume</h4>
      </div>

      <div className="trk-resume-content">
        {hasResume ? (
          <>
            <span className="trk-resume-filename" title={resumeFilename}>
              {resumeFilename || 'resume.pdf'}
            </span>
            <div className="trk-resume-actions">
              <button
                className="trk-resume-btn preview"
                onClick={handlePreview}
                disabled={disabled || isLoadingUrl}
                title="Preview in new tab"
              >
                <MdVisibility size={16} />
              </button>
              <button
                className="trk-resume-btn download"
                onClick={handleDownload}
                disabled={disabled || isLoadingUrl}
                title="Download"
              >
                <MdDownload size={16} />
              </button>
              <button
                className="trk-resume-btn upload"
                onClick={handleUploadClick}
                disabled={disabled || isUploading}
                title="Replace resume"
              >
                <MdUpload size={16} />
              </button>
            </div>
          </>
        ) : (
          <button
            className="trk-resume-upload-btn"
            onClick={handleUploadClick}
            disabled={disabled || isUploading}
          >
            <MdUpload size={18} />
            {isUploading ? 'Uploading...' : 'Upload Resume'}
          </button>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
    </div>
  );
}

export default ResumeSection;
