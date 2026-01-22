# Phase 2L: Force Ingestion Mode

**Status**: ✅ Completed
**Date**: January 11, 2026
**Goal**: Add "Force Ingestion" button that bypasses SimHash skip logic, ensuring all jobs go through extraction

---

## Overview

During staged testing, the SimHash deduplication causes jobs to be marked as SKIPPED when content hasn't changed. This is correct behavior for production but makes testing the extraction pipeline difficult - if you've already crawled a job once, subsequent runs skip it.

Phase 2L adds a "Force Ingestion" mode that:
1. Bypasses the SimHash similarity check in CrawlerWorker
2. Always sends jobs to ExtractorQueue (even if content unchanged)
3. Allows full pipeline testing without clearing the database

**Included in this phase**:
- Frontend: Red "Force Ingestion" button in Stage 2 (left of "Start Ingestion")
- Backend API: New `force` parameter in `/api/ingestion/start`
- IngestionWorker: Pass `force` flag to CrawlerQueue messages
- CrawlerWorker: Skip SimHash check when `force=true`, always proceed to S3+extraction
- Run metadata: Store `force` flag for debugging/visibility

**Explicitly excluded**:
- Force mode for individual companies (all-or-nothing)
- Force mode for individual jobs

---

## Key Achievements

### 1. CrawlMessage Extension
Added `force: bool = False` field to `CrawlMessage` dataclass, with serialization support.

### 2. API Enhancement
`POST /api/ingestion/start` now accepts optional `{ "force": true }` body. Stores flag in `run_metadata.force`.

### 3. Worker Pipeline
Force flag flows through: API → Lambda invoke → IngestionWorker → SQS message → CrawlerWorker

### 4. SimHash Bypass Logic
CrawlerWorker checks `message.force` before SimHash comparison:
```python
if not message.force and is_similar(old_simhash, new_simhash, threshold=3):
    # Skip only if not forced AND content similar
```
SimHash is still computed and stored even when forced.

### 5. Frontend UI
- Red "Force Ingestion" button with same enable/disable logic as Start Ingestion
- Separate confirmation modal with warning message
- Red-themed modal styling

---

## Testing

**Automated Testing**:
- ✅ All 27 worker tests pass

**Manual Testing**:
- [ ] Force button disabled when Start Ingestion is disabled
- [ ] Force button opens separate confirmation modal with warning
- [ ] Force run shows `force: true` in run_metadata
- [ ] Jobs that would be SKIPPED are now processed to READY
- [ ] Normal ingestion still skips unchanged content

---

## File Structure

```
backend/
├── api/
│   └── ingestion_routes.py   # Add force param to /start
├── workers/
│   ├── types.py              # Add force to CrawlMessage + InitializationResult.to_crawl_messages
│   ├── ingestion_worker.py   # Pass force through handler → process_run → run_ingestion_phase
│   └── crawler_worker.py     # Check message.force, bypass SimHash when true

frontend/src/pages/
├── IngestPage.js             # Pass force param to API call
└── ingest/
    ├── Stage2Preview.js      # Add Force Ingestion button + confirmation modal
    └── Stage2Preview.css     # Red button + modal styling
```

**Key Files**:
- [types.py](../../backend/workers/types.py) - CrawlMessage with force field
- [ingestion_routes.py](../../backend/api/ingestion_routes.py) - StartIngestionRequest model
- [crawler_worker.py](../../backend/workers/crawler_worker.py) - SimHash bypass logic
- [Stage2Preview.js](../../frontend/src/pages/ingest/Stage2Preview.js) - Force button + modal

---

## References

**Related Phases**:
- [Phase 2J: Crawler Queue](./PHASE_2J_SUMMARY.md) - SimHash deduplication
- [Phase 2K: Extractor Queue](./PHASE_2K_SUMMARY.md) - Extraction pipeline
