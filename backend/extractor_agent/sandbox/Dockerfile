# Phase 8B — minimal sandbox image for running untrusted LLM-generated trial code.
#
# Design:
#   - slim python + httpx ONLY (browser-headers approach; Playwright is a later add-on)
#   - bakes in extractors_v2_base/ (the CONTRACT) so trial code can
#     `import extractors_v2_base` — NOT the generated extractors_v2/ (those are the
#     agent's OUTPUT and must never be baked in, so rebuilds stay clean — ADR-034)
#   - NO secrets baked in; entrypoint runs a trial passed via stdin, prints to stdout
#   - runs as an unprivileged user
#
# Build (from backend/):
#   docker build -f extractor_agent/sandbox/Dockerfile -t jh-extractor-sandbox .
#
# Run (the host harness does this with hardening flags — see host_harness.py):
#   echo "<trial code>" | docker run --rm -i --network=... --read-only ... jh-extractor-sandbox

FROM python:3.13-slim

# httpx = the only dep trial code (and extractors_v2_base) needs.
RUN pip install --no-cache-dir "httpx>=0.27"

# Bake in ONLY the self-contained framework/contract (extractors_v2_base) — the
# stable base class trial code extends. Generated extractors (extractors_v2/) are
# NEVER copied in → the image stays the clean contract across rebuilds (ADR-034).
# Build context is backend/, so this copies backend/extractors_v2_base → /app/extractors_v2_base.
WORKDIR /app
COPY extractors_v2_base /app/extractors_v2_base

# The in-container entrypoint: reads trial code from stdin, executes it, prints result JSON.
COPY extractor_agent/sandbox/container_entrypoint.py /app/container_entrypoint.py

# Unprivileged user — generated code never runs as root.
RUN useradd -m -u 10001 sandbox && chown -R sandbox:sandbox /app
USER sandbox

# Entrypoint reads code from stdin and runs it via the runner.
ENTRYPOINT ["python", "/app/container_entrypoint.py"]
