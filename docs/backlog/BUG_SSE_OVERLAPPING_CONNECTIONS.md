# Bug: Ingestion SSE Opens Overlapping Connections

**Status**: 🔲 Open (not prioritized)
**Severity**: Low (functional — UI works; wastes Lambda invocations + bandwidth)
**Area**: Frontend EventSource lifecycle (`Stage3Progress.js`)
**Date investigated**: 2026-06-05

---

## Summary

The ingestion progress SSE on the deployed stack opens **2–3 overlapping
connections** to the same run simultaneously. Each connection runs its full
intended ~25s lifecycle, but new connections are spawned faster than old ones
die, so they accumulate. In the browser Network tab this looks like
"reconnecting every 3–8 seconds," but it is actually **multiple staggered
~25s connections**, not one short-lived connection.

This is a **frontend EventSource lifecycle bug**, NOT a server bug. The
server-side generator's 25s force-close works exactly as designed.

---

## Impact

- **Wasted Lambda invocations**: each overlapping connection is a separate
  `JobHuntTrackerAPI` invocation running a 25s poll loop. 2–3× the intended
  compute for the SSE endpoint.
- **Wasted bandwidth**: each new connection re-sends the full `all_jobs`
  payload (109 jobs in the observed run → ~525KB transferred across the
  reconnect chain in one session). The `start_time` resume cursor in the URL
  is not used by the generator to skip the full dump.
- **No user-facing breakage**: the progress UI still renders correctly because
  duplicate events are idempotent (same statuses applied twice).

---

## Root Cause

The SSE `useEffect` in `Stage3Progress.js` re-runs **while a connection is
still alive**, opening a new EventSource without the old server-side generator
(a 25s Lambda loop) being aware the client left. Two compounding causes:

### Primary — reconnect race + unstable effect dependency
```js
eventSource.onerror = () => {
  if (readyState === CLOSED && !isTerminalStatus) {
    setTimeout(() => setReconnectCount((c) => c + 1), 1000); // manual reconnect
  }
};
return () => { eventSource.close(); };
}, [runId, apiUrl, onTerminal, applyJobDiffs, reconnectCount]); // deps
```

1. **`onerror` manual reconnect races with EventSource native auto-reconnect.**
   On each 25s server close, `onerror` schedules `reconnectCount++` AND the
   browser's EventSource natively auto-reconnects → up to two new connections
   for one close.
2. **`onTerminal` is a prop, likely an unstable reference.** If the parent does
   not wrap `onTerminal` in `useCallback`, it is a new function on every parent
   render. Every state update (`setJobs`/`setStatus` on each event) can
   re-render the parent → new `onTerminal` → effect re-runs **mid-connection**
   → closes + reopens the ES while the server's 25s Lambda loop is still alive.

   (Note: `applyJobDiffs` IS stably memoized with `useCallback([])`, so it is
   NOT a contributor. The suspect is `onTerminal`.)

### Secondary — React StrictMode (dev only)
`React.StrictMode` (`index.js`) double-invokes effects in **development**,
starting with 2 connections. This compounds the issue locally but is NOT the
cause of the **production** overlap (Vercel ships a production build where
StrictMode double-invoke is disabled). The primary cause above is the real
production bug.

---

## Evidence

### 1. Code comment confirms server-side design (intended 25s close)
`backend/api/ingestion_routes.py` `_progress_generator`:
```python
# Force close before Lambda timeout (30s) so Mangum can return
# the buffered SSE events. API Gateway + Mangum buffers the entire
# StreamingResponse and returns it at once when the generator ends.
if time.time() - start_time > 25:
    break
```

### 2. Timestamped curl against production — proves intra-connection buffering
A single SSE connection's events all arrived at the client within a ~116ms
burst (all timestamped ~17:06:02.7xx), despite representing crawl progress
produced over many seconds server-side. Confirms API Gateway + Mangum buffer
the whole response and flush on generator close — the connection does NOT
stream in real time.

### 3. CloudWatch logs — proves OVERLAPPING connections (the root cause)
`/aws/lambda/JobHuntTrackerAPI`, filtered for `SSE`. Request IDs (UUIDs)
distinguish concurrent invocations/connections:

```
21:05:27  conn-A  poll, sent_all_jobs=False → emitting all_jobs   (A starts)
21:05:30  conn-A  poll (A continues)
21:05:33  conn-A  poll
21:05:35  conn-B  poll, sent_all_jobs=False → emitting all_jobs   (B starts — A still alive!)
21:05:36  conn-A  poll
21:05:38  conn-B  poll
21:05:39  conn-A  poll → update
21:05:42  conn-A  poll
21:05:44  conn-B  poll
21:05:45  conn-A  "SSE closing after 25s"                          (A closes at ~25s ✅)
21:05:48  conn-C  poll, sent_all_jobs=False → emitting all_jobs   (C starts)
...
```
- Connection A lives 21:05:27 → 21:05:45 (~18–25s) — the 25s close works.
- Connection B starts at 21:05:35, **8s into A's lifetime** — overlap.
- Each connection re-emits the full `all_jobs` (`sent_all_jobs=False` on every
  new invocation, because the flag is initialized per-generator).

### 4. Browser Network tab — reconnect chain + full-payload resends
- Repeating `SSE connected` / `SSE connection error, readyState: 0` pairs in
  the console = the reconnect chain.
- Each `progress/13?...&start_time=<incrementing>` request carries a new resume
  cursor, but the server re-sends full `all_jobs` anyway.
- ~525KB transferred across the session due to repeated full-state resends.

---

## Proposed Fix (when prioritized)

1. **Remove the manual reconnect race.** Do not rely on BOTH native
   EventSource auto-reconnect AND a manual `reconnectCount++` in `onerror`.
   Pick one controlled reconnect path.
2. **Stabilize `onTerminal`.** Wrap it in `useCallback` in the parent, or drop
   it from the effect dep array and call it via a ref. Stops mid-connection
   effect re-runs.
3. **Guard against overlap.** Hold the EventSource in a `useRef`; before opening
   a new one, close the previous (`if (esRef.current) esRef.current.close()`).
4. **(Optional) Server-side efficiency.** Use the `start_time` resume cursor so
   a reconnecting client receives diffs instead of a full `all_jobs` resend.

Fixing the frontend overlap (1–3) also removes the duplicate 25s Lambda
invocations and most of the redundant `all_jobs` bandwidth.

---

## Related / Notes

- This bug is independent of the SSE **buffering** limitation (evidence #2),
  which is the real blocker for any future token-by-token chat streaming.
  Both are symptoms of "SSE + reconnect on Lambda + API Gateway is fiddly."
- A non-buffering long-running runtime (container) for streaming would avoid
  both the buffering and the 25s-reconnect churn, since the connection stays
  open. Captured separately in the chat/runtime design discussion.
- Affected files:
  - `frontend/src/pages/ingest/Stage3Progress.js` (EventSource effect)
  - `backend/api/ingestion_routes.py` (`_progress_generator`, optional cursor fix)
