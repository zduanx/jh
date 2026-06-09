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
    tool: Literal["run_trial", "read_file", "write_file", "done", "fail"] = Field(
        description=("run_trial = execute python in the sandbox; "
                     "read_file = read a file under extractors_v2/; "
                     "write_file = write a file under extractors_v2/ (read it first if it exists); "
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
    content: Optional[str] = Field(
        default=None,
        description="For write_file: the FULL new content of the file.",
    )
    result: Optional[dict] = Field(
        default=None,
        description='For done: the final answer, e.g. {"icon_url": "...", "source": "apple-touch-icon", "confidence": "high"}.',
    )
    reason: Optional[str] = Field(default=None, description="For fail: why you're giving up.")


class AgentStep(BaseModel):
    """One structured turn from the agent (inner ReAct loop)."""
    thought: str = Field(description="Your internal reasoning for this step (kept in context).")
    summary: str = Field(description="A short one-line present-tense summary, for the terminal.")
    action: Action


# All stages the agent knows how to run (the order it should plan them in).
# validate_company runs FIRST — a sanity gate (real company? name matches domain?).
KNOWN_STAGES = ["validate_company", "icon", "write_extractor"]   # 8D adds: "fetch_jobs", "validate_jd"


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
- "write_extractor": write the extractor file + register the company.
(Later phases add: "fetch_jobs" = discover how to list all jobs; "validate_jd" = confirm a job page parses.)

Choose stages based on the GOAL, in a sensible order. For onboarding, ALWAYS start with "validate_company" (so garbage input fails before anything is written), then "icon", then "write_extractor". e.g. goal "onboard the company" → ["validate_company","icon","write_extractor"]; goal "just find the icon" → ["icon"]. Return the ordered stage list + brief reasoning."""


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
3. `<link rel="icon" ...>` (favicon) — icon-only; prefer the largest `sizes`. (Also try `/favicon.ico`.)
4. `<meta property="og:image" ...>` — LAST RESORT; usually the full logo WITH text.
Resolve relative URLs to absolute. Verify the candidate returns an image (HTTP 200 + image content-type). Only fall back to og:image if 1-3 yield nothing (then confidence "medium").

done result: {"icon_url":"...","source":"apple-touch-icon|manifest|favicon|og:image","confidence":"high|medium"}""",

    "write_extractor": """STAGE: write the company's extractor file AND register it — using the read_file / write_file tools. This is multi-file editing (like a coding agent), confined to extractors_v2/.

RULE: any file that already exists must be read_file'd BEFORE you write_file it (you edit real content, not a guess). The files below MAY already exist from a prior run — so read each one first; if it's already correct, you don't need to rewrite it.

Do these, in order:

1. read_file("extractors_v2/{company}.py") first. If it exists and is already correct, skip the write. Otherwise write_file("extractors_v2/{company}.py", <content>) where <content> is EXACTLY this shape (a subclass of BaseExtractorV2 with CLASS attributes named exactly COMPANY_NAME and ICON_URL — uppercase, as class vars, NOT module-level constants):

from typing import Any

from extractors_v2_base import BaseExtractorV2


class {Company}Extractor(BaseExtractorV2):
    COMPANY_NAME = "{company}"
    ICON_URL = "{the icon_url you discovered}"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        raise NotImplementedError("agent has not discovered _fetch_all_jobs yet")

   ({Company}Extractor = the company slug Capitalized + "Extractor", e.g. anthropic → AnthropicExtractor.)

2. read_file("extractors_v2/registry.py") — read the CURRENT registry (you MUST read before editing it).

3. write_file("extractors_v2/registry.py", <content>): take the EXACT content you just read, and (a) add a line `from extractors_v2.{company} import {Company}Extractor` next to the other imports, and (b) add `"{company}": {Company}Extractor,` inside the REGISTRY dict. Preserve everything else verbatim.

Use the prior stage's icon_url for ICON_URL. When both files are written, return done with {"wrote": ["extractors_v2/{company}.py", "extractors_v2/registry.py"]}.""",
    # 8D will add: "fetch_jobs": ..., "validate_jd": ...
}


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
