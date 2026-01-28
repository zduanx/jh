import React from 'react';

/**
 * Stage workflow for the progress stepper.
 * Linear: interested -> applied -> screening -> interview -> reference -> offer
 * Then branches to: accepted OR declined
 * rejected is a terminal state that can happen at any point
 */
const MAIN_STAGES = ['applied', 'screening', 'interview', 'reference', 'offer'];
const TERMINAL_STAGES = ['accepted', 'declined'];

/**
 * ProgressStepper - Horizontal stepper showing job application progress.
 *
 * Visual layout:
 *   o----------o----------o----------o----------o
 * applied  screening  interview  reference   offer
 *                                              +--o accepted
 *                                              +--o declined
 *
 * Props:
 * - currentStage: string - current tracking stage
 * - events: array - list of events with event_type and event_date
 * - isRejected: boolean - whether job is rejected (locks all)
 * - onStageClick: (stageName) => void - callback when stage node is clicked
 */
function ProgressStepper({ currentStage, events = [], isRejected, onStageClick }) {
  // Build a map of completed stages from events
  const completedStages = new Set(events.map((e) => e.event_type));

  // Get current stage index in main flow
  const currentStageIndex = MAIN_STAGES.indexOf(currentStage);
  const isTerminalStage = TERMINAL_STAGES.includes(currentStage);

  // Determine stage state
  const getStageState = (stageName, index) => {
    if (isRejected) return 'locked';
    if (completedStages.has(stageName)) return 'completed';

    // If we're on a terminal stage (accepted/declined), offer is the last completable main stage
    if (isTerminalStage && stageName === 'offer') {
      return completedStages.has('offer') ? 'completed' : 'locked';
    }

    // Next available stage is the one right after current
    if (currentStageIndex >= 0 && index === currentStageIndex + 1) {
      return 'next';
    }
    // If current stage is interested, applied is next
    if (currentStage === 'interested' && index === 0) {
      return 'next';
    }

    return 'locked';
  };

  const getTerminalState = (stageName) => {
    if (isRejected) return 'locked';
    if (completedStages.has(stageName)) return 'completed';

    // Terminal stages are available after offer is completed
    if (completedStages.has('offer') && !completedStages.has('accepted') && !completedStages.has('declined')) {
      return 'next';
    }

    return 'locked';
  };

  const handleClick = (stageName, state) => {
    if (state !== 'locked' && onStageClick) {
      onStageClick(stageName);
    }
  };

  return (
    <div className="trk-stepper">
      {/* Main stages row */}
      <div className="trk-stepper-main">
        {MAIN_STAGES.map((stage, index) => {
          const state = getStageState(stage, index);
          const isLast = index === MAIN_STAGES.length - 1;

          return (
            <React.Fragment key={stage}>
              {/* Stage node */}
              <div
                className={`trk-stepper-node ${state}`}
                onClick={() => handleClick(stage, state)}
                title={stage}
              >
                <div className="trk-stepper-dot" />
                <span className="trk-stepper-label">{stage}</span>
              </div>

              {/* Connector line (except after last) */}
              {!isLast && (
                <div className={`trk-stepper-line ${getStageState(MAIN_STAGES[index + 1], index + 1) === 'locked' ? 'locked' : ''}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Terminal stages (accepted/declined) branching from offer */}
      <div className="trk-stepper-terminal">
        {TERMINAL_STAGES.map((stage) => {
          const state = getTerminalState(stage);
          return (
            <div
              key={stage}
              className={`trk-stepper-node terminal ${state}`}
              onClick={() => handleClick(stage, state)}
              title={stage}
            >
              <div className="trk-stepper-branch-line" />
              <div className="trk-stepper-dot" />
              <span className="trk-stepper-label">{stage}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ProgressStepper;
