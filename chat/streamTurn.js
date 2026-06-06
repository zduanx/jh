/**
 * Shared turn-streaming loop — used by BOTH transports (local.js and handler.js).
 *
 * Owns the transport-agnostic logic for one chat turn:
 *   - READ session history from Redis (per-message blob)              [ADR-031]
 *   - build context (summary + recent messages) and run generateResponse() (the seam)
 *   - accumulate the streamed assistant answer
 *   - enforce the total turn budget (graceful timeout → `error` event) [ADR-028]
 *   - honor client disconnect (abort)                                  [ADR-028]
 *   - SAVE the exchange in `finally` — complete or partial (interrupted) [ADR-028/031]
 *
 * The transport supplies:
 *   write(frame)  - send one SSE frame string (res.write / responseStream.write)
 *   isAborted()   - returns true if the client has disconnected
 *
 * Both transports call this, so they share read/generate/save identically — only
 * the transport wrapper differs.
 */

import { sseFrame } from './sse.js';
import { generateResponse } from './generateResponse.js';
import { getSession, saveUserMessage, saveAssistantMessage, buildContext } from './redis.js';

// Total turn budget — graceful application-level timeout. Set BELOW the Lambda
// hard timeout (configured at deploy) so we emit a clean `error` event before
// AWS abruptly kills the invocation. (Per-LLM-call timeouts come in Phase 7.)
export const TURN_BUDGET_MS = 120000; // 2 min

/**
 * Stream one chat turn through the provided write function.
 * @param {(frame: string) => void} write - sends one SSE frame
 * @param {object} opts
 * @param {string|number} opts.uid       - authenticated user id (from JWT)
 * @param {string} opts.sessionId
 * @param {string} opts.userMessage      - the new user message for this turn
 * @param {() => boolean} [opts.isAborted] - true if client disconnected
 */
export async function streamTurn(write, { uid, sessionId, userMessage, isAborted = () => false }) {
  const deadline = Date.now() + TURN_BUDGET_MS;

  // READ: load prior history and build context BEFORE this turn's user message
  // (so the model doesn't see the current question duplicated).
  const session = await getSession(uid, sessionId);
  const history = buildContext(session);

  // SAVE USER message immediately — it's a definite fact, persist before generation
  // so it survives even if the turn fails early. (Industry pattern.) [ADR-031]
  try {
    if (userMessage) await saveUserMessage(uid, sessionId, userMessage);
  } catch (err) {
    console.error('chat: saveUserMessage failed', err);
  }

  let accumulated = '';
  let timedOut = false;

  try {
    for await (const event of generateResponse(sessionId, history)) {
      if (isAborted()) break;
      if (Date.now() > deadline) {
        timedOut = true;
        console.log(`chat: turn budget (${TURN_BUDGET_MS}ms) exceeded for ${sessionId}`);
        write(sseFrame('error', 'turn timed out'));
        break;
      }
      if (event.type === 'token') accumulated += event.data; // accumulate the answer
      write(sseFrame(event.type, event.data));
    }
  } catch (err) {
    console.error('chat: generateResponse error', err);
    if (!isAborted()) write(sseFrame('error', 'internal error'));
  } finally {
    // SAVE ASSISTANT message (best-effort). A partial (abort/timeout) is flagged
    // interrupted; a clean turn is not. Skip if nothing was produced. [ADR-028/031]
    if (accumulated.trim()) {
      try {
        await saveAssistantMessage(uid, sessionId, accumulated, {
          interrupted: isAborted() || timedOut,
        });
      } catch (err) {
        console.error('chat: saveAssistantMessage failed', err);
      }
    }
  }
}
