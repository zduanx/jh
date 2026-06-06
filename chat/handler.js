/**
 * AWS Lambda handler for the chat service (Phase 6A).
 *
 * The AWS transport — parallel to local.js, sharing all core logic:
 *   sse.js            (sseFrame)         — shared
 *   generateResponse  (the mock seam)    — shared
 *   streamTurn        (budget/abort loop)— shared
 * Only the transport differs: Lambda response streaming via
 * `awslambda.streamifyResponse` + `responseStream`, instead of Node's http `res`.
 *
 * Deployed behind a Lambda Function URL in RESPONSE_STREAM invoke mode (set in
 * the SAM template) — this is what allows turns to stream for >30s, bypassing
 * the API Gateway 30s cap and Mangum buffering. See ADR-025.
 *
 * `awslambda` is a global injected by the Lambda Node runtime (not importable);
 * it only exists when running inside AWS, which is why this file is exercised by
 * deploy, while local.js covers local dev.
 */

import { streamTurn } from './streamTurn.js';
import { sseFrame } from './sse.js';
import { extractBearer, verifyToken } from './auth.js';

/* global awslambda */
export const handler = awslambda.streamifyResponse(async (event, responseStream, _context) => {
  // --- Auth: verify JWT BEFORE streaming, so we can return a real 401 status.
  // (Once the stream starts, status is locked to 200 — see API_DESIGN.md §15.)
  const headers = event.headers || {};
  try {
    verifyToken(extractBearer(headers));
  } catch (e) {
    const errStream = awslambda.HttpResponseStream.from(responseStream, {
      statusCode: 401,
      headers: { 'Content-Type': 'application/json' },
    });
    errStream.write(JSON.stringify({ detail: 'Not authenticated' }));
    errStream.end();
    return;
  }

  // Function URL delivers the HTTP request in `event`. Parse the JSON body
  // (it may be base64-encoded depending on content type).
  let body = {};
  try {
    const raw = event.isBase64Encoded
      ? Buffer.from(event.body || '', 'base64').toString('utf8')
      : event.body || '';
    body = raw ? JSON.parse(raw) : {};
  } catch {
    body = {};
  }

  const sessionId = body.session_id ?? 'no-session';
  const history = []; // Phase 6B: load from Redis.

  // Set SSE response metadata (status + headers) before streaming.
  responseStream = awslambda.HttpResponseStream.from(responseStream, {
    statusCode: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  });

  // Client-disconnect abort (ADR-028): the response stream errors/closes when
  // the client goes away.
  let aborted = false;
  responseStream.on('error', () => {
    aborted = true;
  });
  responseStream.on('close', () => {
    aborted = true;
  });

  try {
    await streamTurn((frame) => responseStream.write(frame), {
      sessionId,
      history,
      isAborted: () => aborted,
    });
  } catch (err) {
    console.error('chat handler error', err);
    if (!aborted) {
      try {
        responseStream.write(sseFrame('error', 'internal error'));
      } catch {
        /* stream already gone */
      }
    }
  } finally {
    responseStream.end();
  }
});
