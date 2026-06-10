# Agent Engineering: Lessons from the Extractor-Discovery Agent (Phase 8C/8D)

Hard-won lessons from building an autonomous, sandboxed, multi-file coding agent that
onboards companies by discovering their job-listing APIs. These are general agent-design
lessons, learned by watching real runs fail and fixing them.

---

## 1. Judgment vs. control flow — split them

**Lesson:** the LLM is great at JUDGMENT (is this a real company? is this a real JD?), unreliable at CONTROL FLOW (therefore call the `fail` tool, not `done`).

- `validate_company` judged `valid: false` correctly, but returned it via the `done` tool → the pipeline treated it as success and kept going (onboarded garbage).
- **Fix:** the LLM emits the *judgment* (`valid: false` in the result); our CODE enforces the *consequence* (`if result["valid"] is False → stop`). Don't trust the LLM to route judgment → the right control tool.
- **General rule:** *LLM provides the decision; deterministic code acts on it.* Same pattern as the eval judge (LLM scores claims; arithmetic computes the score).

## 2. Loose prompts for judgment, rigid rules for constraints

**Lesson:** for fuzzy "is this legit?" questions, give the LLM the question + a bias, NOT a decision tree.

- My first `validate_company` had rigid rules ("name must match domain") → false-rejected real companies (Google@abc.xyz, anyone on Greenhouse/Lever ATS domains).
- **Fix:** "are you confident this is a real company and a consistent site? Lean toward allowing when unsure (git diff is the backstop)." The LLM then correctly allowed `alphabet`@abc.xyz (it knew the ABC=alphabet branding *and* that a Cloudflare 403 ≠ a dead site) — nuance no rule could capture.
- **General rule:** rigid rules for *deterministic* constraints (scope guard, read-before-write); loose judgment for *world-knowledge* calls.

## 3. The thing you VERIFY must BE the thing you SHIP

**Lesson:** a validation stage that proves *a* working version is useless if a *different* version gets written.

- `validate_jd` ran a trial, hit a bug (`self.client` doesn't exist), FIXED it in the trial, judged "valid" — but `write_extractor` wrote the OLD broken `code`. validate passed; the shipped file crashed (`elist` → AttributeError).
- **Fix:** `validate_jd` returns `verified_code` = the exact body that JUST WORKED in the trial; `write_extractor` writes THAT, not the unverified upstream code.
- **General rule:** the validator must *emit the artifact it validated*. Otherwise validation and the shipped artifact diverge.

## 4. Encode observed failures as specific prompt guidance ("shortcuts beat 'think harder'")

**Lesson:** when a run flails, don't add "think harder" — encode the specific lesson the failure revealed.

- HRT failed twice (18 steps) chasing the website's *server-side* filter format. Run 1 (success) had "fetch all, filter client-side." → Added: *"ALWAYS fetch all jobs unfiltered, then filter in python; do NOT replicate the server's filtered request — that's a rabbit hole."*
- HRT's custom WP endpoint 500'd until the `setting` param (a `data-filters-settings` DOM blob) was included → Added a **symptom→fix table**: *"500 critical error = a REQUIRED param is missing (usually `setting`); empty [] = wrong filters, send none."*
- OpenAI's icon stage rabbit-holed through Wayback/Google-cache → Added: *"try `/favicon.ico` and `/apple-touch-icon.png` directly before giving up; do NOT try Wayback/cache/sitemaps."* Next run: icon found in 1 step.
- **General rule:** every flailing run is a prompt-improvement signal. Convert the specific failure → a specific instruction. "Think harder" is weak; "here's the shortcut" is strong.

## 5. Detailed (cached) system prompt > more round-trips

**Lesson:** each ReAct turn re-sends the WHOLE conversation (chat-like), so round-trips are quadratically expensive; a detailed system prompt is cached and nearly free after turn 1.

- Putting the ATS API patterns (Greenhouse/Ashby/Eightfold/Lever URLs) directly in the prompt → the agent goes STRAIGHT to the right API (~3-4 trials) instead of exploring blindly.
- **Mechanism:** Anthropic prompt caching (`cache_control: ephemeral` on the system block) → the detailed guidance costs ~nothing per turn.
- **General rule:** trade input tokens (cached system prompt) for fewer round-trips (each re-sends the growing, uncached history). Detail up front beats blind exploration.

## 6. Context trimming is dangerous — don't drop what the agent re-examines

**Lesson:** premature context compaction caused MORE work, not less.

- Tried compacting old large tool-result dumps (JS bundles) to save tokens. But the agent needed to RE-EXAMINE those bundles across turns → it re-FETCHED them (7× re-reads), costing more steps AND tokens than the trim saved.
- **Fix:** turned trimming OFF. A correct version needs "summarize, don't drop" (keep the conclusion, drop the raw bytes) — not blind truncation.
- **General rule:** the ~200K-tokens/run cost is acceptable; correctness first, token optimization later (and carefully).

## 7. Per-stage budgets (generic engine, per-stage config)

**Lesson:** different stages need different step budgets; keep the engine generic.

- `run_stage` is identical for every stage — it just looks up `stage_system_prompt(stage)` (the prompt) and `_max_steps(stage)` (the cap) by stage name. validate=4, icon=8, fetch_jobs=18, validate_jd=5, write=8.
- Two-tier limits: the PROMPT sets a soft target ("~10 trials"); the CODE sets a higher hard cap (18) so a hard stage isn't killed mid-discovery.
- **General rule:** generic infra + per-stage config (looked up by name) — not stage-specific code paths.

## 8. The discovery LADDER that generalized (5 real ATSs)

From doing 5 companies by hand first, then teaching the agent:
- **Identify the ATS** (signature in HTML, or try known APIs blind by slug).
- **Known public APIs:** Greenhouse `boards-api.greenhouse.io/v1/boards/{slug}/jobs` (+`?content=true` for departments/offices); Ashby `api.ashbyhq.com/posting-api/job-board/{slug}`; Eightfold `{host}/api/apply/v2/jobs?domain&pid` (PAGINATE); Lever; Workday.
- **No public API → read the JS bundle** for the real endpoint/action/required params (HRT's custom WP admin-ajax + `setting` blob).
- **Map per-ATS fields → contract** (field names differ); **the job `url` is ALREADY in the data** — extract it, don't construct it (URL_PREFIX_JOB was the wrong model).
- **Filter CLIENT-SIDE** (fetch all, filter in python): `?q=`→title; `?Teams=`/`?disciplines=`→department/office field; HTML-embedded→`data-term` blob.
- **Watch for decoys** (HRT's `hrttalentcommunity` board = 3 fake jobs).

## 9. Do it manually FIRST, then write the prompt

**Lesson:** the best prompt came from solving 5 companies by hand before writing a word of the `fetch_jobs` prompt.

- Each manual solve revealed a wrinkle the prompt then encoded: signature-in-HTML (Anthropic) → blind-API (OpenAI) → pagination (Netflix) → custom-endpoint-read-the-bundle (HRT) → same-ATS-different-params (Roblox `?content=true`).
- **General rule:** you can't write good agent guidance for a task you haven't done yourself. Manual exploration *is* the prompt research.

## 10. Prompt caching: append makes history cacheable; the BREAKPOINT makes it cached

**Lesson:** an agent that re-sends its whole growing conversation every turn (ReAct is chat-like) hits the **input-tokens-per-minute rate limit** — we hit Anthropic Tier-1's 30K/min mid-`fetch_jobs` (the large Greenhouse JSON re-sent each turn). The fix is prompt caching, but two things must both be true:

- **The history must be a STABLE PREFIX** — we append-only to `messages`, so prior turns never change → cacheable. (Necessary.)
- **You must place a `cache_control` BREAKPOINT** — Anthropic caches only up to a breakpoint. We had one on the *system prompt* only; the *history* (the big part) was uncached and re-sent as fresh input. Adding a breakpoint on the **last message** each turn makes `[system + all prior messages]` cache. (Sufficient.) Append alone is necessary but NOT sufficient — you have to *point* the cache at the history.
- **The rate limit math:** `counted = input_tokens + cache_creation` — cache **reads are EXCLUDED** ("excluding cache reads" in the console). So once history is a cache read, it's both ~10× cheaper (0.1×) AND free against the per-minute limit. Result: roblox went from 429 → peak 13.5K/30K.
- **Caveat — cache WRITES still count:** the FIRST time a huge result enters context it's a write (1.25×, counted). So a single giant payload on one turn can still spike the limit; the deeper fix is to not pull more than you need into context (e.g. don't fetch full job descriptions when you only need departments/offices to filter).
- **General rule:** for a re-sending agent loop, cache the history (breakpoint on the last message). It's the technique the rate-limit pricing is *designed* to reward — cheaper and unblocks the limit at once.

## 11. Instrument before you optimize — you can't tune what you can't see

**Lesson:** we *speculated* about which step blew the token budget; we couldn't confirm it until we printed the numbers. The run log (without `--d`) didn't even contain the large payloads (they went to the API, not stdout), so the log alone couldn't answer "tokens per step."

- Added a per-call `[tokens] counted=… cache_read=… | ~X/30K in last 60s` line from the response's `usage` (input / cache_creation / cache_read / output) + a rolling-60s window.
- That window IS the time-aware metric (a sliding 60s sum) — it shows the per-minute accumulation directly, so you *see* the exact step that approaches the limit, and *see* caching working (cache_read climbing while counted stays small).
- **General rule:** add cheap observability (token usage, timing) before optimizing context/cost. The instrumentation turned "why is it 429ing?" from a guess into a measurement — and revealed the fix was already working (peak 13.5K), not that more cuts were needed.

---

## Cross-cutting principle

**The agent provides intelligence (discovery, judgment, code); the harness provides safety + determinism (scope guards, gates, verified-code propagation, validation).** Most bugs were the harness trusting the LLM for something deterministic, or the LLM being asked to be rigid about something fuzzy. Get the split right and the agent is both capable and reliable.

See: [PHASE_8C_SUMMARY](../logs/PHASE_8C_SUMMARY.md), [PHASE_8D_SUMMARY](../logs/PHASE_8D_SUMMARY.md), [ADR-034](../architecture/DECISIONS.md#adr-034-sandbox-execution--local-docker-dev-lambda-the-production-path).
