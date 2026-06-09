# Phase 8C: Icon Walking-Skeleton → a Multi-File AI Coding Agent

**Status**: ✅ Completed
**Date**: June 9, 2026
**Goal**: The first end-to-end agent slice — given a company + careers URL, the agent **discovers the company icon** through sandboxed trials and **writes its own output** (the extractor file + registry entry) via read/write tools, scoped to `extractors_v2/`. Started as a walking skeleton ("find the logo"); grew into a genuine **autonomous multi-file coding agent**.

> Walking-skeleton-first: prove the whole pipeline on the easy task (icon), with the
> *same* machinery (plan-execute · sandboxed trials · read/write file tools · registry)
> that 8D scales to the hard task ("list all jobs").

---

## What it became (vs. the original plan)

The original 8C was "find a logo, write one const." It evolved — each change driven by a design discussion (see git history of this doc):

| Original plan | What we built | Why |
|---|---|---|
| find the **logo** | find the **icon** (standalone symbol, no wordmark) | logo had the company name; we want the mark — prefer apple-touch-icon/favicon over og:image |
| ReAct only (plan deferred to 8D) | **Plan-and-Execute** (outer) + ReAct (inner) | built the structure now; LLM plans stages from the goal |
| `apply.py` writes one file (deterministic post-step) | the **LLM writes via read_file/write_file tools** | the demo is an AI *coding* agent — the LLM does the multi-file editing, like Claude Code |
| one output const (`LOGO_URL`) | **two files**: `extractors_v2/{company}.py` + `extractors_v2/registry.py` | demonstrates safe, scoped, multi-file editing |
| `Company` enum | **dropped the enum → `COMPANY_NAME: str` + a registry** | companies are an OPEN set (the agent adds them); enum is the wrong type. Registry = source of truth |

---

## Folder model (see ADR-034)

```
extractors_v2_base/   ← the CONTRACT (baked into the Docker image): base.py, config.py, _template.py
                         self-contained (stdlib + httpx); trial code does `import extractors_v2_base`
extractors_v2/        ← GENERATED output (production imports; NEVER baked): {company}.py, registry.py, cli.sh
extractor_agent/      ← the agent (host brain + sandbox harness + file tools)
```
Generated code lives in `extractors_v2/` (outside the baked folder) so sandbox rebuilds stay clean.
The `Company` enum was removed — `extractors_v2/registry.py` is the source of truth for "what companies exist".

---

## What 8C built

```
backend/extractor_agent/
├── discover.py    # Plan-and-Execute (run_agent) + inner ReAct loop (run_stage); dispatches tools
├── prompts.py     # Pydantic models (AgentStep/Action/Plan) + per-stage prompts (icon, write_extractor)
├── tools.py       # read_file / write_file — scoped to extractors_v2/, READ-BEFORE-WRITE enforced
├── cli.py         # entry: run_agent → print result
├── runs/          # gitignored run logs — {company}-{ts}.log (the audit; tee'd from jcompany)
└── sandbox/       # (8B) the Docker harness — run_trial in an isolated container

backend/extractors_v2/
├── registry.py    # source of truth: {slug: ExtractorClass}; list_companies() / get_extractor()
├── cli.sh         # e* verbs: edocker, eclean, elogo, elist, ejd
└── {company}.py   # the agent's generated extractors (e.g. anthropic.py)
```

---

## Architecture (resolved through discussion)

**Plan-and-Execute (outer) + ReAct (inner).**
- `run_agent` → **plan turn** (LLM selects stages for the goal) → executes each stage's **inner ReAct loop**.
- WE author the available stages (in the prompt); the **LLM plans which to run** (goal-driven) and **reacts** within each (trial → observe → retry). So: *we plan the menu, the LLM plans the selection + reacts on execution.*
- 8C stages: `["validate_company", "icon", "write_extractor"]`. 8D adds `fetch_jobs`, `validate_jd` — just more `_STAGE_INSTRUCTIONS` entries.
- **`validate_company` is a sanity GATE that runs first** — a **loose, judgment-based** check (NOT rigid rules): "are you confident this is a real company and a consistent site?" + a confidence signal. Garbage (`zzqwerty`, keyboard-mash) **fails → nothing written**; legitimate-but-unusual passes (e.g. `alphabet` @ abc.xyz — the LLM knows the branding *and* that a Cloudflare 403 ≠ a dead site). **Deliberately NOT a name↔domain string match** — that false-rejects real companies (Google@abc.xyz, anyone on Greenhouse/Lever/Workday ATS domains). Lesson: *for judgment calls, give the LLM the question + a bias-to-allow (git diff is the backstop), not a decision tree; rigid rules are for deterministic constraints (scope guard, read-before-write).*

**Structured output, Pydantic-validated.**
- Each turn the LLM returns a forced `AgentStep` `{thought, summary, action}` (schema generated from the Pydantic model). Replies are **validated** (`model_validate`); malformed ones are fed back for a retry — *validation scales with autonomy*.

**Tools (one action per turn — observable, industry-standard):**
- `run_trial(code)` — execute python in the Docker sandbox (8B). The discovery "act".
- `read_file(path)` / `write_file(path, content)` — the agent's own file editing, **confined to `extractors_v2/`** (path guard) with **read-before-write** (must read an existing file before overwriting it). Multi-file = multiple turns, one file each (so every edit is individually visible).

**Brain on host, trials in Docker.** The LLM (with the API key) runs on the host; only trial *code* ships into the sandbox. File edits are host-side (the reviewed output).

---

## The flow (verified end-to-end)

```
jcompany [--d] <company> <careers_url>        (root dev.sh; --d = verbose)
  PLAN  → LLM selects stages for the goal → ["icon", "write_extractor"]
  STAGE icon (ReAct):  fetch page → find apple-touch-icon/favicon/manifest → verify it's an image → done
  STAGE write_extractor (ReAct + file tools):
     read_file({company}.py)  → write_file({company}.py, <class>)
     read_file(registry.py)   → write_file(registry.py, <+ entry>)     ← multi-file, read-before-write
  RESULT → printed; review with `git status / git diff extractors_v2/`
elogo <company>   → loads the GENERATED class via the registry, prints its ICON_URL  ← proves it works
```

Observed run (Anthropic): plan → icon found in ~4 trials (recovered from a `bs4` ModuleNotFound by
switching to regex) → wrote `anthropic.py` + `registry.py` → `elogo anthropic` loaded the class and
printed the icon URL. The agent's generated code is real, importable, production-usable.

---

## Acceptance — status
- [x] `jcompany <company> <url>` runs the full flow with **observable step-by-step** output (`[stage - step N]`).
- [x] Agent discovers a plausible **icon** URL via sandboxed trial(s).
- [x] Validation confirms it's a reachable image (a trial HEAD/content-type check).
- [x] Output written into `extractors_v2/{company}.py` (uncommitted) — visible in `git diff`. **Exceeded:** also writes `registry.py` (multi-file).
- [x] `elogo <company>` loads the generated class via the registry and prints its `ICON_URL`.
- [x] Bad reply / malformed output → validated + retried (Pydantic); scoped path guard + read-before-write prevent garbage writes.
- [x] **Record file produced** — `jcompany` tees the run to a gitignored `extractor_agent/runs/{company}-{ts}.log` (ANSI-stripped); the path is printed at the end. The console log IS the audit; the file persists it.
- [x] **Fail path verified** — tested with a nonsense company + unreachable URL: the agent fetched, got a DNS error, **stopped early** (2 steps, not 8), reported `✗ icon failed` with a clear reason, `write_extractor` never ran → **no garbage file written**.

---

## Key decisions
| Decision | Choice |
|---|---|
| Agent shape | **Plan-and-Execute (outer) + ReAct (inner)** — built now, not deferred |
| LLM output | **Pydantic-validated** structured `{thought, summary, action}` + retry on invalid |
| Tools | `run_trial` (sandbox) + `read_file`/`write_file` (scoped, read-before-write) — the LLM does the coding |
| File writes | **the LLM writes** via tools (AI coding agent), not a deterministic post-step. Multi-file across turns |
| Company identity | **string `COMPANY_NAME` + registry** (enum dropped — open set; registry validates typos at lookup) |
| Scope guard | tools confined to `extractors_v2/`; only `.py`; read-before-write — prompt limit + hard code backstop |
| Review | git diff (uncommitted) — no custom review UI |
| Run record | `jcompany` tees output to a gitignored `extractor_agent/runs/{company}-{ts}.log` (ANSI-stripped) — the audit of what the agent did |
| CLI | `jcompany` (root, `j*`); `jdocker` (daemon + image); `elogo`/`eclean`/etc. are `e*` cli.sh verbs (auto-sourced) |
| Sandbox lifecycle | `jdocker` (build, cache = staleness), `jkillall` (remove containers + image), container force-kill on timeout |

---

## Next: 8D (list-all-jobs) — the hard discovery task on the SAME machinery.
Add a `fetch_jobs` stage (discover how to enumerate a company's jobs via sandboxed trials) +
`validate_jd` (a job page LLM-parses to a JD). The plan-execute structure, sandbox, file tools,
and registry are all built — 8D is "new stages + harder prompts", not new infrastructure.
