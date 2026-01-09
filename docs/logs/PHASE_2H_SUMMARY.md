# Phase 2H: SSE Progress + Frontend

**Status**: ✅ Completed
**Date**: January 4, 2026
**Goal**: Real-time progress updates via SSE + frontend Stage3Progress component

---

## Overview

Phase 2H adds real-time progress display to the ingestion flow. The backend provides an SSE endpoint that streams job status updates, and the frontend connects via EventSource to display live progress.

**Key insight**: SSE (Server-Sent Events) provides simple one-way streaming with auto-reconnect. API Gateway's 29s timeout is handled by EventSource's automatic reconnection.

**Prerequisite**: Phase 2G must be complete (Worker Lambda + job UPSERT).

**Included in this phase**:
- SSE `/progress/{run_id}` endpoint with full state + diff protocol
- Frontend EventSource connection with reconnection handling
- Progress display UI (done/total counts, status badges, company cards)
- SQLAlchemy `db.expire_all()` fix for stale reads in long-running SSE
- Final log fetch after terminal status (ensures no logs are missed)

**Explicitly excluded** (deferred to Phase 2I/2J):
- Extractor flow improvements (raw info crawling, extraction logic) → Phase 2I
- Real job crawling (SQS, Lambda workers, S3 storage) → Phase 2J

---

## Key Achievements

### 1. SSE Progress Endpoint
- Real-time streaming via `text/event-stream`
- JWT authentication via query parameter (EventSource can't send headers)
- User ownership verification (run.user_id must match token's user_id)
- Reference: [ADR-016](../architecture/DECISIONS.md#adr-016-sse-for-real-time-progress-updates)

### 2. Full State + Diff Protocol
- On connect/reconnect: emit `all_jobs` event with complete job map
- During session: emit `update` events with only changed jobs
- ~90% bandwidth reduction vs always sending full state
- Reference: [ADR-018](../architecture/DECISIONS.md#adr-018-sse-update-strategy---full-state-on-connect-diffs-during-session)

### 3. Frontend EventSource Connection
- React `useEffect` hook manages EventSource lifecycle
- Handles `status`, `all_jobs`, `update` events
- Auto-reconnect on API Gateway 29s timeout
- Auto-navigate to results on completion

### 4. SQLAlchemy Stale Read Fix
- Long-running SSE connections cache SQLAlchemy objects
- Added `db.expire_all()` before each poll to refresh cached data
- Ensures job status updates are visible without session restart

### 5. Final Log Fetch
- CloudWatch logs may arrive after terminal status
- Added 1-second delayed final fetch after reaching terminal state
- Uses `useRef` to track completion and prevent duplicate fetches

---

## Architecture

```
GET /progress/{run_id} (SSE, polls every 3s)
    ├─> pending/initializing: poll ingestion_run → emit status
    ├─> ingesting: poll jobs → emit all_jobs (first) / update (diffs)
    └─> finished/error/aborted: emit final all_jobs → emit status → close stream

Frontend (Stage3Progress)
    ├─> Connect EventSource on mount
    ├─> Handle status/all_jobs/update events
    ├─> Rebuild state on reconnect (all_jobs replaces state)
    └─> Navigate to Stage 4 (Summary) on terminal status
```

---

## API Endpoints

**Route**: `GET /api/ingestion/progress/{run_id}?token=<jwt>`
- Purpose: Stream real-time job status updates
- Authentication: JWT as query parameter (EventSource limitation)
- Response: `text/event-stream` with SSE events

---

## Highlights

### Polling Strategy by Phase

| Run Status | Data Polled | Events Emitted |
|------------|-------------|----------------|
| pending | `ingestion_run` | `status: pending` |
| initializing | `ingestion_run` | `status: initializing` |
| ingesting | `jobs` table | `all_jobs` (first), then `update` diffs |
| finished/error/aborted | `jobs` table (final) | `all_jobs` (final state) → `status: <terminal>` → close stream |

### Event Format

Uses SSE native `event:` field (not JSON type):
```
event: status
data: pending

event: status
data: initializing

event: all_jobs
data: {"google": [{"external_id": "123", "title": "Software Engineer", "status": "pending"}, ...]}

event: update
data: {"google": {"123": "crawling"}, "amazon": {"456": "ready"}}

event: status
data: finished
```

### Data Structures

- **Unique key**: `company` + `external_id`
- **all_jobs**: `{company: [{external_id, title, status}, ...]}`
- **update**: `{company: {external_id: status, ...}}` (status changes only)

### Frontend EventSource Connection

```javascript
useEffect(() => {
    const es = new EventSource(`/api/ingestion/progress/${runId}?token=${token}`);

    es.addEventListener('status', (e) => {
        setStatus(e.data);
        if (['finished', 'error', 'aborted'].includes(e.data)) {
            es.close();
        }
    });

    es.addEventListener('all_jobs', (e) => {
        setJobs(JSON.parse(e.data));
    });

    es.addEventListener('update', (e) => {
        const updates = JSON.parse(e.data);
        setJobs(prev => applyUpdates(prev, updates));
    });

    return () => es.close();
}, [runId, token]);
```

### Bandwidth Analysis

```
Per minute (ingesting phase):
- Full state: 25KB on connect
- Updates: ~0.5KB × 20 = 10KB
- Total: ~35KB first minute, ~10KB subsequent

Per 29s reconnect cycle:
- Reconnect overhead: 25KB
- Updates: ~0.5KB × 10 = 5KB
- Total: ~30KB per cycle
```

---

## Metrics

| Metric | Value |
|--------|-------|
| SSE poll interval | 3 seconds |
| API Gateway timeout | 29 seconds |
| Reconnect behavior | Automatic (EventSource native) |
| Full state size (100 jobs) | ~25KB |
| Diff update size | ~0.5KB |
| Final log fetch delay | 1 second |

---

## Testing & Validation

**Manual Testing**:
- Start ingestion → Verify SSE connection opens
- Watch progress → Verify job statuses update in real-time
- Wait 29s → Verify auto-reconnect works
- Abort run → Verify stream closes with correct status
- Page refresh during run → Verify reconnects and rebuilds state

**Automated Testing**:
- Future: SSE endpoint integration tests
- Future: Frontend component tests

---

## Next Steps → Phase 2I

Phase 2I improves the extractor flow:
- Raw info crawling (browser simulation to fetch job page content)
- Raw info extraction (parse requirements, description from raw HTML)
- Claude-generated extraction prompts for custom logic per company
- Reusable prompt templates for extractor class generation

**Target**: Enhanced extractor classes with full job detail extraction

---

## File Structure

```
backend/
├── api/
│   └── ingestion_routes.py      # SSE /progress endpoint
└── auth/
    └── dependencies.py          # get_current_user_from_token helper

frontend/src/pages/ingest/
├── Stage3Progress.js            # SSE connection + progress display
└── Stage3Progress.css           # s3-* prefixed styles
```

**Key Files**:
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - SSE endpoint implementation
- [Stage3Progress.js](../../frontend/src/pages/ingest/Stage3Progress.js) - Frontend EventSource

---

## References

**External Documentation**:
- [SSE EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) - Browser API reference
- [Server-Sent Events Spec](https://html.spec.whatwg.org/multipage/server-sent-events.html) - HTML spec

**Internal Documentation**:
- [PHASE_2G_SUMMARY.md](./PHASE_2G_SUMMARY.md) - Worker Lambda, CloudWatch logs endpoint, Stage 4 Summary UI
- [PHASE_2I_SUMMARY.md](./PHASE_2I_SUMMARY.md) - Extractor Flow improvements
- [PHASE_2J_SUMMARY.md](./PHASE_2J_SUMMARY.md) - Real SQS + Lambda workers
- [ADR-016](../architecture/DECISIONS.md#adr-016-sse-for-real-time-progress-updates) - SSE Architecture
- [ADR-018](../architecture/DECISIONS.md#adr-018-sse-update-strategy---full-state-on-connect-diffs-during-session) - SSE Update Strategy
