import React, { useState, useEffect, useCallback } from 'react';
import './IngestPage.css';
import Stage1Configure, { Stage1ActionBar } from './ingest/Stage1Configure';
import Stage2Preview, { Stage2ActionBar } from './ingest/Stage2Preview';
import Stage3Progress from './ingest/Stage3Progress';

const STAGES = [
  { id: 1, name: 'Configure', description: 'Select companies & filters' },
  { id: 2, name: 'Preview', description: 'Review extracted URLs' },
  { id: 3, name: 'Ingest', description: 'Sync & process jobs' },
];

function IngestPage() {
  const [currentStage, setCurrentStage] = useState(1);
  const [companies, setCompanies] = useState([]);
  const [savedSettings, setSavedSettings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dbMode, setDbMode] = useState(null); // 'TEST' or 'PRODUCTION'
  const [activeRunId, setActiveRunId] = useState(null);
  const [startingIngestion, setStartingIngestion] = useState(false);

  // Action bar state - passed up from stage components
  const [actionBarState, setActionBarState] = useState({});

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

  // Check for active ingestion run on mount (for page refresh)
  useEffect(() => {
    const checkCurrentRun = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      try {
        const res = await fetch(`${apiUrl}/api/ingestion/current-run`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.run_id) {
            setActiveRunId(data.run_id);
            setCurrentStage(3);
          }
        }
      } catch {
        // Ignore errors - just start at stage 1
      }
    };
    checkCurrentRun();
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

  // Start ingestion - called from Stage 2 confirm
  const handleStartIngestion = async () => {
    setStartingIngestion(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${apiUrl}/api/ingestion/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to start ingestion');
      }

      const data = await res.json();
      setActiveRunId(data.run_id);
      setCurrentStage(3);
    } catch (err) {
      setError(err.message);
    } finally {
      setStartingIngestion(false);
    }
  };

  // Handle abort from Stage 3
  const handleAbort = () => {
    setActiveRunId(null);
    setCurrentStage(1);
  };

  // Render action bar based on current stage
  const renderActionBar = () => {
    switch (currentStage) {
      case 1:
        return (
          <Stage1ActionBar
            {...actionBarState}
            onNext={() => setCurrentStage(2)}
          />
        );
      case 2:
        return (
          <Stage2ActionBar
            {...actionBarState}
            onBack={() => setCurrentStage(1)}
            onNext={() => setCurrentStage(3)}
          />
        );
      default:
        return null;
    }
  };

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
            onActionBarChange={setActionBarState}
          />
        );
      case 2:
        // Build enabled companies list for Stage 2
        const enabledCompanies = savedSettings
          .filter(s => s.is_enabled !== false)
          .map(s => {
            const company = companies.find(c => c.name === s.company_name);
            return {
              company_name: s.company_name,
              display_name: company?.display_name || s.company_name,
              logo_url: company?.logo_url,
              title_filters: s.title_filters || { include: [], exclude: [] },
            };
          })
          .sort((a, b) => a.display_name.localeCompare(b.display_name));

        return (
          <Stage2Preview
            companies={enabledCompanies}
            savedSettings={savedSettings}
            onSettingsUpdate={setSavedSettings}
            onActionBarChange={setActionBarState}
            onNext={handleStartIngestion}
            startingIngestion={startingIngestion}
          />
        );
      case 3:
        return (
          <Stage3Progress
            runId={activeRunId}
            onAbort={handleAbort}
          />
        );
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
      <div className="stage-wrapper">
        {renderActionBar() && (
          <div className="ingest-action-bar">
            {renderActionBar()}
          </div>
        )}
        {renderStageContent()}
      </div>
    </div>
  );
}

export default IngestPage;
