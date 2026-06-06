/**
 * Shared turn-streaming loop — used by BOTH transports (local.js and handler.js).
 *
 * Contains the transport-agnostic logic for one chat turn:
 *   - consume the generateResponse() seam (the event stream)
 *   - enforce the total turn budget (graceful timeout → `error` event)  [ADR-028]
 *   - honor client disconnect (abort)                                   [ADR-028]
 *   - emit a graceful `error` on internal failure
 *
 * The transport supplies:
 *   write(frame)  - send one SSE frame string (res.write / responseStream.write)
 *   isAborted()   - returns true if the client has disconnected
 *
 * This keeps the local Node server and the AWS Lambda handler identical in
 * behavior — only the transport wrapper differs.
 */

import { sseFrame } from './sse.js';
import { generateResponse } from './generateResponse.js';

// Total turn budget — graceful application-level timeout. Set BELOW the Lambda
// hard timeout (configured at deploy) so we emit a clean `error` event before
// AWS abruptly kills the invocation. (Per-LLM-call timeouts come in Phase 7.)
export const TURN_BUDGET_MS = 120000; // 2 min

/**
 * Stream one chat turn through the provided write function.
 * @param {(frame: string) => void} write - sends one SSE frame
 * @param {object} opts
 * @param {string} opts.sessionId
 * @param {Array}  [opts.history]
 * @param {() => boolean} [opts.isAborted] - true if client disconnected
 */
export async function streamTurn(write, { sessionId, history = [], isAborted = () => false }) {
  const deadline = Date.now() + TURN_BUDGET_MS;

  try {
    for await (const event of generateResponse(sessionId, history)) {
      if (isAborted()) break;
      if (Date.now() > deadline) {
        console.log(`chat: turn budget (${TURN_BUDGET_MS}ms) exceeded for ${sessionId}`);
        write(sseFrame('error', 'turn timed out'));
        break;
      }
      write(sseFrame(event.type, event.data));
    }
  } catch (err) {
    console.error('chat: generateResponse error', err);
    if (!isAborted()) write(sseFrame('error', 'internal error'));
  }
}
