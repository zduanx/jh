/**
 * Tests for summarize.js (Phase 7D) — the OFFLINE-testable parts.
 *
 * Run: npm test   (from chat/)
 *
 * The LLM call itself (summarizeConversation) needs a key + costs money, so it's
 * exercised manually / in the E2E. Here we test renderMessage — the pure logic
 * that flattens stored messages (incl. tool_use / tool_result blocks) into the
 * transcript fed to the summarizer. Getting block rendering wrong would silently
 * feed garbage to the summary, so it's worth locking down.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { renderMessage } from '../summarize.js';

test('renders a plain string message as "role: content"', () => {
  assert.equal(renderMessage({ role: 'user', content: 'best jobs for me?' }), 'user: best jobs for me?');
});

test('renders an assistant tool_use block', () => {
  const m = {
    role: 'assistant',
    content: [{ type: 'tool_use', id: 'tu1', name: 'search_jobs_semantic', input: { limit: 5 } }],
  };
  const out = renderMessage(m);
  assert.match(out, /^assistant:/);
  assert.match(out, /called search_jobs_semantic/);
  assert.match(out, /"limit":5/);
});

test('renders a tool_result block', () => {
  const m = {
    role: 'user',
    content: [{ type: 'tool_result', tool_use_id: 'tu1', content: '[{"title":"SRE"}]' }],
  };
  const out = renderMessage(m);
  assert.match(out, /tool result:/);
  assert.match(out, /SRE/);
});

test('renders mixed text + tool blocks', () => {
  const m = {
    role: 'assistant',
    content: [
      { type: 'text', text: 'Let me check.' },
      { type: 'tool_use', id: 't', name: 'get_resume', input: {} },
    ],
  };
  const out = renderMessage(m);
  assert.match(out, /Let me check\./);
  assert.match(out, /called get_resume/);
});
