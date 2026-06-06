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

import { runTurn } from './sseTransport.js';
import { extractBearer, verifyToken } from './auth.js';
import { getSession } from './redis.js';

/* global awslambda */
export const handler = awslambda.streamifyResponse(async (event, responseStream, _context) => {
  // --- Auth: verify JWT BEFORE streaming, so we can return a real 401 status.
  // (Once the stream starts, status is locked to 200 — see API_DESIGN.md §15.)
  const headers = event.headers || {};
  let uid;
  try {
    const payload = verifyToken(extractBearer(headers));
    uid = payload.user_id;
  } catch (e) {
    const errStream = awslambda.HttpResponseStream.from(responseStream, {
      statusCode: 401,
      headers: { 'Content-Type': 'application/json' },
    });
    errStream.write(JSON.stringify({ detail: 'Not authenticated' }));
    errStream.end();
    return;
  }

  // Debug/introspection: GET /session?session_id=... → the stored Redis blob.
  // Same production path (JWT → uid → getSession). Function URL puts the path in
  // event.rawPath and query in event.rawQueryString / queryStringParameters.
  const rawPath = event.rawPath || event.requestContext?.http?.path || '';
  const method = event.requestContext?.http?.method || 'POST';
  if (method === 'GET' && rawPath.endsWith('/session')) {
    const sessionId = event.queryStringParameters?.session_id || 'no-session';
    const session = await getSession(uid, sessionId);
    const out = awslambda.HttpResponseStream.from(responseStream, {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
    });
    out.write(JSON.stringify({ uid, session_id: sessionId, session }));
    out.end();
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
  const userMessage = body.message ?? '';

  // Set SSE response metadata (status + headers) before streaming.
  responseStream = awslambda.HttpResponseStream.from(responseStream, {
    statusCode: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  });

  // Shared turn runner — responseStream already matches StreamLike. Identical to local.js.
  await runTurn(responseStream, { uid, sessionId, userMessage });
});
