# Phase 8B: Docker Sandbox Harness (the keystone)

**Status**: ✅ Completed
**Date**: June 8, 2026
**Goal**: A `run_trial(code) -> result` harness that runs **untrusted, LLM-written trial code** in an isolated Docker container — fetches arbitrary external sites safely, returns result via stdout — and is **proven safe in isolation before any agent depends on it.**

> **Result:** built + **all 9 safety-proof tests pass**. Docker Desktop installed (v29.5.2). The `jh-extractor-sandbox` image (219MB: python-slim + httpx + extractors_v2_base) runs trial code with full hardening. Containment **verified**: generated code can't read secrets (`~/.aws`, env keys), can't write the filesystem (read-only), is killed on infinite loop (timeout), and the network is cuttable (`--network none`). Legit use also verified: safe code returns results, `import extractors_v2_base` works, real fetches succeed. The sandbox is real, not a stub.

> This is the foundation of Phase 8's "AI sandboxing" theme and the riskiest piece.
> Build + prove it *before* the agent (8C).
>
> **Decision recorded:** [ADR-034](../architecture/DECISIONS.md#adr-034-sandbox-execution--local-docker-dev-lambda-the-production-path) — local Docker for dev (free/fast/owned), **Lambda is the production path** (Firecracker microVM, zero-IAM). `run_trial` is the swappable seam (docker vs. lambda.invoke); swapping is a config change, not a redesign.

---

## Step 0 — Install Docker (first task of 8B)
Docker is **not installed on this machine** (`which docker` → not found). First task of 8B:
- Install + start **Docker Desktop** (macOS).
- Verify: `docker --version` + `docker run --rm hello-world`.
Everything else in 8B depends on this.

---

## What 8B builds

```
backend/extractor_agent/            # HOST-ONLY (separate from extractors_v2_base/ — the brain + launcher)
└── sandbox/
    ├── Dockerfile                  # minimal image: python + httpx, bakes in extractors_v2_base/
    ├── host_harness.py             # host-side: ship code → docker run → return stdout JSON
    └── __tests__/                  # the safety proof (safe snippet + malicious snippet)
```

### The Dockerfile
- Base: slim python.
- Installs **httpx** only (browser-headers approach — most career APIs need only headers, not a browser).
- Copies in `extractors_v2_base/` (so trial code can `import` the base class).
- **No secrets baked in.** Entrypoint reads code from stdin, runs it, prints result to stdout.
- *Playwright (full browser) is a documented add-on* — only if a target company needs JS rendering. Start HTTP-only (Playwright ≈ 1GB, slow).

### `run_trial(code: str, timeout=...) -> dict`
Host-side function the agent calls:
```
1. docker run --rm                  # ephemeral — destroyed on exit (no state leak between runs)
     --network <controlled>         # outbound to fetch sites; no inbound; ideally no internal/DB net
     --memory 256m --cpus 1         # resource limits
     --read-only --tmpfs /tmp       # filesystem read-only except a throwaway /tmp
     (NO env / secrets passed)      # container can't see ANTHROPIC_API_KEY, DB password, etc.
     sandbox-image
2. pipe `code` via stdin
3. capture stdout (the result JSON) + stderr (errors) + exit code
4. enforce `timeout` (kill a hung/infinite-loop trial)
5. return { ok, result, stdout, stderr, error, timed_out }
```

**Communication = stdin (code in) / stdout (result out).** Simple pipes — no ports, no shared writable filesystem. The container gets internet (to fetch the company site) but **no secrets and no host filesystem access.**

---

## The safety proof (acceptance — do this FIRST)

Build the test before trusting the harness:
- [ ] **Safe snippet** (`import httpx; print(json.dumps({"ok": 1}))`) → returns the result.
- [ ] **`rm -rf` / file-write snippet** → host filesystem **unharmed** (container FS read-only / discarded).
- [ ] **Secret-read snippet** (`print(open(os.path.expanduser('~/.aws/credentials')).read())`) → **fails / sees nothing** (no host FS, no secrets).
- [ ] **Infinite loop** (`while True: pass`) → **killed by timeout**, harness returns `timed_out`.
- [ ] **Network fetch** (fetch a real careers URL) → works (the legit use).
- [ ] **`--rm` per run** → no state from a previous trial leaks into the next.

> *A broken sandbox is worse than none.* These tests are the proof it isolates — same discipline as the 7E "validate the eval before trusting it."

---

## Why this design (carried decisions)
- **Agent brain on host, only trial code in Docker** (8 overview): the container never needs your API key — it just runs one throwaway script. The LLM reasoning stays host-side.
- **Local Docker is the skill, not the location**: "I sandbox untrusted AI code" is portable; production would be **Fargate** (Lambda can't run Docker) or **E2B** (Firecracker microVMs, free tier) — documented, not built.
- **Disposability is the safety property**: `--rm` per trial → state leaks impossible, crashes contained → become gradeable failure signals for the agent loop.

---

## Open questions
- Network policy: allow all outbound, or restrict to the target domain? (Start: outbound allowed, no access to host/internal net — i.e. don't put it on a network that can reach your DB.)
- How is `extractors_v2_base/` provided — baked into the image (rebuild on change) or bind-mounted read-only (faster iteration)? (Leaning: bind-mount read-only during dev for fast iteration; bake for a "release" image.)
- Image warm-up cost vs. a warm container pool — only optimize if the agent's trial loop feels slow.

---

## Next: 8C (logo walking-skeleton) — the first agent slice, on top of a proven sandbox.
