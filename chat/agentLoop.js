/**
 * The ReAct agent loop (Phase 7C) — Reason → Act → Observe, hand-written.
 *
 * This is the part ADR-029 says to OWN (no LangChain / Vercel AI SDK). It is the
 * native Anthropic tool-use loop, which IS ReAct:
 *
 *   call model
 *     ├─ stop_reason 'tool_use' → run the tool(s) (Act), append tool_result
 *     │                           (Observe), loop (Reason again)
 *     └─ stop_reason 'end_turn' → stream the final text answer, done
 *   (bounded by maxIterations so a misbehaving model can't loop forever)
 *
 * DESIGN — dependency injection for testability:
 * This module imports NOTHING from the Anthropic or MCP SDKs. It takes its two
 * external dependencies as parameters:
 *   - callModel({ system, messages, tools }) -> a ModelTurn (see below)
 *   - tools: { schemas, call(name, args) }   -> the tool surface (MCP in prod)
 * Production wires the real Anthropic client + MCP client; tests pass stubs. So
 * the loop's logic (termination, max-iter cap, tool_result feedback, event
 * mapping) is unit-tested offline, with no LLM cost and no server.
 *
 * It yields the SAME events as the seam (generateResponse): {type,data} with
 * type 'step' | 'token' | 'done'. Errors propagate (streamTurn maps to 'error').
 *
 * --- The callModel contract (ModelTurn) ---
 * callModel returns an object:
 *   {
 *     stopReason: 'tool_use' | 'end_turn' | string,
 *     content:    Array<ContentBlock>,   // the assistant's full message content
 *                                        //   (text blocks + tool_use blocks),
 *                                        //   appended verbatim as the assistant turn
 *     textDeltas?: AsyncIterable<string> // ONLY on the final (end_turn) turn:
 *                                        //   streamed text chunks for the answer
 *   }
 * tool_use blocks in `content` look like { type:'tool_use', id, name, input }.
 */

export const DEFAULT_MAX_ITERATIONS = 8;

// Verbose loop tracing → chat/server.log. OFF by default (so prod never logs
// user data / spams CloudWatch); opt in with AGENT_DEBUG (locally: `jbenode -d`).
// Levels:
//   1 = compact trace (iterations, stop reasons, tool calls)   [jbenode -d]
//   2 = ALSO dump the full `messages` array sent to the model   [jbenode -dd]
// Prefixed [agent] so it's easy to grep.
const DEBUG = (process.env.AGENT_DEBUG === '1' || process.env.AGENT_DEBUG === '2');
const DEBUG_MESSAGES = process.env.AGENT_DEBUG === '2';
function log(...args) {
  if (DEBUG) console.log('[agent]', ...args);
}
/** Dump the full message list (only at level 2) — what the model actually sees. */
function dumpMessages(label, messages) {
  if (!DEBUG_MESSAGES) return;
  console.log(`[agent] ===== ${label} (${messages.length} msg) =====`);
  messages.forEach((m, i) => {
    const content =
      typeof m.content === 'string'
        ? m.content
        : JSON.stringify(m.content, null, 2);
    console.log(`[agent]   [${i}] role=${m.role}\n${content}`);
  });
  console.log('[agent] ===== end messages =====');
}
/** Compact one-line preview of a value for logs (truncated). */
function preview(v, n = 200) {
  const s = typeof v === 'string' ? v : JSON.stringify(v);
  return s && s.length > n ? s.slice(0, n) + '…' : s;
}

/**
 * Run the ReAct loop for one user turn.
 *
 * @param {object} opts
 * @param {(req: {system: string, messages: object[], tools: object[]}) => Promise<object>} opts.callModel
 * @param {{ schemas: object[], call: (name: string, args: object) => Promise<any> }} opts.tools
 * @param {string} opts.system            - system prompt (grounding)
 * @param {object[]} opts.messages        - conversation so far (history + this user msg)
 * @param {number} [opts.maxIterations]   - hard cap on model↔tool round trips
 * @param {() => boolean} [opts.isAborted]- cooperative cancel
 * @returns {AsyncGenerator<{type:'step'|'token'|'done', data:any}>}
 */
export async function* runAgent({
  callModel,
  tools,
  system,
  messages,
  maxIterations = DEFAULT_MAX_ITERATIONS,
  isAborted = () => false,
}) {
  // Local working copy — we append assistant turns and tool results as we loop.
  const convo = [...messages];
  log(`turn start: ${convo.length} msg(s), ${tools.schemas.length} tool(s), maxIter=${maxIterations}`);
  log(`  last user msg: ${preview(convo.at(-1)?.content)}`);

  for (let iter = 0; iter < maxIterations; iter++) {
    if (isAborted()) {
      log(`iter ${iter}: aborted before model call`);
      return;
    }

    log(`iter ${iter}: calling model with ${convo.length} msg(s)…`);
    dumpMessages(`iter ${iter} messages → model`, convo);
    const turn = await callModel({ system, messages: convo, tools: tools.schemas });

    // Drain text deltas LIVE first, yielding tokens as they arrive (true
    // streaming). A tool-use turn produces no/empty text, so this yields nothing
    // and we fall through to the tool branch; a final-answer turn streams here.
    // We buffer what we streamed so the no-stream fallback below doesn't double-emit.
    let streamedAny = false;
    if (turn.textDeltas) {
      for await (const delta of turn.textDeltas) {
        if (isAborted()) return;
        if (delta) {
          streamedAny = true;
          yield { type: 'token', data: delta };
        }
      }
    }

    // Now the turn is complete; resolve why it stopped + its full content.
    // (Values OR promises — the real adapter resolves from the final message;
    // test stubs pass plain values. `await` handles both.)
    const stopReason = await turn.stopReason;
    const content = (await turn.content) || [];
    log(`iter ${iter}: stop_reason=${stopReason}, ${content.length} block(s), streamedText=${streamedAny}`);

    // ----- Final answer: we already streamed the tokens above; finish. -----
    if (stopReason === 'end_turn' || !hasToolUse(content)) {
      log(`iter ${iter}: FINAL answer → done`);
      // Fallback: a turn that gave content text but no live deltas (e.g. stubs).
      if (!streamedAny) {
        const text = textOf(content);
        if (text) yield { type: 'token', data: text };
      }
      yield { type: 'done', data: {} };
      return;
    }

    // ----- Tool use: record the assistant turn, run tools, observe -----
    convo.push({ role: 'assistant', content });

    const toolUses = content.filter((b) => b.type === 'tool_use');
    log(`iter ${iter}: model requested ${toolUses.length} tool(s): ${toolUses.map((t) => t.name).join(', ')}`);
    const toolResults = [];
    for (const tu of toolUses) {
      if (isAborted()) return;
      yield { type: 'step', data: `using ${tu.name}` };
      log(`  → call ${tu.name}(${preview(tu.input)})`);
      let resultContent;
      try {
        const result = await tools.call(tu.name, tu.input || {});
        resultContent = JSON.stringify(result);
        log(`  ← ${tu.name} ok: ${preview(resultContent)}`);
      } catch (err) {
        // Feed the error back to the model as a tool_result so it can recover,
        // rather than killing the whole turn. (ReAct: observe failure, re-reason.)
        resultContent = JSON.stringify({ error: String(err.message || err) });
        log(`  ← ${tu.name} ERROR: ${err.message || err}`);
      }
      toolResults.push({ type: 'tool_result', tool_use_id: tu.id, content: resultContent });
    }

    // Observe: append all tool results as the next user turn, then loop.
    convo.push({ role: 'user', content: toolResults });
  }

  // Hit the iteration cap without a final answer — fail loud (don't pretend done).
  log(`exceeded maxIterations (${maxIterations}) — throwing`);
  throw new Error(`agent loop exceeded maxIterations (${maxIterations})`);
}

/** True if any content block is a tool_use request. */
function hasToolUse(content = []) {
  return content.some((b) => b.type === 'tool_use');
}

/** Concatenate text from text blocks (fallback when no stream is given). */
function textOf(content = []) {
  return content
    .filter((b) => b.type === 'text')
    .map((b) => b.text)
    .join('');
}
