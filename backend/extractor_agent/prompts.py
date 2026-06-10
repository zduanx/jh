"""
Prompts + structured-output MODELS for the extractor-discovery agent (Phase 8C).

The agent runs a ReAct loop: each turn the LLM returns a STRUCTURED step
(AgentStep below); we run the action (a sandboxed trial), feed the result back,
and loop until it converges (action "done") or hits the cap.

Structured output is defined as PYDANTIC MODELS (not a hand-written JSON Schema):
  - the schema we hand the LLM is GENERATED from the model (`AgentStep.model_json_schema()`)
    → schema + parsing can't drift apart
  - each LLM reply is VALIDATED via `AgentStep.model_validate(...)` → malformed replies
    raise a clear error we can feed back to the model ("validation scales with autonomy").
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Action(BaseModel):
    """What the agent does this step."""
    tool: Literal["run_trial", "read_file", "read_files", "write_file", "explore_site", "done", "fail"] = Field(
        description=("run_trial = execute python in the sandbox; "
                     "read_file = read ONE file under extractors_v2/; "
                     "read_files = read SEVERAL known files at once (one round-trip — use when you already know the set, e.g. {company}.py + registry.py); "
                     "write_file = write a file under extractors_v2/ (read it first if it exists); "
                     "explore_site = delegate to the dedicated site-explorer sub-agent (pass `url`): it reverse-engineers how a custom careers site loads jobs in ISOLATED context and returns the request facts — keeps YOUR context small; "
                     "done = finished with a result; fail = give up.")
    )
    code: Optional[str] = Field(
        default=None,
        description="For run_trial: python code. Set `result = <json-able>` (or define `async def run(): ...`). You may `import extractors_v2_base, httpx, json, re`.",
    )
    path: Optional[str] = Field(
        default=None,
        description="For read_file / write_file: the path under extractors_v2/ (e.g. 'extractors_v2/anthropic.py' or 'extractors_v2/registry.py').",
    )
    paths: Optional[list[str]] = Field(
        default=None,
        description="For read_files: the list of paths under extractors_v2/ to read in one call.",
    )
    content: Optional[str] = Field(
        default=None,
        description="For write_file: the FULL new content of the file.",
    )
    result: Optional[dict] = Field(
        default=None,
        description='For done: the final answer, e.g. {"icon_url": "...", "source": "apple-touch-icon", "confidence": "high"}.',
    )
    url: Optional[str] = Field(
        default=None,
        description="For explore_site: the careers URL to hand the explorer sub-agent.",
    )
    reason: Optional[str] = Field(default=None, description="For fail: why you're giving up.")


class AgentStep(BaseModel):
    """One structured turn from the agent (inner ReAct loop)."""
    thought: str = Field(description="Your internal reasoning for this step (kept in context).")
    summary: str = Field(description="A short one-line present-tense summary, for the terminal.")
    action: Action


# All stages the agent knows how to run (the order it should plan them in).
# validate_company runs FIRST — a sanity gate (real company? name matches domain?).
KNOWN_STAGES = ["validate_company", "icon", "fetch_jobs", "validate_jd", "write_extractor"]


class Plan(BaseModel):
    """The OUTER plan: which stages to run, in order (Plan-and-Execute)."""
    thought: str = Field(description="Brief reasoning about the plan.")
    stages: list[str] = Field(
        description=f"Ordered list of stages to run. Choose from: {KNOWN_STAGES}. Skip any that don't apply."
    )


# Schemas handed to the LLM are GENERATED from the models — single source of truth.
ACTION_SCHEMA = AgentStep.model_json_schema()
PLAN_SCHEMA = Plan.model_json_schema()


def plan_system_prompt() -> str:
    return f"""You are an extractor-discovery agent. Before acting, make a PLAN: select which discovery STAGES to run (in order) to achieve the GOAL for this company.

Available stages: {KNOWN_STAGES}
- "validate_company": a judgment-based sanity check — is this plausibly a real company and a consistent site? ALWAYS run this FIRST for an onboarding goal — it gates the rest.
- "icon": find the company's standalone icon image URL.
- "fetch_jobs": discover how to list ALL of the company's jobs (the underlying ATS API), producing a working _fetch_all_jobs (each job carries its `url`).
- "validate_jd": fetch one job's `url` via the framework's crawl + judge it's a real JD for this company (end-to-end proof the URLs work). Runs AFTER fetch_jobs.
- "write_extractor": write the extractor file (icon + fetch logic) + register the company. Run this LAST.

Choose stages based on the GOAL, in a sensible order. A FULL onboarding runs all of them IN THIS ORDER: ["validate_company","icon","fetch_jobs","validate_jd","write_extractor"] (validate gates first; validate_jd checks the discovered URLs before committing; write_extractor is last since it needs the icon + fetch results). For a narrower goal, include only what's needed — e.g. "just find the icon" → ["validate_company","icon"]. Return the ordered stage list + brief reasoning."""


def plan_user_prompt(company: str, url: str, goal: str) -> str:
    return f"Company: {company}\nURL: {url}\nGoal: {goal}\n\nWhat stages should you run?"


# ===========================================================================
# Plan-and-Execute structure: an OUTER plan sequences STAGES; each stage runs an
# INNER ReAct loop (trial → observe → retry). 8C has one real stage (icon); 8D
# adds fetch_jobs + validate_jd. Adding a stage = adding an entry to STAGES below.
# ===========================================================================

# Shared preamble for every stage (the sandbox contract + ReAct mechanics + file tools).
_SANDBOX_PREAMBLE = """You solve each stage by taking ONE action per turn; I run it and tell you what happened; you react and try again until the stage is solved.

Tools:
- run_trial: execute python in a SANDBOX. Set a top-level `result = <json-serializable>` (or `async def run(): return ...`). You may `import httpx, json, re` and `import extractors_v2_base`. It has outbound internet, NO secrets, a read-only filesystem, and is fresh each run.
- read_file(path): read a file under extractors_v2/. Returns its content (or exists=false).
- write_file(path, content): write a file under extractors_v2/ with the FULL content. You may ONLY write under extractors_v2/ — nothing else on disk. If the file already exists, you MUST read_file it FIRST (so you edit real content, not a guess).

When the stage is solved, return action {"tool":"done","result":{...}}. If you genuinely can't, return {"tool":"fail","reason":"..."}. Keep `summary` to a short present-tense phrase."""


# Per-stage instruction blocks. Each describes the stage's goal + expected `done` result.
_STAGE_INSTRUCTIONS = {
    "validate_company": """STAGE: a sanity-check BEFORE any discovery or writing — use your JUDGMENT, not rigid rules. This gates the run.

Question: given the company name and the URL, are you confident this is a REAL company and that this site plausibly belongs to it / is consistent with it? Use your world knowledge; fetch the page with one run_trial if that helps you decide.

Notes:
- The name and domain do NOT need to match literally — that's normal (e.g. careers sites on abc.xyz, facebook.com, or third-party ATS domains like greenhouse.io/lever.co/workday). Judge plausibility, not string overlap.
- When you are genuinely UNSURE, lean toward proceeding — a human reviews the result (git diff) afterward. False-rejecting a real company is worse than letting a borderline one through.

If valid → return done with {"valid": true, "company": "<clean lowercase slug>", "confidence": "high|medium|low", "reasoning": "..."}.
If NOT valid → return the FAIL action (tool "fail") with a clear reason — do NOT return done. (Use fail when you're confident it's garbage: an obviously fake/gibberish name like keyboard-mash, or a site that doesn't exist / is parked / is clearly unrelated.)""",

    "icon": """STAGE: find the COMPANY ICON image URL — the standalone brand SYMBOL/mark (e.g. just the swirl), NOT the full logo with the company name/wordmark.

You want the ICON (symbol only, no text). PREFER these sources IN THIS ORDER (icon-only first; og:image usually has the wordmark, so it's last resort):
1. `<link rel="apple-touch-icon" ...>` — a clean square icon, no wordmark. BEST.
2. The web app manifest: find `<link rel="manifest" href="...">`, fetch that JSON, use its largest `icons[].src` (app-tile icons — icon-only).
3. `<link rel="icon" ...>` (favicon) — icon-only; prefer the largest `sizes`.
4. `<meta property="og:image" ...>` — LAST RESORT; usually the full logo WITH text.
Resolve relative URLs to absolute. Verify the candidate returns an image (HTTP 200 + image content-type). Only fall back to og:image if 1-3 yield nothing (then confidence "medium").

ALWAYS-AVAILABLE FALLBACK (use this BEFORE giving up — never go to step 4 of this paragraph without trying it): just GET `https://<domain>/favicon.ico` and `https://<domain>/apple-touch-icon.png` directly — these standard paths almost always exist even when the HTML is a bot-blocked JS shell. If one returns an image (200 + image content-type), USE IT.

EFFICIENCY: do NOT rabbit-hole. If the homepage is bot-blocked or icon-free, do NOT try Wayback Machine, Google cache, sitemaps, or CDX APIs — those waste steps. Instead just hit the standard /favicon.ico and /apple-touch-icon.png paths directly. Solve in ≤4 trials.

done result: {"icon_url":"...","source":"apple-touch-icon|manifest|favicon|og:image","confidence":"high|medium"}""",

    "fetch_jobs": """STAGE: discover HOW to list ALL of the company's jobs from the given careers URL, producing a working approach that returns a list of jobs. Aim to solve in ~8 trials; each trial is expensive, so plan before you act.

EFFICIENCY (read first — this is how you stay under budget):
- ALWAYS prefer: fetch ALL jobs UNFILTERED from the source, then apply the URL's filters in YOUR python (client-side). Do NOT try to replicate the website's own server-side filtered request — that path is a rabbit hole (custom nested filter formats, etc.). Get everything, filter locally.
- Plan your approach in `thought` before trialing. Don't repeat a failed approach with small variations — if an approach fails twice, CHANGE STRATEGY (e.g. stop fighting the server filter → get-all-then-filter-locally).
- Reuse what earlier trials already revealed (endpoint, action, params) — don't re-fetch the same page/bundle repeatedly.

KEY INSIGHT: the careers page is usually a JS app — the jobs are NOT in the visible HTML. The REAL source is almost always an underlying ATS (applicant tracking system) with a PUBLIC JSON API. Go straight for it; don't scrape rendered HTML.

LADDER (try in order, stop when you get a clean job list):

1. Identify the ATS. Fetch the page and grep for a signature: greenhouse, lever, ashby, eightfold, workday, smartrecruiters, jobvite. If found, you know the ATS. If the page is a tiny JS shell with NO signature, just TRY the known ATS APIs by the company slug (step 2) — they often work even with no signature.

2. Hit the ATS's public JSON API (KNOWN patterns — {slug} = company slug, often the COMPANY_NAME; for some it's a custom board token found on the page):
   - Greenhouse: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs   (add ?content=true to also get `departments` and `offices` — needed if the filter is by team/location)
   - Ashby:      https://api.ashbyhq.com/posting-api/job-board/{slug}      (jobs in `.jobs`)
   - Lever:      https://api.lever.co/v0/postings/{slug}?mode=json
   - Eightfold:  {careers_host}/api/apply/v2/jobs?domain={domain}&pid={pid}&start=0&num=100   (pid/domain are in the URL; positions in `.positions`, total in `.count` — PAGINATE: loop `start` until you have all `count`)
   - Workday:    POST {host}/wday/cxs/{tenant}/{site}/jobs  (paginated)
   Pick the matching one. Verify the count looks sane (not 0, not a tiny "talent community" decoy board, not absurd).

3. If NO public ATS API works (custom site, e.g. a WordPress careers page): DELEGATE to the dedicated explorer sub-agent with `explore_site` (pass just the careers URL). It reads the page + (often 20KB+) JS bundle in ISOLATED context — keeping YOUR context small — and returns the facts: {found, endpoint, method, action, required_params, notes}. Use those to write the actual fetch (typically POST that endpoint with the action + required params, no filters, then filter client-side). Don't read the JS bundle yourself — that's the sub-agent's job.

4. PAGINATE if the API reports a total greater than what you fetched.

5. MAP each job to our contract dict and RETURN them. Each job dict MUST be:
   {"id": <str>, "title": <str>, "location": <str>, "url": <str>, "response_data": <the raw job object>}
   - "url" is REQUIRED: the FULL job-detail (JD landing) page URL. It is ALREADY in the listing data — just extract it, don't construct it. Field names differ per ATS: Greenhouse `absolute_url`; Ashby `jobUrl`; Eightfold `canonicalPositionUrl`; for HTML-embedded jobs, the card's `<a href="...">`. Make it absolute.
   - Other fields also differ per ATS — inspect the JSON: Greenhouse `id`,`title`,`location.name`; Ashby `id`,`title`,`location`; Eightfold `id`,`name`,`location`. Put the raw object in `response_data`.

6. APPLY the URL's filters CLIENT-SIDE on the full list you already fetched (do NOT send the filters to the server — fetch everything, then filter in python). The input URL may have query params that narrow the list. Figure out what each param means and WHERE it lives in the job data, then filter the mapped jobs:
   - a search query (?q=, ?search=) → match the job TITLE (substring, case-insensitive)
   - a discipline/team/category (?disciplines=, ?Teams=, ?job-category=) → match a structured field (Greenhouse `departments[].name`, Eightfold `department`) or, for HTML-embedded jobs, a `data-term`-style attribute
   - a location (?loc=, ?locations=) → match the office/location ("headquarters" → the main office)

OUTPUT: when you have a working fetch + the mapped, filtered list, return done with:
{"approach": "<one-line: which ATS/endpoint + how you paginate/filter>", "code": "<a complete async def _fetch_all_jobs(self) -> list[dict] body that reproduces this — using httpx, applying the same filters; it may read self.INPUT_CAREER_URL>", "sample_count": <int total before filter>, "filtered_count": <int after the URL filter>, "sample_titles": [<up to 5 titles>]}

The `code` is the heart of it — the next stage writes it into the extractor. Make it self-contained (httpx only) and deterministic.
CRITICAL constraints on the `code` (it becomes a method on a BaseExtractorV2 subclass):
- There is NO `self.client`, `self.session`, or similar — the base class provides NONE. Create your own: `async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:`. Do NOT reference `self.<anything>` except `self.INPUT_CAREER_URL`.
- The dicts you RETURN (the final list) must each contain `id`, `title`, `location`, `url`, `response_data` — do NOT drop `url` in the final mapping (a common mistake is capturing the url while parsing but omitting it from the returned dict). Verify your returned dicts have a non-empty `url`.
- Whatever code you put in `code` MUST be the SAME code you verified in your trials — if a trial fixed a bug (e.g. removed `self.client`), the `code` must contain the FIXED version, not the broken one.""",

    "validate_jd": """STAGE: prove the discovered extractor works end-to-end BEFORE it's written — by running it as a trial. Your trial code IS the extractor class (the same code that will be written to extractors_v2/{company}.py): define the class extending the baked-in BaseExtractorV2, instantiate it, fetch jobs, and crawl one job's url via the FRAMEWORK's crawl_raw_info. If this trial works, the written file (identical class) is guaranteed to work.

In a run_trial, define + run the class (this exercises the baked-in extractors_v2_base):

    import asyncio
    from extractors_v2_base import BaseExtractorV2

    class _Extractor(BaseExtractorV2):
        COMPANY_NAME = "{company}"
        async def _fetch_all_jobs(self):
            <paste the EXACT fetch_jobs code you discovered>

    async def run():
        ext = _Extractor()
        jobs = await ext._fetch_all_jobs()
        sample = jobs[0]
        raw = await ext.crawl_raw_info(sample["url"])   # base-class crawl (HTTP GET) of the JD page
        return {"job_count": len(jobs), "url": sample["url"], "title": sample["title"],
                "raw_len": len(raw), "raw_head": raw[:2500]}

Then JUDGE the fetched page (confidence-based, like validate_company): does `raw_head` look like a real JOB DESCRIPTION (title, responsibilities/requirements, an apply path) for THIS company?
- done with {"valid": true, "checked_url": "...", "confidence": "high|medium|low", "reasoning": "...", "verified_code": "<the EXACT _fetch_all_jobs body that JUST WORKED in your trial — this becomes the written extractor, so it must be the working version, including any fixes you made (e.g. using httpx.AsyncClient, not self.client)>"} if it clearly is. The `verified_code` is REQUIRED — write_extractor uses THIS, not the earlier (possibly-broken) fetch_jobs code.
- If jobs[0]['url'] is empty, the page 404s, or it isn't a JD for this company → return the FAIL action with a clear reason (the fetch_jobs result is broken — better to fail than ship a bad extractor).
One sample is enough — you're proving the fetch + url + crawl path works, not every job.""",

    "write_extractor": """STAGE: write the company's extractor file AND register it — using the read_file / write_file tools. This is multi-file editing (like a coding agent), confined to extractors_v2/.

RULE: any file that already exists must be read BEFORE you write_file it (so the overwrite is allowed and you preserve unrelated content). TIP: you know both target files up front — read them BOTH at once with `read_files(["extractors_v2/{company}.py", "extractors_v2/registry.py"])` (one round-trip) instead of two separate read_file calls. The files MAY already exist from a PRIOR run with DIFFERENT/older code — do NOT trust the old file. The prior stages' results are the SOURCE OF TRUTH. For the `_fetch_all_jobs` body, use validate_jd's `verified_code` (the version that was PROVEN to work in a trial) if present; otherwise the fetch_jobs `code`. ALWAYS write the file with the CURRENT results; only skip the write if you've read it and confirmed it byte-for-byte matches what you would write.

Do these, in order:

1. read_file("extractors_v2/{company}.py") (required — to allow the overwrite). Then write_file("extractors_v2/{company}.py", <content>) using validate_jd's `verified_code` for _fetch_all_jobs (NOT an old file's, NOT the unverified fetch_jobs code if a verified version exists). <content> must be EXACTLY this shape (a subclass of BaseExtractorV2 with CLASS attributes named exactly COMPANY_NAME and ICON_URL — uppercase, as class vars, NOT module-level constants):

import httpx
from typing import Any

from extractors_v2_base import BaseExtractorV2


class {Company}Extractor(BaseExtractorV2):
    COMPANY_NAME = "{company}"
    ICON_URL = "{the icon_url you discovered}"
    INPUT_CAREER_URL = "{the careers URL you were given}"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        {the discovered _fetch_all_jobs body from the fetch_jobs stage — properly indented}

   ({Company}Extractor = the company slug Capitalized + "Extractor", e.g. anthropic → AnthropicExtractor.)
   - Use the prior stages' results: ICON_URL = the icon_url; INPUT_CAREER_URL = the careers URL; the _fetch_all_jobs body = the `code` the fetch_jobs stage produced (indent it under the method). If a fetch_jobs result is NOT in the prior results (e.g. it wasn't planned), leave _fetch_all_jobs as `raise NotImplementedError("not discovered yet")`.

2. read_file("extractors_v2/registry.py") — read the CURRENT registry (you MUST read before editing it).

3. write_file("extractors_v2/registry.py", <content>): take the EXACT content you just read, and (a) add a line `from extractors_v2.{company} import {Company}Extractor` next to the other imports, and (b) add `"{company}": {Company}Extractor,` inside the REGISTRY dict. Preserve everything else verbatim.

When both files are written, return done with {"wrote": ["extractors_v2/{company}.py", "extractors_v2/registry.py"]}.""",
    # 8D will add: "validate_jd": ...
}


# ===========================================================================
# DEDICATED SUB-AGENT: site explorer. A concretely-defined sub-task (reverse-
# engineer how a custom careers site loads jobs) → its own SPECIALIZED system
# prompt, so the expertise lives WHERE THE WORK HAPPENS (not in a generic task
# string the parent has to write — which would drift). The parent just passes
# the URL. The heavy reading (page + 20KB+ JS bundle) stays in THIS sub-agent's
# isolated context; only the compact facts return → big token savings.
# ===========================================================================
EXPLORE_SITE_SYSTEM = """You are a SITE-EXPLORATION sub-agent. Given a careers URL whose jobs are NOT served by a known public ATS API, reverse-engineer HOW the page loads its jobs, and return the request facts. You run in ISOLATED context — do the heavy reading here; the caller sees ONLY your final result.

Tools: run_trial (execute python in a sandbox; set `result = <json-able>` or `async def run(): ...`; import httpx, json, re). IMPORTANT: when a fetch returns a big blob (HTML page, JS bundle), do NOT return the raw blob — print/return only the EXTRACTED bits (regex matches: the ajax url, the action name, attribute values). Keep every trial's output small.

How custom careers sites usually work:
1. Fetch the page. Find the main frontend JS bundle (`<script src="...frontend-bundle...js">` or similar) and any inline config (e.g. `var XxxAjax = {"ajaxurl":..., "nonce":...}`).
2. Fetch the JS bundle. grep it for the AJAX call: the endpoint, method (usually POST), and the `action` name (e.g. `action: "get_xxx_jobs_handler"`), and what params it sends (`data`, `setting`, `queryparams`, `nonce`).
3. WordPress admin-ajax.php is the most common case. The POST needs the custom `action` AND almost always a `setting` param whose value is a DOM attribute like `data-filters-settings` (or `data-*-settings`) on the listing element — taken from the page HTML and HTML-UNESCAPED (raw HTML has `&quot;`; unescape to real JSON before sending).
4. VERIFY with ≤2 POST attempts: (a) read the page HTML for the `data-*-settings` attribute + nonce; (b) POST action+setting+nonce with NO filters. SYMPTOMS: a 500 "There has been a critical error" = a REQUIRED param is missing (usually `setting`); an empty `[]` = wrong/extra filter params (send none, filter later). Once it returns jobs, you've confirmed the request — stop.

When confident, return done with:
{"found": true, "endpoint": "<full url>", "method": "POST|GET", "action": "<action name or null>", "required_params": ["setting", "nonce", ...], "param_sources": {"setting": "data-filters-settings attr on .xxx, html-unescaped", "nonce": "XxxAjax.nonce in page HTML"}, "job_shape": "<one line: jobs come back as JSON array of {ID,title,content-html with data-term...}>", "notes": "<anything the caller needs to build _fetch_all_jobs + filter>"}

If you genuinely can't (e.g. needs JS execution / a real browser), return {"tool":"fail","reason":"..."}. Keep `summary` short."""


def explore_site_task(url: str) -> str:
    return f"Careers URL: {url}\n\nReverse-engineer how this page loads its jobs and return the request facts."


def stage_system_prompt(stage: str) -> str:
    """System prompt for one discovery stage (icon, fetch_jobs, ...)."""
    instr = _STAGE_INSTRUCTIONS[stage]
    return f"You are an extractor-discovery agent.\n\n{_SANDBOX_PREAMBLE}\n\n{instr}"


def stage_user_prompt(stage: str, company: str, url: str, prior: dict | None = None) -> str:
    """User prompt for a stage. `prior` carries results from earlier stages (8D)."""
    msg = f"Company: {company}\nCareers/site URL: {url}\nStage: {stage}\n"
    if prior:
        msg += f"\nResults from earlier stages: {prior}\n"
    msg += "\nSolve the stage above."
    return msg


# --- backwards-compatible aliases (the icon-only entry points still used by cli/discover) ---
def logo_system_prompt() -> str:
    return stage_system_prompt("icon")


def logo_user_prompt(company: str, url: str) -> str:
    return stage_user_prompt("icon", company, url)
