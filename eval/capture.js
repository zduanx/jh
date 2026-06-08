/**
 * Phase 7E — capture step (Node).
 *
 * Runs the REAL chat agent over each test case and records the triple Ragas needs:
 *   { id, question, answer, contexts[], expectRefusal }
 * where `contexts` = the actual tool results the agent saw (resume text, retrieved
 * jobs, job details). We get contexts EXACTLY by wrapping buildTools().call — the
 * same instrumentation seam the agent already exposes — rather than parsing logs.
 *
 * This is the industry "trace the run, eval offline" pattern, scaled down: capture
 * here (Node), grade separately (Python/Ragas, run_eval.py).
 *
 * Why drive runAgent directly (not the HTTP endpoint): we need the contexts, which
 * the SSE stream doesn't expose. runAgent + a wrapped tools.call gives us the real
 * agent loop AND exact context capture. Multi-turn cases thread `history` as the
 * conversation; single-turn cases start fresh.
 *
 * Run:  node eval/capture.js            (needs chat/.env.local: ANTHROPIC_API_KEY,
 *                                         MCP_SERVER_URL, MCP_SERVICE_TOKEN; MCP server up)
 * Out:  eval/cases.captured.json
 */

import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { runAgent } from '../chat/agentLoop.js';
import { callModel } from '../chat/anthropicClient.js';
import { buildTools, SYSTEM_PROMPT } from '../chat/generateResponse.js';
import { CASES, EVAL_UID } from './cases.js';

const __dir = dirname(fileURLToPath(import.meta.url));

// Load chat/.env.local so the agent has its keys (same loader as chat/local.js).
const envLocal = join(__dir, '..', 'chat', '.env.local');
if (fs.existsSync(envLocal)) process.loadEnvFile(envLocal);

/**
 * Run one case through the agent, capturing the answer + every tool result.
 * Returns { id, question, answer, contexts, expectRefusal }.
 */
async function captureCase(testCase) {
  const uid = testCase.uid ?? EVAL_UID;
  const messages = [
    ...(testCase.history || []),
    { role: 'user', content: testCase.question },
  ];

  // Build the real tools surface, then WRAP .call to record each tool result as a
  // context string. The wrapper is transparent to runAgent.
  const tools = await buildTools(uid);
  const contexts = [];
  const originalCall = tools.call.bind(tools);
  tools.call = async (name, args) => {
    const result = await originalCall(name, args);
    // Record a readable context entry: the tool + its returned data.
    contexts.push(`Tool ${name} returned: ${JSON.stringify(result)}`);
    return result;
  };

  let answer = '';
  try {
    for await (const ev of runAgent({
      callModel,
      tools,
      system: SYSTEM_PROMPT,
      messages,
    })) {
      if (ev.type === 'token') answer += ev.data;
      // step/done events are not needed for grading
    }
  } finally {
    await tools.close().catch(() => {});
  }

  // Prior conversation turns are ALSO valid grounding for a follow-up answer
  // ("what's #1?" is grounded in the earlier turn, not just this turn's tools).
  // So include history as context for faithfulness — otherwise multi-turn answers
  // that correctly reference earlier turns score as "unsupported".
  const historyContexts = (testCase.history || []).map(
    (m) => `Earlier ${m.role} message: ${typeof m.content === 'string' ? m.content : JSON.stringify(m.content)}`,
  );

  return {
    id: testCase.id,
    question: testCase.question,
    answer: answer.trim(),
    contexts: [...historyContexts, ...contexts],
    expectRefusal: !!testCase.expectRefusal,
  };
}

async function main() {
  console.log(`[capture] running ${CASES.length} case(s) as uid=${EVAL_UID}…`);
  const out = [];
  for (const c of CASES) {
    process.stdout.write(`  • ${c.id} … `);
    try {
      const captured = await captureCase(c);
      out.push(captured);
      console.log(`ok (${captured.contexts.length} ctx, ${captured.answer.length} chars)`);
    } catch (err) {
      console.log(`FAILED: ${err.message}`);
      out.push({ id: c.id, question: c.question, answer: '', contexts: [], error: String(err.message || err) });
    }
  }

  const outPath = join(__dir, 'cases.captured.json');
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
  console.log(`[capture] wrote ${out.length} case(s) → ${outPath}`);
}

main().catch((e) => {
  console.error('[capture] fatal:', e);
  process.exit(1);
});
