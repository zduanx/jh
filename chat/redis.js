/**
 * Redis session store (Upstash REST/HTTP).
 *
 * Stores conversation state as a single JSON blob per session, keyed by the
 * authenticated user + session: chat:{uid}:{sessionId}. See ADR-031.
 *
 *   {
 *     message_count,            // monotonic counter (summarization trigger in Phase 7)
 *     summary,                  // rolling summary of compressed-out messages (Phase 7; "" in 6B)
 *     messages: [ {role, content, ts, interrupted} ],   // per-message, role-tagged, in order
 *     created_at, updated_at
 *   }
 *
 * REST client (not TCP) because chat runs on Lambda — plain HTTPS, no VPC. ADR-027.
 * Env read at call-time (the ESM hoisting lesson from 6A's auth bug).
 */

import { Redis } from '@upstash/redis';
import { summarizeConversation } from './summarize.js';

const TTL_SECONDS = 3600; // 1h, sliding (re-set on every write)
// Block/batch summarization (NOT per-turn sliding):
// - let messages accumulate up to SUMMARIZE_AT (high-water mark)
// - then compress the oldest block down to RECENT_KEEP (low-water mark) in ONE batch.
// This keeps summarization (the 7D LLM call) infrequent — once every
// (SUMMARIZE_AT - RECENT_KEEP) messages — instead of every turn, which would be
// costly AND defeat prompt caching (per-turn summary mutation invalidates the
// cached prefix).
//
// Trigger is MESSAGE-COUNT based, NOT token based (7D decision). "Messages" here
// include tool_use + tool_result blocks the agent injects, so 20 messages ≈ ~5–7
// real exchanges. Estimated input at 20 msgs: ~3K tokens typical, ~6K worst case
// (a full resume ≈ 1.4K tokens sits in the window) — vs a 200K context window, so
// ~2–3%. No truncation risk → count is a sufficient proxy; token accounting would
// be plumbing for no benefit at these sizes. (Upgrade path if ever needed: a cheap
// char/4 estimate, or surface usage.input_tokens from callModel.)
const RECENT_KEEP = 10; // messages kept verbatim after a compaction (~2–3 exchanges)
const SUMMARIZE_AT = 20; // compact when the count reaches this high-water mark

let _client = null;
function client() {
  if (!_client) {
    _client = new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL,
      token: process.env.UPSTASH_REDIS_REST_TOKEN,
    });
  }
  return _client;
}

function keyFor(uid, sessionId) {
  return `chat:${uid}:${sessionId}`;
}

function emptySession() {
  const now = Date.now();
  return { message_count: 0, summary: '', messages: [], created_at: now, updated_at: now };
}

/** Read the session blob (or a fresh empty one if none exists). */
export async function getSession(uid, sessionId) {
  const data = await client().get(keyFor(uid, sessionId));
  // @upstash/redis auto-deserializes JSON; be defensive about shape.
  if (!data || typeof data !== 'object' || !Array.isArray(data.messages)) {
    return emptySession();
  }
  return {
    message_count: data.message_count ?? data.messages.length,
    summary: data.summary ?? '',
    messages: data.messages,
    created_at: data.created_at ?? Date.now(),
    updated_at: data.updated_at ?? Date.now(),
  };
}

/**
 * Append one message to the session, cap recent, and persist with refreshed TTL.
 * Internal helper for saveUserMessage / saveAssistantMessage.
 */
async function appendMessage(uid, sessionId, message) {
  const session = await getSession(uid, sessionId);
  const now = Date.now();

  session.messages.push(message);
  session.message_count += 1;
  session.updated_at = now;

  // Block compaction: only when we REACH the high-water mark, compress the oldest
  // block down to RECENT_KEEP in one batch. Between triggers we just append — so
  // summarization (the 7D LLM call) runs once every (SUMMARIZE_AT - RECENT_KEEP)
  // messages, not every turn, and the cached prefix stays stable between triggers.
  if (session.messages.length >= SUMMARIZE_AT) {
    const overflow = session.messages.splice(0, session.messages.length - RECENT_KEEP);
    // Inline await (7D decision A): summarization is infrequent (~every 10 msgs)
    // and must complete before we persist the trimmed session. If it fails, keep
    // the existing summary (overflow is dropped, not lost-with-error) — better a
    // slightly thinner summary than a broken turn.
    try {
      session.summary = await summarizeOverflow(session.summary, overflow);
    } catch (err) {
      console.error('chat: summarizeOverflow failed, keeping prior summary', err);
    }
  }

  // Write + refresh sliding TTL in one command.
  await client().set(keyFor(uid, sessionId), session, { ex: TTL_SECONDS });
}

/**
 * Persist the user message immediately at the START of a turn — the user message
 * is a definite fact and should survive even if generation fails. (Industry pattern.)
 */
export async function saveUserMessage(uid, sessionId, content) {
  await appendMessage(uid, sessionId, { role: 'user', content, ts: Date.now(), interrupted: false });
}

/**
 * Persist the assistant response at the END of a turn (in `finally`). `interrupted`
 * flags a partial answer (disconnect/stop/timeout) per ADR-028.
 */
export async function saveAssistantMessage(uid, sessionId, content, { interrupted = false } = {}) {
  await appendMessage(uid, sessionId, { role: 'assistant', content, ts: Date.now(), interrupted });
}

/**
 * Build the context the model sees: summary (if any) + recent messages.
 * In 6B summary is empty, so this is just the recent messages.
 */
export function buildContext(session) {
  const ctx = [];
  if (session.summary) {
    ctx.push({ role: 'system', content: `Conversation summary so far: ${session.summary}` });
  }
  ctx.push(...session.messages);
  return ctx;
}

/**
 * Compress an overflow block into the rolling summary via an LLM call (7D).
 * Delegates to summarize.js (cheap, non-streaming model). Bypasses the call on
 * empty input so we never summarize nothing.
 *
 * @returns {Promise<string>} the updated rolling summary
 */
export async function summarizeOverflow(existingSummary, overflowMessages) {
  if (!overflowMessages || overflowMessages.length === 0) return existingSummary;
  return summarizeConversation(existingSummary, overflowMessages);
}

/** Health check used by jready. */
export async function ping() {
  return client().ping();
}
