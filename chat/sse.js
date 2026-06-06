/**
 * SSE (Server-Sent Events) formatting helpers.
 *
 * Event protocol (Phase 6 — unified, see API_DESIGN.md §15):
 *   step  - what the AI is doing now (includes the initial "thinking" state); text
 *   token - a chunk of the final answer
 *   done  - turn complete; { session_id }
 *   error - failure; error string
 *
 * The frontend shows "processing" by default on send (no event) until the first event arrives.
 */

/**
 * Format a single SSE event frame.
 * @param {string} event - event name (step|token|done|error)
 * @param {string|object} data - string sent as-is; object is JSON-stringified
 * @returns {string} the SSE frame ("event: ...\ndata: ...\n\n")
 */
export function sseFrame(event, data) {
  const payload = typeof data === 'string' ? data : JSON.stringify(data);
  // Guard against multi-line strings breaking the SSE format: prefix each line with "data: ".
  const dataLines = payload
    .split('\n')
    .map((line) => `data: ${line}`)
    .join('\n');
  return `event: ${event}\n${dataLines}\n\n`;
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
