"""
Worker Lambda handlers for async processing.

Workers:
- ingestion_worker: Handles job URL sourcing and UPSERT (async invoke from API)
- crawler_worker: Fetches job page HTML (Phase 2I, SQS-triggered)
- extractor_worker: Extracts job details from HTML (Phase 2I, SQS-triggered)
"""
