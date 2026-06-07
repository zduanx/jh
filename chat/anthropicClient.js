/**
 * Anthropic adapter — fulfils agentLoop's `callModel` contract using the real
 * Claude Messages API (streaming + tool use). This is the ONLY file that imports
 * the Anthropic SDK; agentLoop.js stays SDK-free and testable (ADR-029).
 *
 * agentLoop calls:  callModel({ system, messages, tools }) -> ModelTurn
 * and expects back:
 *   {
 *     stopReason: 'tool_use' | 'end_turn' | ...   // why the model stopped
 *     content:    ContentBlock[]                   // the assistant's full output
 *     textDeltas: AsyncIterable<string>            // streamed text chunks
 *   }
 *
 * Streaming model: we use `messages.stream()` and bridge the SDK's `.on('text')`
 * deltas into an async queue that `textDeltas` drains lazily — so the FINAL answer
 * streams token-by-token to the browser in real time (not buffered). `stopReason`
 * and `content` come from `finalMessage()`.
 *
 * Two-hop streaming (7C highlight): Claude → here (SDK SSE) is hop 2; here →
 * browser (our SSE) is hop 1. agentLoop only drains textDeltas on the end_turn
 * turn, so tool-use turns produce no user-visible tokens (just `step` events).
 *
 * Env read at CALL time (ESM hoisting lesson): ANTHROPIC_API_KEY.
 */

import Anthropic from '@anthropic-ai/sdk';

// voyage-3 is the embedder; the CHAT model is Claude. Pin a current model.
const MODEL = process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-6';
const MAX_TOKENS = Number(process.env.ANTHROPIC_MAX_TOKENS || 2048);

let _client = null;
function client() {
  if (!_client) {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) throw new Error('ANTHROPIC_API_KEY not configured'); // fail closed
    _client = new Anthropic({ apiKey });
  }
  return _client;
}

/**
 * One model turn. Returns the ModelTurn agentLoop expects.
 *
 * @param {object} req
 * @param {string} req.system        - system prompt (the stable, cacheable prefix)
 * @param {object[]} req.messages    - the conversation so far
 * @param {object[]} req.tools       - tool schemas (MCP-derived; see toolsForAnthropic)
 * @param {object} [opts]
 * @param {number} [opts.perCallTimeoutMs] - abort a single hung LLM call (layer-2 timeout)
 * @returns {Promise<{stopReason: string, content: object[], textDeltas: AsyncIterable<string>}>}
 */
export async function callModel({ system, messages, tools }, opts = {}) {
  const stream = client().messages.stream({
    model: MODEL,
    max_tokens: MAX_TOKENS,
    // Prompt caching on the stable prefix (system + tool schemas) — the moving
    // part is `messages`, so the cached prefix stays identical across turns.
    system: [{ type: 'text', text: system, cache_control: { type: 'ephemeral' } }],
    tools,
    messages,
  });

  // Optional per-call timeout (layer 2): kill a single hung LLM call.
  if (opts.perCallTimeoutMs) {
    const t = setTimeout(() => stream.abort(), opts.perCallTimeoutMs);
    stream.finalMessage().finally(() => clearTimeout(t)).catch(() => {});
  }

  // Live async queue: .on('text') enqueues deltas; textDeltas dequeues them as
  // they arrive (TRUE token-by-token streaming to the browser, not buffered).
  // The queue closes when the stream ends. tool-use turns emit no text → the
  // queue closes immediately and textDeltas yields nothing.
  const textDeltas = liveTextDeltas(stream);

  // stopReason/content are only known at stream END. We must NOT await
  // finalMessage() here — agentLoop drains textDeltas first, and the stream only
  // completes as those deltas flow. So expose them as a promise the loop resolves
  // AFTER it finishes streaming (it reads .stopReason/.content via the getters,
  // which await the final message). For the BRANCH decision agentLoop needs
  // stopReason up front — but it only needs it to choose tool_use vs end_turn,
  // and tool_use turns have ~no text, so awaiting final there is cheap. We return
  // a thin object whose stopReason/content are resolved from finalMessage(), and
  // textDeltas that stream live. agentLoop awaits stopReason (a promise) at the
  // top of each branch.
  const finalPromise = stream.finalMessage();

  return {
    get stopReason() {
      return finalPromise.then((m) => m.stop_reason);
    },
    get content() {
      return finalPromise.then((m) => m.content);
    },
    textDeltas,
    _final: finalPromise,
  };
}

/**
 * Bridge the SDK's `.on('text')` events into a live async generator. Deltas are
 * yielded as they arrive; the generator completes when the stream ends (or
 * errors/aborts). A classic producer/consumer queue with a "resolve waiter".
 */
function liveTextDeltas(stream) {
  const queue = [];
  let done = false;
  let error = null;
  let wake = null; // resolves the consumer when new data/!done arrives

  const signal = () => {
    if (wake) {
      wake();
      wake = null;
    }
  };

  stream.on('text', (delta) => {
    if (delta) queue.push(delta);
    signal();
  });
  stream.on('end', () => {
    done = true;
    signal();
  });
  stream.on('abort', () => {
    done = true;
    signal();
  });
  stream.on('error', (err) => {
    error = err;
    done = true;
    signal();
  });

  return (async function* () {
    while (true) {
      while (queue.length) yield queue.shift();
      if (error) throw error;
      if (done) return;
      await new Promise((res) => {
        wake = res;
      });
    }
  })();
}

/**
 * Convert MCP tool schemas (from listTools) into Anthropic tool schemas.
 * MCP gives { name, description, inputSchema }; Anthropic wants
 * { name, description, input_schema }. Same JSON Schema, different key.
 *
 * @param {Array<{name, description, inputSchema}>} mcpTools
 * @returns {Array<{name, description, input_schema}>}
 */
export function toolsForAnthropic(mcpTools) {
  return mcpTools.map((t) => ({
    name: t.name,
    description: t.description,
    input_schema: t.inputSchema,
  }));
}
