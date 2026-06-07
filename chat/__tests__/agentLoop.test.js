/**
 * Tests for agentLoop.js — the ReAct loop logic (Phase 7C, Step 2).
 *
 * Run: npm test   (from chat/)
 *
 * Fully OFFLINE: no LLM, no MCP, no network. We inject a STUBBED callModel
 * (scripted model turns) and a FAKE tools surface, and assert the state machine:
 *   - tool_use → end_turn terminates with the streamed answer
 *   - tool_result is fed back to the model (the model sees the observation)
 *   - max-iteration cap fires (a model that always tool_uses can't loop forever)
 *   - a tool error becomes a tool_result (model can recover), not a turn crash
 *   - events map correctly (step for tools, token for answer, done at end)
 *   - abort stops the loop
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { runAgent, DEFAULT_MAX_ITERATIONS } from '../agentLoop.js';

/** Collect all events from the generator into an array. */
async function collect(gen) {
  const out = [];
  for await (const ev of gen) out.push(ev);
  return out;
}

/** Build an async iterable from string chunks (mimics streamed text deltas). */
async function* deltas(...chunks) {
  for (const c of chunks) yield c;
}

/** A fake tools surface that records calls and returns canned results. */
function fakeTools(impl = {}) {
  const calls = [];
  return {
    calls,
    schemas: [{ name: 'search_jobs_semantic' }, { name: 'get_resume' }],
    async call(name, args) {
      calls.push({ name, args });
      if (impl[name]) return impl[name](args);
      return { ok: true, name };
    },
  };
}

// --------------------------------------------------------------------------- //
test('single tool call then final answer: terminates, streams answer, emits done', async () => {
  const tools = fakeTools({ search_jobs_semantic: () => [{ job_id: 1, title: 'SRE' }] });

  // Scripted model: turn 1 asks for a tool, turn 2 gives the final answer.
  let n = 0;
  const callModel = async () => {
    n++;
    if (n === 1) {
      return {
        stopReason: 'tool_use',
        content: [{ type: 'tool_use', id: 'tu1', name: 'search_jobs_semantic', input: { user_id: 5 } }],
      };
    }
    return { stopReason: 'end_turn', content: [], textDeltas: deltas('Your top ', 'match is SRE.') };
  };

  const events = await collect(runAgent({ callModel, tools, system: 's', messages: [] }));

  const types = events.map((e) => e.type);
  assert.deepEqual(types, ['step', 'token', 'token', 'done']);
  assert.equal(events[0].data, 'using search_jobs_semantic');
  assert.equal(events.filter((e) => e.type === 'token').map((e) => e.data).join(''), 'Your top match is SRE.');
  assert.equal(tools.calls.length, 1);
  assert.deepEqual(tools.calls[0], { name: 'search_jobs_semantic', args: { user_id: 5 } });
});

test('tool_result is fed back to the model on the next turn', async () => {
  const tools = fakeTools({ get_resume: () => ({ text: 'RESUME_BODY' }) });
  const seenMessages = [];

  let n = 0;
  const callModel = async ({ messages }) => {
    seenMessages.push(messages);
    n++;
    if (n === 1) {
      return { stopReason: 'tool_use', content: [{ type: 'tool_use', id: 'tu1', name: 'get_resume', input: {} }] };
    }
    return { stopReason: 'end_turn', content: [], textDeltas: deltas('done') };
  };

  await collect(runAgent({ callModel, tools, system: 's', messages: [{ role: 'user', content: 'q' }] }));

  // 2nd model call must include: the user q, the assistant tool_use, and the tool_result.
  const secondCall = seenMessages[1];
  const toolResult = secondCall.find(
    (m) => Array.isArray(m.content) && m.content.some((c) => c.type === 'tool_result'),
  );
  assert.ok(toolResult, 'tool_result appended to conversation');
  const tr = toolResult.content.find((c) => c.type === 'tool_result');
  assert.equal(tr.tool_use_id, 'tu1');
  assert.match(tr.content, /RESUME_BODY/);
});

test('max-iteration cap fires when the model always asks for a tool', async () => {
  const tools = fakeTools();
  // Model NEVER ends the turn → would loop forever without the cap.
  const callModel = async () => ({
    stopReason: 'tool_use',
    content: [{ type: 'tool_use', id: 'x', name: 'search_jobs_semantic', input: {} }],
  });

  await assert.rejects(
    collect(runAgent({ callModel, tools, system: 's', messages: [], maxIterations: 3 })),
    /exceeded maxIterations \(3\)/,
  );
  assert.equal(tools.calls.length, 3, 'ran exactly maxIterations tool calls, no more');
});

test('a tool error becomes a tool_result (model can recover), not a crash', async () => {
  const tools = fakeTools({
    search_jobs_semantic: () => {
      throw new Error('db down');
    },
  });
  const seenMessages = [];
  let n = 0;
  const callModel = async ({ messages }) => {
    seenMessages.push(messages);
    n++;
    if (n === 1) {
      return { stopReason: 'tool_use', content: [{ type: 'tool_use', id: 'tu1', name: 'search_jobs_semantic', input: {} }] };
    }
    return { stopReason: 'end_turn', content: [], textDeltas: deltas('recovered') };
  };

  const events = await collect(runAgent({ callModel, tools, system: 's', messages: [] }));
  // Loop did NOT throw; it recovered to a final answer.
  assert.deepEqual(events.map((e) => e.type), ['step', 'token', 'done']);
  // The error was passed back as a tool_result.
  const tr = seenMessages[1].at(-1).content.find((c) => c.type === 'tool_result');
  assert.match(tr.content, /db down/);
});

test('immediate final answer (no tools) streams and finishes', async () => {
  const tools = fakeTools();
  const callModel = async () => ({ stopReason: 'end_turn', content: [], textDeltas: deltas('hi ', 'there') });

  const events = await collect(runAgent({ callModel, tools, system: 's', messages: [] }));
  assert.deepEqual(events.map((e) => e.type), ['token', 'token', 'done']);
  assert.equal(tools.calls.length, 0, 'no tools called');
});

test('end_turn with text blocks but no stream falls back to content text', async () => {
  const tools = fakeTools();
  const callModel = async () => ({
    stopReason: 'end_turn',
    content: [{ type: 'text', text: 'block answer' }],
  });
  const events = await collect(runAgent({ callModel, tools, system: 's', messages: [] }));
  assert.deepEqual(events.map((e) => e.type), ['token', 'done']);
  assert.equal(events[0].data, 'block answer');
});

test('abort stops the loop before the next model call', async () => {
  const tools = fakeTools();
  let aborted = false;
  let n = 0;
  const callModel = async () => {
    n++;
    aborted = true; // abort after the first model call
    return { stopReason: 'tool_use', content: [{ type: 'tool_use', id: 'x', name: 'search_jobs_semantic', input: {} }] };
  };
  const events = await collect(
    runAgent({ callModel, tools, system: 's', messages: [], isAborted: () => aborted }),
  );
  // Aborted right after the tool_use turn → no done, loop returns quietly.
  assert.ok(!events.some((e) => e.type === 'done'), 'no done after abort');
  assert.equal(n, 1, 'only one model call before abort took effect');
});

test('DEFAULT_MAX_ITERATIONS is a sane positive number', () => {
  assert.ok(DEFAULT_MAX_ITERATIONS >= 4 && DEFAULT_MAX_ITERATIONS <= 20);
});
