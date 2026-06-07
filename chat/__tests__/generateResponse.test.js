/**
 * Tests for generateResponse.js wiring (Phase 7C, Step 3) — the uid-injection
 * contract of the tools surface.
 *
 * Run: npm test   (from chat/)
 *
 * Fully OFFLINE: we inject stubbed MCP functions (no server) and assert the
 * critical security contract from ADR-033 — the authenticated uid is injected as
 * `user_id` into EVERY tool call, and the model's args can't override it.
 *
 * (The full agent path — real Claude + real MCP streaming a grounded answer — is
 * the live E2E test, which needs ANTHROPIC_API_KEY + a running MCP server.)
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { buildTools } from '../generateResponse.js';

/** Stub MCP deps that record every callTool invocation. */
function stubDeps(toolList = [{ name: 'get_resume', description: 'd', inputSchema: { type: 'object', properties: {} } }]) {
  const calls = [];
  return {
    calls,
    deps: {
      async connect() {
        return { async close() {} };
      },
      async listTools() {
        return toolList;
      },
      async callTool(_client, name, args) {
        calls.push({ name, args });
        return { ok: true };
      },
    },
  };
}

test('buildTools injects uid as user_id on every call', async () => {
  const { calls, deps } = stubDeps();
  const tools = await buildTools(42, deps);

  await tools.call('get_resume', {});
  await tools.call('search_jobs_semantic', { limit: 5 });

  assert.equal(calls.length, 2);
  assert.equal(calls[0].args.user_id, 42, 'uid injected on first call');
  assert.equal(calls[1].args.user_id, 42, 'uid injected on second call');
  assert.equal(calls[1].args.limit, 5, 'model-supplied args preserved');
});

test('model-supplied user_id cannot override the authenticated uid', async () => {
  const { calls, deps } = stubDeps();
  const tools = await buildTools(7, deps);

  // A malicious/confused model tries to pass someone else's id.
  await tools.call('get_resume', { user_id: 999 });

  assert.equal(calls[0].args.user_id, 7, 'authenticated uid wins (injected last)');
});

test('buildTools exposes Anthropic-format schemas (input_schema, not inputSchema)', async () => {
  const { deps } = stubDeps();
  const tools = await buildTools(1, deps);

  assert.equal(tools.schemas.length, 1);
  assert.ok('input_schema' in tools.schemas[0], 'converted to Anthropic key');
  assert.ok(!('inputSchema' in tools.schemas[0]), 'MCP key removed');
});
