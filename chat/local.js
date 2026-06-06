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
import { streamTurn } from './streamTurn.js';
import { extractBearer, verifyToken } from './auth.js';
import { getSession } from './redis.js';

// Load .env.local for local dev (Lambda does NOT use this — its env comes from
// the SAM template / deploy). Uses Node's built-in env-file loader (no deps).
const __dir = dirname(fileURLToPath(import.meta.url));
const envLocal = join(__dir, '.env.local');
if (fs.existsSync(envLocal)) {
  process.loadEnvFile(envLocal);
}

const PORT = process.env.CHAT_PORT || 8100;

function sendJson(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(data),
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
    });

    // If the client disconnects, stop producing (ADR-028: interruption aborts).
    // Use res.on('close') — the response socket closing is the reliable
    // disconnect signal for a streaming response (req 'close' does not fire
    // dependably once the request body has been consumed).
    let aborted = false;
    res.on('close', () => {
      if (!res.writableEnded) {
        aborted = true;
        console.log(`chat: client disconnected, aborting turn for ${sessionId}`);
      }
    });

    // Shared turn logic: read history (Redis) → generate → save (budget/abort/error).
    await streamTurn((frame) => res.write(frame), {
      uid,
      sessionId,
      userMessage,
      isAborted: () => aborted,
    });
    res.end();
    return;
  }

  return sendJson(res, 404, { detail: 'Not Found' });
});

server.listen(PORT, () => {
  console.log(`jh-chat local server listening on http://localhost:${PORT}`);
  console.log(`  GET  /health`);
  console.log(`  POST /chat`);
});
