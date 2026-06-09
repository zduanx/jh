"""
Per-company v2 extractors — one file per company.

Each file holds a BaseExtractorV2 subclass with PENDING members the agent fills:
  - LOGO_URL        (discovered in 8C)
  - _fetch_all_jobs (discovered in 8D)

The agent writes/edits exactly one file here; `git diff` on it is the human review.
See _template.py for the shape.
"""
