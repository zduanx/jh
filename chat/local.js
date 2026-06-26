/**
 * Local dev server for the Job Hunt chat service (Phase 6A).
 *
 * Minimal Node HTTP server — no dependencies. Lets us curl the service
 * locally before wiring streaming, Redis, or deploying to a Lambda Function URL.
 *
 * Run:   node chat/local.js     (or: jbenode)
 * Test:  curl http://localhost:8100/health
 *        curl -X POST http://localhost:8100/chat -d '{"session_id":"t1","message":"hi"}'
 */

import http from 'node:http';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { runTurn, adaptNodeRes } from './sseTransport.js';
import { extractBearer, verifyToken } from './auth.js';
import { getSession } from './redis.js';

// Load .env.local for local dev (Lambda does NOT use this — its env comes from
// the Terraform-set Lambda env vars). Phase 9B: prefer the UNIFIED ROOT .env.local
// (one source for all stacks); fall back to the legacy per-stack chat/.env.local.
const __dir = dirname(fileURLToPath(import.meta.url));
const rootEnvLocal = join(__dir, '..', '.env.local');
const stackEnvLocal = join(__dir, '.env.local');
const envLocal = fs.existsSync(rootEnvLocal) ? rootEnvLocal : stackEnvLocal;
if (fs.existsSync(envLocal)) {
  process.loadEnvFile(envLocal);
}

const PORT = process.env.CHAT_PORT || 8100;

// CORS headers — the React dev server (localhost:3000) calls this server cross-origin.
// Allow the same origin the backend already allows (ALLOWED_ORIGINS, first entry).
const CORS = {
  'Access-Control-Allow-Origin': (process.env.ALLOWED_ORIGINS || 'http://localhost:3000').split(',')[0],
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

function sendJson(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(data),
    ...CORS,
  });
  res.end(data);
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString('utf8');
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { _parseError: true, _raw: raw };
  }
}

const server = http.createServer(async (req, res) => {
  const { method, url } = req;

  // CORS preflight — the browser sends OPTIONS before a cross-origin request
  // that carries an Authorization header. Answer it with the allow-headers.
  if (method === 'OPTIONS') {
    res.writeHead(204, CORS);
    return res.end();
  }

  // Health check
  if (method === 'GET' && url === '/health') {
    return sendJson(res, 200, { status: 'healthy', service: 'jh-chat' });
  }

  // Debug/introspection: return the stored session blob for the authenticated
  // user. Uses the SAME production path (verify JWT → uid → getSession from Redis)
  // so it reflects exactly what the chat turn reads/writes.
  // GET /session?session_id=...
  if (method === 'GET' && url.startsWith('/session')) {
    let uid;
    try {
      uid = verifyToken(extractBearer(req.headers)).user_id;
    } catch (e) {
      return sendJson(res, 401, { detail: 'Not authenticated' });
    }
    const sessionId = new URL(url, `http://localhost:${PORT}`).searchParams.get('session_id') || 'no-session';
    const session = await getSession(uid, sessionId);
    return sendJson(res, 200, { uid, session_id: sessionId, session });
  }

  // Chat — streams the turn as SSE by consuming the generateResponse seam.
  if (method === 'POST' && url === '/chat') {
    // Auth: verify JWT before streaming (return 401 before status is locked to 200).
    let uid;
    try {
      const payload = verifyToken(extractBearer(req.headers));
      uid = payload.user_id;
    } catch (e) {
      return sendJson(res, 401, { detail: 'Not authenticated' });
    }

    const body = await readBody(req);
    const sessionId = body.session_id ?? 'no-session';
    const userMessage = body.message ?? '';

    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      ...CORS,
    });

    // Shared turn runner over an adapted stream — identical to handler.js.
    await runTurn(adaptNodeRes(res), { uid, sessionId, userMessage });
    return;
  }

  return sendJson(res, 404, { detail: 'Not Found' });
});

server.listen(PORT, () => {
  console.log(`jh-chat local server listening on http://localhost:${PORT}`);
  console.log(`  GET  /health`);
  console.log(`  POST /chat`);
});
