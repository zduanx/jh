/**
 * Chat SSE streaming client (fetch + ReadableStream).
 *
 * The chat endpoint is POST + Authorization header, so native EventSource (GET-only,
 * no custom headers) can't be used. This is the industry-standard approach for
 * POST-based SSE (how ChatGPT's web client / Vercel AI SDK / the Anthropic+OpenAI
 * JS SDKs stream): read response.body as a stream and parse SSE frames manually.
 *
 * Event protocol (see API_DESIGN.md §15): step / token / done / error.
 */

/**
 * Stream a chat turn. Calls onEvent({type, data}) for each SSE event.
 * Resolves when the stream ends. Returns an AbortController so the caller can stop it.
 *
 * @param {object} opts
 * @param {string} opts.chatUrl    - chat Function URL base
 * @param {string} opts.token      - JWT
 * @param {string} opts.sessionId
 * @param {string} opts.message
 * @param {(evt: {type:string, data:string}) => void} opts.onEvent
 * @returns {Promise<void>}
 */
export async function streamChatTurn({ chatUrl, token, sessionId, message, onEvent, signal }) {
  const res = await fetch(`${chatUrl}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });

  if (!res.ok) {
    // Auth or pre-stream error returns a normal JSON error (status not 200).
    onEvent({ type: 'error', data: `request failed (${res.status})` });
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let sawDone = false;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line ("\n\n").
    let sep;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const evt = parseFrame(frame);
      if (evt) {
        if (evt.type === 'done') sawDone = true;
        onEvent(evt);
      }
    }
  }

  // Stream closed without an explicit done/error → treat as interrupted.
  // (HTTP 200 means "stream opened", not "succeeded" — see API_DESIGN.md §15.)
  if (!sawDone) {
    onEvent({ type: 'interrupted', data: 'stream ended without completion' });
  }
}

/** Parse one SSE frame ("event: X\ndata: ...") into {type, data}. */
function parseFrame(frame) {
  let event = 'message';
  const dataLines = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
  }
  if (dataLines.length === 0) return null;
  return { type: event, data: dataLines.join('\n') };
}

/** Fetch the stored session (history) via the GET /session debug endpoint. */
export async function fetchSession({ chatUrl, token, sessionId }) {
  const res = await fetch(`${chatUrl}/session?session_id=${encodeURIComponent(sessionId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json();
}
