import React, { useState, useEffect, useCallback } from 'react';
import './IngestPage.css';
import Stage1Configure from './ingest/Stage1Configure';

const STAGES = [
  { id: 1, name: 'Configure', description: 'Select companies & filters' },
  { id: 2, name: 'Preview', description: 'Review extracted URLs' },
  { id: 3, name: 'Archive', description: 'Snapshot job pages' },
  { id: 4, name: 'Ingest', description: 'Process into database' },
  { id: 5, name: 'Results', description: 'View summary' },
];

function IngestPage() {
  const [currentStage, setCurrentStage] = useState(1);
  const [companies, setCompanies] = useState([]);
  const [savedSettings, setSavedSettings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dbMode, setDbMode] = useState(null); // 'TEST' or 'PRODUCTION'

  const apiUrl = process.env.REACT_APP_API_URL;

  // Fetch database mode (for dev indicator)
  useEffect(() => {
    const fetchDbMode = async () => {
      try {
        const res = await fetch(`${apiUrl}/debug/db`);
        if (res.ok) {
          const data = await res.json();
          setDbMode(data.database_type);
        }
      } catch {
        // Ignore errors - indicator just won't show
      }
    };
    fetchDbMode();
  }, [apiUrl]);

  // Fetch companies and settings on mount
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('access_token');

      // Fetch companies (public endpoint)
      const companiesRes = await fetch(`${apiUrl}/api/ingestion/companies`);
      if (!companiesRes.ok) throw new Error('Failed to fetch companies');
      const companiesData = await companiesRes.json();
      // Sort alphabetically by display_name
      companiesData.sort((a, b) => a.display_name.localeCompare(b.display_name));
      setCompanies(companiesData);

      // Fetch settings (authenticated - may fail if not logged in)
      if (token) {
        try {
          const settingsRes = await fetch(`${apiUrl}/api/ingestion/settings`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (settingsRes.ok) {
            const settingsData = await settingsRes.json();
            setSavedSettings(settingsData);
          } else {
            setSavedSettings([]);
          }
        } catch {
          setSavedSettings([]);
        }
      } else {
        setSavedSettings([]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Render stepper
  const renderStepper = () => (
    <div className="stepper">
      {STAGES.map((stage, index) => {
        const isActive = stage.id === currentStage;
        const isCompleted = stage.id < currentStage;
        const isLocked = stage.id > currentStage;

        return (
          <React.Fragment key={stage.id}>
            <div className={`step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isLocked ? 'locked' : ''}`}>
              <div className="step-circle">
                {isCompleted ? '✓' : stage.id}
              </div>
              <div className="step-info">
                <span className="step-name">{stage.name}</span>
                <span className="step-description">{stage.description}</span>
              </div>
            </div>
            {index < STAGES.length - 1 && <div className="step-connector" />}
          </React.Fragment>
        );
      })}
    </div>
  );

  // Placeholder for future stages
  const renderComingSoon = (stageName) => (
    <div className="stage-content coming-soon">
      <div className="coming-soon-icon">🚧</div>
      <h2>{stageName}</h2>
      <p>This stage is under development.</p>
      <button className="back-btn" onClick={() => setCurrentStage(1)}>
        ← Back to Configure
      </button>
    </div>
  );

  // Render current stage content
  const renderStageContent = () => {
    switch (currentStage) {
      case 1:
        return (
          <Stage1Configure
            companies={companies}
            savedSettings={savedSettings}
            loading={loading}
            error={error}
            onError={setError}
            onSettingsUpdate={setSavedSettings}
            onNext={() => setCurrentStage(2)}
          />
        );
      case 2:
        return renderComingSoon('Preview');
      case 3:
        return renderComingSoon('Archive');
      case 4:
        return renderComingSoon('Ingest');
      case 5:
        return renderComingSoon('Results');
      default:
        return renderComingSoon('Unknown Stage');
    }
  };

  return (
    <div className="ingest-container">
      <div className="ingest-header">
        <h1>
          Job Ingestion
          {dbMode && dbMode !== 'PRODUCTION' && (
            <span className="db-mode-badge">{dbMode} DB</span>
          )}
        </h1>
        <p>Extract and import job postings from company career pages</p>
      </div>

      {renderStepper()}
      {renderStageContent()}
    </div>
  );
}

export default IngestPage;
