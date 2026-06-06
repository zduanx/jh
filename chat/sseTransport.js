/**
 * SSE transport adapter + shared turn runner.
 *
 * Both transports run a chat turn through the SAME logic (runTurn) by presenting
 * a uniform stream interface:
 *   StreamLike = { write(frame), end(), on(event, cb) }
 *
 * - AWS Lambda: `responseStream` already matches StreamLike → passed directly.
 * - Local Node: `res` (ServerResponse) is wrapped by adaptNodeRes() to match.
 *
 * This guarantees handler.js and local.js can't drift — the write-wrapper, abort
 * detection, error handling, and end() all live here, once.
 *
 * Headers (writeHead vs HttpResponseStream.from) genuinely differ between
 * transports, so each sets them BEFORE calling runTurn.
 */

import { sseFrame } from './sse.js';
import { streamTurn } from './streamTurn.js';

/**
 * Adapt a Node http ServerResponse to the StreamLike interface so it behaves
 * like Lambda's responseStream for runTurn().
 * @param {import('node:http').ServerResponse} res
 */
export function adaptNodeRes(res) {
  return {
    write: (frame) => res.write(frame),
    end: () => res.end(),
    on: (event, cb) => {
      if (event === 'close') {
        // Only treat as a client disconnect if WE didn't already end the stream.
        res.on('close', () => {
          if (!res.writableEnded) cb();
        });
      } else {
        res.on(event, cb);
      }
    },
  };
}

/**
 * Run one chat turn over a StreamLike. Owns: abort detection (close/error events
 * + failed-write — the reliable cross-transport signal, see ADR-028), the shared
 * streamTurn loop, graceful error framing, and end(). [ADR-028]
 *
 * @param {{write:Function, end:Function, on:Function}} stream - StreamLike
 * @param {{uid:any, sessionId:string, userMessage:string}} params
 */
export async function runTurn(stream, { uid, sessionId, userMessage }) {
  let aborted = false;

  // Best-effort early disconnect signals (unreliable on Lambda; reliable locally).
  stream.on('close', () => { aborted = true; });
  stream.on('error', () => { aborted = true; });

  // PRIMARY, reliable signal on both transports: a write to a dead client throws.
  const write = (frame) => {
    try {
      stream.write(frame);
    } catch (err) {
      aborted = true;
    }
  };

  try {
    await streamTurn(write, { uid, sessionId, userMessage, isAborted: () => aborted });
  } catch (err) {
    console.error('chat: turn error', err);
    if (!aborted) write(sseFrame('error', 'internal error'));
  } finally {
    stream.end();
  }
}
