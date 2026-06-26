/**
 * Tests for mcpClient.js — the chat agent's MCP client (Phase 7C, Step 1).
 *
 * Run: npm test          (from chat/)   — node --test
 *  or: node --test chat/__tests__/mcpClient.test.js
 *
 * Two layers:
 *   - OFFLINE (always run): fail-closed config checks — no server needed.
 *   - LIVE (auto-skip if unreachable): a real Node→Python MCP round trip against
 *     the LOCAL server (`jbemcp` on $MCP_SERVER_URL). Proves the boundary works:
 *     initialize handshake, tools/list, tools/call. Skips (does not fail) when the
 *     server isn't running, so the suite is safe in CI / when MCP is down.
 *
 * Env: loads chat/.env.local (same as local.js) for MCP_SERVER_URL + MCP_SERVICE_TOKEN.
 *
 * Note: the LOCAL jbemcp server has NO auth middleware, so a 401-on-bad-token can't
 * be proven here — that path is covered server-side by the Python suite
 * (backend/mcp_server/__tests__/test_auth_middleware.py) and only manifests against
 * the deployed Lambda. Here we prove the client SENDS the bearer + fails closed.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { connect, listTools, callTool, withMcpSession } from '../mcpClient.js';

// Load .env.local exactly like local.js does (built-in loader, no deps).
const __dir = dirname(fileURLToPath(import.meta.url));
const envLocal = join(__dir, '..', '.env.local');
if (fs.existsSync(envLocal)) process.loadEnvFile(envLocal);

const EXPECTED_TOOLS = ['get_job', 'get_resume', 'score_against_jd', 'search_jobs_semantic'];

/** Is the local MCP server reachable? Probe /mcp; any HTTP reply means "up". */
async function serverReachable() {
  const base = process.env.MCP_SERVER_URL;
  if (!base) return false;
  try {
    const res = await fetch(new URL('/mcp', base), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
      signal: AbortSignal.timeout(1500),
    });
    return res.status > 0; // got an HTTP response → server is listening
  } catch {
    return false;
  }
}

// --------------------------------------------------------------------------- //
// OFFLINE — fail-closed config (no server needed)
// --------------------------------------------------------------------------- //
test('connect() fails closed when MCP_SERVER_URL is missing', async () => {
  const saved = process.env.MCP_SERVER_URL;
  delete process.env.MCP_SERVER_URL;
  try {
    await assert.rejects(connect(), /MCP_SERVER_URL not configured/);
  } finally {
    if (saved !== undefined) process.env.MCP_SERVER_URL = saved;
  }
});

test('connect() fails closed when MCP_SERVICE_TOKEN is missing', async () => {
  // Hermetic: connect() checks MCP_SERVER_URL *before* the token, so set a dummy
  // URL to reach the token check (otherwise in a clean env — e.g. CI — this fails
  // on the URL check first and never exercises the token path under test).
  const savedUrl = process.env.MCP_SERVER_URL;
  const savedToken = process.env.MCP_SERVICE_TOKEN;
  process.env.MCP_SERVER_URL = 'http://localhost:9999/mcp';
  delete process.env.MCP_SERVICE_TOKEN;
  try {
    await assert.rejects(connect(), /MCP_SERVICE_TOKEN not configured/);
  } finally {
    if (savedUrl !== undefined) process.env.MCP_SERVER_URL = savedUrl;
    else delete process.env.MCP_SERVER_URL;
    if (savedToken !== undefined) process.env.MCP_SERVICE_TOKEN = savedToken;
  }
});

// --------------------------------------------------------------------------- //
// LIVE — real round trip (auto-skip if the local server isn't running)
// --------------------------------------------------------------------------- //
test('live MCP round trip (needs jbemcp on MCP_SERVER_URL)', async (t) => {
  if (!(await serverReachable())) {
    t.skip(`MCP server not reachable at ${process.env.MCP_SERVER_URL || '(unset)'} — start it with jbemcp`);
    return;
  }

  await withMcpSession(async (client) => {
    // tools/list — all four discovered, with schemas
    const tools = await listTools(client);
    const names = tools.map((x) => x.name).sort();
    assert.deepEqual(names, EXPECTED_TOOLS, 'all four tools discovered');

    const search = tools.find((x) => x.name === 'search_jobs_semantic');
    assert.ok(search.description && search.description.length > 20, 'description carried through');
    assert.ok(
      'company' in (search.inputSchema?.properties ?? {}),
      'documented param present in schema',
    );

    // tools/call — RPC round trip. user_id with no resume → null (proves the path).
    const res = await callTool(client, 'get_resume', { user_id: 999999 });
    assert.equal(res, null, 'get_resume for a nonexistent user returns null');
  });
});
