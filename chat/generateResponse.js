/**
 * THE SEAM.
 *
 * generateResponse(sessionId, history) is the single interface between the
 * transport layer (Function URL handler / local server) and the response logic.
 *
 * Phase 6: this is a MOCK — it streams a ~50s turn (step events for ~40s, then
 * token-by-token mock answer for ~10s) to prove >30s streaming works, with no AI.
 * The mock is OBSERVABLE: it reports how many prior messages it received, so the
 * plumbing (history wiring, session keying) is verifiable headless via curl.
 *
 * Phase 7: replace ONLY the body of this generator with the real agent loop
 * (stop_reason loop, MCP tool calls, LLM token streaming). The signature and the
 * event types it yields stay identical, so the transport + frontend don't change.
 *
 * Yields events of shape: { type: 'step'|'token'|'done', data: string|object }
 *
 * Timings are hardcoded to produce a ~50s turn (the >30s streaming proof):
 *   1 (thinking) + 7 steps * 5s = 40s of steps, then ~10s of tokens ≈ 50s.
 * To iterate faster locally, temporarily lower these constants.
 */

import { sleep } from './sse.js';

const STEP_MS = 5000; // delay between step events
const NUM_STEPS = 7; // "doing" steps after the initial thinking step
const TOKEN_MS = 250; // delay between answer tokens

// Mock "doing" steps (Phase 7 will emit real agent steps here).
const MOCK_STEPS = [
  'searching jobs',
  'reading the job description',
  'loading your resume',
  'comparing requirements',
  'scoring against your background',
  'ranking matches',
  'drafting the answer',
];

export async function* generateResponse(sessionId, history = []) {
  // Observable: prove history + session wiring without a frontend.
  yield { type: 'step', data: `thinking… (loaded ${history.length} prior messages for session ${sessionId})` };
  await sleep(STEP_MS);

  // ~40s of intermediate steps.
  for (let i = 0; i < NUM_STEPS; i++) {
    const step = MOCK_STEPS[i % MOCK_STEPS.length];
    yield { type: 'step', data: step };
    await sleep(STEP_MS);
  }

  // ~10s of final-answer tokens, streamed word-by-word.
  const turnNumber = Math.floor(history.length / 2) + 1; // each turn = user+assistant
  const answer =
    `Mock answer #${turnNumber} for session ${sessionId}: ` +
    `this is a placeholder response streamed token-by-token to prove >30s streaming works.`;
  for (const word of answer.split(' ')) {
    yield { type: 'token', data: word + ' ' };
    await sleep(TOKEN_MS);
  }

  yield { type: 'done', data: { session_id: sessionId } };
}
