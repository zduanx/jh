/**
 * MCP client — the chat agent's connection to the Phase 7B Python MCP server.
 *
 * This is the agent's "act" arm (the ReAct loop's tool-execution side). It is an
 * RPC client: `callTool(name, args)` makes a remote procedure call over MCP to the
 * Python server, which runs the real tool function in-process and returns the
 * result. (See ADR-029: we build the agent LOOP by hand, but use the official MCP
 * SDK for the transport plumbing — JSON-RPC framing, the initialize handshake, and
 * JSON-vs-SSE content negotiation are commodity protocol, not worth hand-rolling.)
 *
 * Transport: streamable-http to the server's `/mcp` endpoint.
 *   - Local dev:  `jbemcp` on http://localhost:8001 (stateful, NO auth middleware).
 *   - Deployed:   the McpServer Lambda Function URL (stateless + json_response;
 *                 service-token auth via ServiceAuthMiddleware — ADR-033).
 * We ALWAYS send `Authorization: Bearer <MCP_SERVICE_TOKEN>`: the deployed server
 * requires it; the local server ignores it. One code path for both.
 *
 * Auth model (ADR-033): this is SERVICE-to-service auth (the chat agent is a trusted
 * backend service). The end user's identity is carried separately — the agent passes
 * the JWT-verified `user_id` as a TOOL ARGUMENT on each call. The token proves
 * "caller is our agent"; the user_id says "acting for this user".
 *
 * Env read at CALL time, not module-load time (ESM hoisting lesson — see auth.js):
 *   MCP_SERVER_URL      base URL of the MCP server (e.g. http://localhost:8001)
 *   MCP_SERVICE_TOKEN   shared service token (ADR-033)
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

// The MCP server mounts streamable-http at /mcp (FastMCP default).
const MCP_PATH = '/mcp';

/**
 * Open a connected MCP client session.
 *
 * Each call performs the MCP `initialize` handshake. Callers should `await
 * session.close()` when done (or use withMcpSession, which does it for them).
 *
 * @returns {Promise<Client>} a connected SDK Client
 */
export async function connect() {
  const base = process.env.MCP_SERVER_URL;
  const token = process.env.MCP_SERVICE_TOKEN;
  if (!base) throw new Error('MCP_SERVER_URL not configured');
  if (!token) throw new Error('MCP_SERVICE_TOKEN not configured'); // fail closed

  const url = new URL(MCP_PATH, base);
  const transport = new StreamableHTTPClientTransport(url, {
    // Sent on every HTTP request the transport makes (handshake + tool calls).
    requestInit: {
      headers: { Authorization: `Bearer ${token}` },
    },
  });

  const client = new Client({ name: 'jh-chat-agent', version: '0.1.0' });
  await client.connect(transport); // runs initialize
  return client;
}

/**
 * List the tools the server exposes (name, description, JSON input schema).
 * These schemas are what we hand to Claude so it can choose/shape tool calls.
 *
 * @param {Client} client - a connected client (from connect())
 * @returns {Promise<Array<{name, description, inputSchema}>>}
 */
export async function listTools(client) {
  const { tools } = await client.listTools();
  return tools;
}

/**
 * Call one tool by name (the RPC). `args` MUST include the authenticated `user_id`
 * for the user-scoped tools — the agent injects it from the verified JWT.
 *
 * Returns the tool's structured result. FastMCP wraps non-object returns under a
 * "result" key (a tool typed `dict|None` or `list[...]` comes back as
 * `{ result: ... }`), so we unwrap that for convenience; object returns pass through.
 *
 * @param {Client} client
 * @param {string} name
 * @param {object} args
 * @returns {Promise<any>} the tool result (unwrapped)
 */
export async function callTool(client, name, args = {}) {
  const res = await client.callTool({ name, arguments: args });
  if (res.isError) {
    const text = (res.content || []).map((c) => c.text).join(' ');
    throw new Error(`MCP tool "${name}" failed: ${text || 'unknown error'}`);
  }
  // Prefer structured content; unwrap FastMCP's {"result": ...} envelope.
  const sc = res.structuredContent;
  if (sc && typeof sc === 'object' && 'result' in sc) return sc.result;
  if (sc !== undefined && sc !== null) return sc;
  // Fallback: text content (shouldn't happen for our structured tools).
  return (res.content || []).map((c) => c.text).join('');
}

/**
 * Convenience: connect, run `fn(client)`, always close. Use for one-shot work
 * (a test, or a single agent turn that opens/closes its own session).
 *
 * @param {(client: Client) => Promise<T>} fn
 * @returns {Promise<T>}
 * @template T
 */
export async function withMcpSession(fn) {
  const client = await connect();
  try {
    return await fn(client);
  } finally {
    await client.close();
  }
}
