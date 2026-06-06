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

const TTL_SECONDS = 3600; // 1h, sliding (re-set on every write)
// Block/batch summarization (NOT per-turn sliding):
// - let messages accumulate up to SUMMARIZE_AT (high-water mark)
// - then compress the oldest block down to RECENT_KEEP (low-water mark) in ONE batch.
// This keeps summarization (a Phase 7 LLM call) infrequent — once every
// (SUMMARIZE_AT - RECENT_KEEP) messages — instead of every turn, which would be
// costly AND defeat prompt caching (per-turn summary mutation invalidates the
// cached prefix). See the context-engineering discussion / Phase 7 notes.
const RECENT_KEEP = 20; // messages kept verbatim after a compaction (~10 exchanges)
const SUMMARIZE_AT = 30; // only compact when the count reaches this high-water mark

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
  // summarization (Phase 7 LLM call) runs once every (SUMMARIZE_AT - RECENT_KEEP)
  // messages, not every turn, and the cached prefix stays stable between triggers.
  if (session.messages.length >= SUMMARIZE_AT) {
    const overflow = session.messages.splice(0, session.messages.length - RECENT_KEEP);
    session.summary = summarizeOverflow(session.summary, overflow);
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
 * STUB (Phase 7): compress overflow messages into the rolling summary via an LLM call.
 * In 6B we don't summarize — overflow is simply dropped, summary stays "".
 * Bypass on empty input so Phase 7's LLM call is never made with nothing to summarize.
 */
export function summarizeOverflow(existingSummary, overflowMessages) {
  if (!overflowMessages || overflowMessages.length === 0) return existingSummary;
  return existingSummary; // Phase 7: LLM summarization of overflowMessages folded in.
}

/** Health check used by jready. */
export async function ping() {
  return client().ping();
}
