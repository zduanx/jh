/**
 * JWT auth for the chat service.
 *
 * Verifies the same JWT the Python backend issues (HS256, shared SECRET_KEY).
 * Since the chat Function URL is AuthType: NONE (public), the handler MUST verify
 * the token itself before doing any work — otherwise the endpoint is open and,
 * in Phase 7, anyone could run up the LLM bill.
 *
 * Token transport: Authorization: Bearer <jwt> (industry standard for APIs).
 * The chatbox is POST + fetch-based streaming, so there is no EventSource
 * header limitation — no need for a ?token= query param.
 */

import jwt from 'jsonwebtoken';

// NOTE: read env at CALL time, not module-load time. With ES modules, imports are
// hoisted/evaluated before the importer's body runs — so reading process.env here
// at load time would capture values before local.js's loadEnvFile() executes.

/**
 * Extract the Bearer token from request headers (case-insensitive).
 * @param {object} headers - header map (lowercased keys, as Lambda/Node provide)
 * @returns {string|null}
 */
export function extractBearer(headers = {}) {
  // Lambda Function URL lowercases header names; Node http does too via req.headers.
  const auth = headers['authorization'] || headers['Authorization'] || '';
  const m = /^Bearer\s+(.+)$/i.exec(auth);
  return m ? m[1].trim() : null;
}

/**
 * Verify a JWT. Returns the decoded payload, or throws on invalid/expired/missing.
 * @param {string|null} token
 * @returns {object} decoded payload (e.g. { user_id, email, ... })
 */
export function verifyToken(token) {
  const secretKey = process.env.SECRET_KEY;
  const algorithm = process.env.ALGORITHM || 'HS256';
  if (!secretKey) {
    // Misconfiguration — fail closed.
    throw new Error('SECRET_KEY not configured');
  }
  if (!token) {
    throw new Error('missing token');
  }
  // jsonwebtoken checks signature AND exp; throws TokenExpiredError / JsonWebTokenError.
  return jwt.verify(token, secretKey, { algorithms: [algorithm] });
}
