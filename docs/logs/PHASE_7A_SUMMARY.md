# Phase 7A: Vector / RAG Infrastructure

**Status**: ✅ Completed
**Date**: June 6, 2026
**Goal**: Add semantic job↔resume matching — embed jobs (at extraction) and resumes (at upload) into pgvector, and prove top-K retrieval ("best match across all my jobs") in plain code, before any LLM/MCP.

> **Result:** full RAG retrieval pipeline works end-to-end. Validated against **550 embedded jobs** (6 companies) + an embedded resume — top-10 matches are all relevant senior/staff backend/infra SWE roles (sim ≈ 0.58–0.61). General Voyage embeddings retrieve sensibly → **ADR-032's "no fine-tuning" decision validated with real data.**

---

## Overview

7A is the **foundation** of the real AI backend: vectors + retrieval (RAG's "R"). It's built and proven in **plain code** first — no LLM, no MCP — so the retrieval quality is validated before anything depends on it. Embeddings use **Voyage** ([ADR-032](../architecture/DECISIONS.md#adr-032-embeddings--voyage-pre-trained-no-fine-tuning)); storage is **pgvector on Neon** (no separate vector DB).

**Included**:
- pgvector enabled; `embedding` column on jobs + a resume store.
- `vectorize_text(text)→vector` Python utility (Voyage) — write-path only.
- Vectorize-on-extract hook; existing jobs vectorized by **re-extracting** (no backfill script).
- Resume upload on the Search page + embed on upload.
- pgvector cosine top-K retrieval, proven in plain code.
- Lightweight retrieval eval (hand-picked cases) — "measure, don't fine-tune".

**Excluded**:
- LLM / MCP / agent → 7B+.
- Fine-tuning embeddings → roadmap ([ADR-032](../architecture/DECISIONS.md#adr-032-embeddings--voyage-pre-trained-no-fine-tuning)).

---

## Build Steps & Status

> Reordered during build: schema → resume upload (vertical slice) → embedding → jobs → retrieval.

### Step 1 — pgvector + schema ✅ (TEST + PROD)
- Migrations: `b3e4146c2ed5` (`CREATE EXTENSION vector`, `jobs.embedding vector(1024)` + HNSW index `vector_cosine_ops`, `resumes` table) and `3c15a29da75d` (`resumes.filename`).
- `pgvector` + `voyageai` + `pypdf` in `requirements.txt` (installed). `EMBEDDING_DIM=1024` (voyage-3) in `models/job.py`.
- Models: `Job.embedding`, new `Resume` model (registered). Applied + verified on **both TEST and PROD**.

### Step 2 — Resume upload feature (no embedding) ✅
- Profile resume (one per user, `resumes` table) — full vertical slice, **no vector yet**.
- Backend (`api/resume_routes.py`): `GET /upload-url` (presigned PUT), `POST /confirm` (download from S3 → extract text via `pypdf` → store `extracted_text` + `filename`), `GET /url` (download), `GET /` (status), `DELETE /` (S3 delete + row), `GET /debug` (extracted text + vector dump).
- S3 key fixed at `resumes/{uid}/profile.pdf` (overwrites); original filename stored for display.
- Frontend (`components/chat/ProfileResume.js`): upload / replace / download / delete + 🐛 Debug popup (always visible; shows extracted text + vector). Mounted on the Search page.
- Verified in browser: upload → "✓ filename (N chars)"; download, delete, debug-text all work. Embedding shows dim 0 (deferred to Step 3).
- PDF only (matches 4C). `extract_pdf_text` (pypdf) — raises 422 on scanned/image-only PDFs.

### Step 3 — Embedding (Voyage) ✅
- `vectorize_text(text) → vector` util (`utils/embeddings.py`, Voyage `voyage-3`, single per-call HTTP) — returns 1024-dim.
- Wired into resume `confirm` → populates `resumes.embedding` (re-embeds on replace). 🐛 Debug shows the real 1024-float vector.
- Payment method added to Voyage → rate limits unlocked (no-card tier was 3 RPM / 10K TPM); free 200M-token allowance still applies (~$0). ~1K JDs ≈ ~1M tokens ≈ 0.5% of free.

### Step 4 — Vectorize jobs on extract ✅
- `update_job_extracted` (extractor_worker) embeds `title + location + description + requirements` → `job.embedding`. **Single** `vectorize_text` per job — the SQS extractor is `BatchSize: 1` (one JD per invocation), so no batching needed (a batch util was added then removed). Best-effort: an embedding failure does NOT fail extraction.
- Existing jobs get vectors by **re-extracting** (no backfill). Requires `VOYAGE_API_KEY` in the deployed Lambda env — wired via the SAM generators (Globals → all functions), no script change needed.

### Step 5 — Retrieval in plain code (RAG "R") ✅
- `search_jobs_by_vector(db, user_id, query_embedding, top_k)` (`db/jobs_service.py`) — pgvector cosine (`<=>` / `cosine_distance`) over the user's READY embedded jobs, HNSW-indexed. Vectors **filter** N → top_k.
- `GET /api/resume/match?top_k=N` (`api/resume_routes.py`) — resume vector → top-K jobs (distance + similarity) to eyeball results.

### Step 6 — Retrieval eval (lightweight) ✅
- Validated against **550 embedded jobs** (tiktok 151, google 136, openai 115, roblox 60, netflix 49, anthropic 39) + embedded resume. Top-10 are all relevant senior/staff backend/infra SWE roles (sim ≈ 0.58–0.61). Quality held going 39 → 550 jobs.
- **Conclusion:** general Voyage embeddings retrieve sensibly → no fine-tuning needed (ADR-032 validated). Similarities cluster ~0.6 because resume↔JD are different doc types — *relative ranking* is what matters and it's correct.

---

## Database / Storage

```
jobs.embedding  vector(N)   -- pgvector, HNSW index; populated at extraction
resume store + embedding    -- per-user profile resume for the assistant
```

Query (nearest jobs to a resume, scoped to the user):
```sql
SELECT id, title FROM jobs WHERE user_id = :uid
ORDER BY embedding <=> :resume_vector LIMIT 10;   -- <=> cosine distance
```

---

## Highlights

### Vectors filter, the LLM judges
pgvector narrows 300 → top-K **in code** (cosine/HNSW); the LLM (later, 7C) reasons over the K. The LLM never compares vectors. See [vectors-rag-eval.md](../learning/vectors-rag-eval.md).

### Embedding is a write-path util, not a tool
`vectorize_text` runs at ingest/upload (Python). The LLM never vectorizes; the frontend never vectorizes. So it's a plain internal function — no endpoint, no MCP tool.

### Cloud embeddings because extraction is a Lambda
Extraction runs in a 256MB/30s Lambda — hostile to bundling a local model. A Voyage HTTP call fits cleanly ([ADR-032](../architecture/DECISIONS.md#adr-032-embeddings--voyage-pre-trained-no-fine-tuning)).

---

## API Endpoints (Profile Resume)

Mounted at `/api/resume` (`api/resume_routes.py`):
- `GET /upload-url` — presigned S3 PUT URL
- `POST /confirm` — extract text (pypdf) + embed (Voyage) → `resumes` row
- `GET /url` — presigned download URL
- `GET /` — status (has_resume, filename, has_embedding, chars)
- `DELETE /` — S3 delete + row delete (immediate, no retention on this bucket)
- `GET /debug` — extracted text + full embedding (numpy → float for JSON)
- `GET /match?top_k=N` — **semantic top-K jobs for the resume** (Step 5 retrieval)

---

## Testing & Validation

- [x] Resume upload → extract text → embed → stored (verified in browser; "✓ filename (N chars, embedded)").
- [x] 🐛 Debug shows extracted text + 1024-float vector.
- [x] Job extraction populates `embedding` (550/550 test jobs embedded via re-extraction).
- [x] `resume_vector → top-K` returns sensible jobs — top-10 all relevant senior/staff backend roles across 6 companies (550-job corpus).
- [ ] PROD jobs embedded (test = 550/550; prod 0/727 until re-extracted on prod).

---

## Next Steps → Phase 7B

Wrap `search_jobs_by_vector` (+ get_job / get_resume / score) as tools in a **single standalone Python MCP server** ([ADR-030](../architecture/DECISIONS.md#adr-030-single-standalone-python-mcp-server-multi-client)).

---

## File Structure

```
backend/
├── models/job.py              # + embedding column, EMBEDDING_DIM=1024
├── models/resume.py           # NEW — Resume model (profile-level, user_id UNIQUE, +filename)
├── models/__init__.py         # registers Resume
├── alembic/versions/          # b3e4146c2ed5 (pgvector + jobs.embedding + HNSW + resumes), 3c15a29da75d (resumes.filename)
├── requirements.txt           # + pgvector, voyageai, pypdf
├── utils/embeddings.py        # NEW — vectorize_text via Voyage (write-path)
├── utils/pdf_text.py          # NEW — extract_pdf_text (pypdf)
├── db/jobs_service.py         # + search_jobs_by_vector (cosine top-K)
├── api/resume_routes.py       # NEW — profile resume API (upload/confirm/url/delete/debug/match)
├── main.py                    # mounts resume_router at /api/resume
├── workers/extractor_worker.py# embeds job on extract (update_job_extracted)
└── .env.local + SAM generators# VOYAGE_API_KEY (Globals → all Lambdas; no script change)

frontend/src/
├── components/chat/ProfileResume.js + .css   # NEW — upload/download/delete/debug UI
└── pages/search/SearchPage.js                # mounts <ProfileResume />
```

---

## Key Learnings

- **pgvector returns numpy `float32` arrays on read** — not JSON-serializable. Anywhere an embedding is serialized to JSON (the `/debug` endpoint; later MCP tool responses) must convert `float(x)` first, or FastAPI raises a 500. Bit us on `/api/resume/debug`.
- **A backend 500 surfaces in the browser as a CORS error** — FastAPI's CORS middleware doesn't add `Access-Control-Allow-Origin` to unhandled-exception responses, so "Failed to fetch / blocked by CORS" can actually be a hidden 500. Check the status code, not just the CORS message.
- **Voyage no-card free tier = 3 RPM / 10K TPM**; adding a payment method unlocks higher limits while the 200M free-token allowance still applies (so usage stays ~$0; ~1K JDs ≈ ~1M tokens ≈ 0.5% of free). Needed for burst job embedding — hence **batch** embedding in Step 4.
- _(Pending Step 5): confirm general Voyage embeddings retrieve sensibly for job/resume (no fine-tuning needed)._

---

## References

- [pgvector](https://github.com/pgvector/pgvector)
- [Voyage AI embeddings](https://docs.voyageai.com/)
- [vectors-rag-eval.md](../learning/vectors-rag-eval.md) · [ADR-032](../architecture/DECISIONS.md#adr-032-embeddings--voyage-pre-trained-no-fine-tuning)
