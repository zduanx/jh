# Phase 8B — minimal sandbox image for running untrusted LLM-generated trial code.
#
# Design:
#   - slim python + httpx ONLY (browser-headers approach; Playwright is a later add-on)
#   - bakes in extractors_v2/ so trial code can `import extractors_v2` (the contract)
#   - NO secrets baked in; entrypoint runs a trial passed via stdin, prints to stdout
#   - runs as an unprivileged user
#
# Build (from backend/):
#   docker build -f extractor_agent/sandbox/Dockerfile -t jh-extractor-sandbox .
#
# Run (the host harness does this with hardening flags — see host_harness.py):
#   echo "<trial code>" | docker run --rm -i --network=... --read-only ... jh-extractor-sandbox

FROM python:3.13-slim

# httpx = the only dep trial code (and extractors_v2) needs.
RUN pip install --no-cache-dir "httpx>=0.27"

# Bake in the self-contained extractor framework (the contract trial code extends).
# Build context is backend/, so this copies backend/extractors_v2 → /app/extractors_v2.
WORKDIR /app
COPY extractors_v2 /app/extractors_v2

# The in-container entrypoint: reads trial code from stdin, executes it, prints result JSON.
COPY extractor_agent/sandbox/container_entrypoint.py /app/container_entrypoint.py

# Unprivileged user — generated code never runs as root.
RUN useradd -m -u 10001 sandbox && chown -R sandbox:sandbox /app
USER sandbox

# Entrypoint reads code from stdin and runs it via the runner.
ENTRYPOINT ["python", "/app/container_entrypoint.py"]
