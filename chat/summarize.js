/**
 * Conversation summarizer (Phase 7D) — folds an overflow block of old messages
 * into the rolling summary, so long chats stay within a small context window
 * without losing the gist.
 *
 * This is a SECOND, independent LLM use, separate from the agent loop (7C):
 *   - non-streaming (we just need the text back),
 *   - a CHEAP model (Haiku) — summarization doesn't need the chat model,
 *   - low max_tokens — a summary is short by design.
 *
 * Block/batch: called once every (SUMMARIZE_AT - RECENT_KEEP) messages (see
 * redis.js), not per turn — keeps cost low and the cached prefix stable.
 *
 * Env (read at call time): ANTHROPIC_API_KEY, optional ANTHROPIC_SUMMARY_MODEL.
 */

import Anthropic from '@anthropic-ai/sdk';

const SUMMARY_MODEL = process.env.ANTHROPIC_SUMMARY_MODEL || 'claude-haiku-4-5';
const SUMMARY_MAX_TOKENS = Number(process.env.ANTHROPIC_SUMMARY_MAX_TOKENS || 512);

let _client = null;
function client() {
  if (!_client) {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) throw new Error('ANTHROPIC_API_KEY not configured'); // fail closed
    _client = new Anthropic({ apiKey });
  }
  return _client;
}

/** Render a stored message (role + string|blocks content) as plain text for the summarizer. */
export function renderMessage(m) {
  if (typeof m.content === 'string') return `${m.role}: ${m.content}`;
  // tool_use / tool_result blocks → a compact textual form.
  const parts = (m.content || []).map((b) => {
    if (b.type === 'text') return b.text;
    if (b.type === 'tool_use') return `[called ${b.name}(${JSON.stringify(b.input)})]`;
    if (b.type === 'tool_result') return `[tool result: ${typeof b.content === 'string' ? b.content : JSON.stringify(b.content)}]`;
    return '';
  });
  return `${m.role}: ${parts.join(' ')}`;
}

/**
 * Summarize an overflow block, folding it into the existing rolling summary.
 *
 * @param {string} existingSummary - the summary so far ("" if none yet)
 * @param {object[]} overflowMessages - the oldest messages being compacted out
 * @returns {Promise<string>} the updated rolling summary
 */
export async function summarizeConversation(existingSummary, overflowMessages) {
  const transcript = overflowMessages.map(renderMessage).join('\n');

  const prompt = [
    existingSummary
      ? `Here is the running summary of the earlier conversation:\n${existingSummary}\n`
      : '',
    `Here are the next older messages to fold into the summary:\n${transcript}\n`,
    `Update the running summary so it preserves the FACTS and DECISIONS needed to continue the conversation: which jobs/companies/roles were discussed, the user's stated preferences or situation, and any conclusions reached. Be concise (a few sentences). Output ONLY the updated summary, no preamble.`,
  ].join('\n');

  const res = await client().messages.create({
    model: SUMMARY_MODEL,
    max_tokens: SUMMARY_MAX_TOKENS,
    messages: [{ role: 'user', content: prompt }],
  });

  // Concatenate any text blocks from the response.
  return res.content
    .filter((b) => b.type === 'text')
    .map((b) => b.text)
    .join('')
    .trim();
}
