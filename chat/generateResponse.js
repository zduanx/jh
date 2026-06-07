/**
 * THE SEAM.
 *
 * generateResponse(sessionId, history, { uid, userMessage }) is the single
 * interface between the transport layer (Function URL handler / local server) and
 * the response logic.
 *
 *   sessionId    - the chat session key
 *   history      - prior turns (built BEFORE this turn's user message, so the
 *                  current question is NOT in here — it comes via userMessage)
 *   uid          - authenticated user id; injected as user_id into every MCP tool
 *                  call (ADR-033). The MCP server trusts this (the agent verified
 *                  the JWT); the service token proves "caller is our agent".
 *   userMessage  - the current user question (what the agent sends to Claude)
 *
 * Phase 7C: the REAL agent. This wires three pieces (all built/tested separately):
 *   - runAgent()      the hand-written ReAct loop (agentLoop.js)         [ADR-029]
 *   - callModel()     the Anthropic streaming + tool-use adapter (anthropicClient.js)
 *   - tools           the MCP client surface (mcpClient.js), uid injected per call
 * It yields the SAME events as the Phase-6 mock ({type,data}: step|token|done), so
 * the transport (sseTransport/streamTurn) and the frontend are unchanged.
 *
 * Yields events of shape: { type: 'step'|'token'|'done', data: string|object }
 */

import { runAgent } from './agentLoop.js';
import { callModel, toolsForAnthropic } from './anthropicClient.js';
import { connect, listTools, callTool } from './mcpClient.js';

// The fixed prefix — what this app is + grounding (anti-fabrication). Stable
// across turns (goes in `system`, the cacheable prefix). ADR/PHASE_7C: grounding.
const SYSTEM_PROMPT = `You are the assistant inside a job-hunt tracker app. The user is a job seeker who has saved jobs they're tracking and (optionally) uploaded a resume.

Your job: help them understand THEIR tracked jobs and how their background fits — e.g. "best jobs for me", "top roles at <company>", "how do I match this job", "what does my resume say".

Rules:
- Use the tools to look up REAL data. Never invent jobs, titles, companies, locations, or match scores.
- If a tool returns nothing (e.g. no resume, no matching jobs), say so plainly — do not fabricate.
- Rely on the tools for CURRENT state. Do NOT trust what an earlier turn said about the user's data (resume, jobs) — it may have changed since (e.g. they just uploaded a resume). When in doubt, call the tool again.
- The tools are already scoped to this user; you do not need to ask for their identity.
- Be concise and concrete. Prefer specifics from the data over generic advice.`;

/**
 * Build the tools surface runAgent expects: { schemas, call(name, args) }.
 * Connects to the MCP server, fetches tool schemas (converted to Anthropic
 * format), and returns a `call` that injects the authenticated uid as user_id.
 *
 * The MCP functions are injectable (default = the real mcpClient) so the
 * uid-injection contract is unit-testable offline. ADR-033: the agent injects the
 * JWT-verified uid; the model never supplies it.
 *
 * @param {string|number} uid
 * @param {object} [deps] - { connect, listTools, callTool } (defaults to mcpClient)
 * @returns {Promise<{schemas: object[], call: Function, close: Function}>}
 */
export async function buildTools(uid, deps = {}) {
  const _connect = deps.connect || connect;
  const _listTools = deps.listTools || listTools;
  const _callTool = deps.callTool || callTool;

  const client = await _connect();
  const mcpTools = await _listTools(client);
  return {
    schemas: toolsForAnthropic(mcpTools),
    // Inject user_id from the verified JWT into every call. The model never
    // supplies it — it's not in the tool args the model sees as required.
    async call(name, args) {
      return _callTool(client, name, { ...args, user_id: uid });
    },
    async close() {
      await client.close();
    },
  };
}

// eslint-disable-next-line no-unused-vars -- sessionId kept for the seam contract
// (streamTurn passes it); the real agent works from `messages`, not the key.
export async function* generateResponse(sessionId, history = [], { uid, userMessage } = {}) {
  // buildContext() may prepend a {role:'system'} summary message (Phase 7D). The
  // Anthropic Messages API does NOT allow 'system' inside `messages` — system is a
  // separate top-level param. So split any summary OUT of history and fold it into
  // the system prompt; pass only user/assistant turns to the loop.
  const summaries = history.filter((m) => m.role === 'system').map((m) => m.content);
  const convoHistory = history.filter((m) => m.role !== 'system');

  // Normalize to the {role, content} Anthropic expects (drop Redis-only fields
  // like ts/interrupted — harmless but keep the payload clean).
  const messages = [
    ...convoHistory.map((m) => ({ role: m.role, content: m.content })),
    { role: 'user', content: userMessage },
  ];

  const system = summaries.length ? `${SYSTEM_PROMPT}\n\n${summaries.join('\n')}` : SYSTEM_PROMPT;

  const tools = await buildTools(uid);
  try {
    // Delegate to the ReAct loop; re-yield its step/token/done events verbatim.
    yield* runAgent({
      callModel,
      tools,
      system,
      messages,
    });
  } finally {
    // Always close the MCP session, even on error/abort.
    await tools.close().catch(() => {});
  }
}
