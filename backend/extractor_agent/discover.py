"""
Extractor-discovery agent (Phase 8C) — Plan-and-Execute (outer) + ReAct (inner).

Structure:
  run_agent(company, url, goal)
    1. PLAN  (one LLM turn) → which stages to run, in order  [Plan-and-Execute]
    2. for each stage: run_stage(stage) → an inner ReAct loop:
         LLM turn (validated {thought, summary, action})
           → run_trial(code) in the Docker SANDBOX → observe → retry
           → until "done" (solved) / "fail" / step cap
    3. return the per-stage results
  (8C has one real stage: "icon". 8D adds fetch_jobs/validate_jd — just more stages.)

The BRAIN runs on the host (Anthropic, has the key); only TRIAL CODE runs in the
sandboxed container. Terminal prints the plan + "[stage] [step N] summary" per turn.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import anthropic
from pydantic import ValidationError

from .prompts import (
    ACTION_SCHEMA, PLAN_SCHEMA, AgentStep, Plan,
    plan_system_prompt, plan_user_prompt,
    stage_system_prompt, stage_user_prompt,
)
from .sandbox.host_harness import run_trial
from .tools import FileTools, FileToolError

MODEL = os.environ.get("EXTRACTOR_AGENT_MODEL", "claude-sonnet-4-6")
MAX_STEPS = int(os.environ.get("EXTRACTOR_AGENT_MAX_STEPS", "8"))

# ANSI for readable terminal stepping
_DIM, _CYAN, _GREEN, _RED, _YELLOW, _BOLD, _RESET = (
    "\033[2m", "\033[36m", "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[0m"
)


def _indent(s: str, prefix: str = "│ ") -> str:
    """Indent each line (for the --d LLM I/O blocks)."""
    return "\n".join(prefix + line for line in str(s).splitlines())


def _brief(content, limit: int = 1200) -> str:
    """Truncate long message content for the --d view (keep it readable)."""
    s = content if isinstance(content, str) else json.dumps(content)
    return s if len(s) <= limit else s[:limit] + f"… (+{len(s) - limit} chars)"


@dataclass
class StageOutcome:
    stage: str
    ok: bool
    result: dict | None = None
    reason: str | None = None
    steps: int = 0


@dataclass
class AgentOutcome:
    company: str
    url: str
    ok: bool                                   # did ALL planned stages succeed?
    plan: list[str] = field(default_factory=list)
    stages: list[StageOutcome] = field(default_factory=list)

    def result_for(self, stage: str) -> dict | None:
        for s in self.stages:
            if s.stage == stage and s.ok:
                return s.result
        return None

    @property
    def merged_results(self) -> dict:
        """All successful stage results merged into one dict (for apply.py)."""
        out: dict = {}
        for s in self.stages:
            if s.ok and s.result:
                out.update(s.result)
        return out


def _client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set (the agent brain needs it)")
    return anthropic.Anthropic()


def _say(verbose: bool, s: str):
    if verbose:
        print(s)


# --------------------------------------------------------------------------- #
# Structured LLM turns (validated via Pydantic; retry on malformed)
# --------------------------------------------------------------------------- #
def _structured(client, system: str, messages: list[dict], schema: dict, name: str,
                *, debug: bool = False) -> dict:
    """One forced-structured LLM turn → raw dict matching `schema`.

    debug=True: print the LLM I/O — the system prompt (first turn), the latest message
    the orchestrator sent, and the raw structured object the LLM returned.
    """
    if debug:
        # Show what the ORCHESTRATOR sends the LLM this turn.
        if len(messages) == 1:   # first turn of a stage → show the system prompt too
            print(f"{_DIM}┌─ → LLM system ─\n{_indent(system)}\n└─{_RESET}")
        last = messages[-1]
        print(f"{_DIM}┌─ → LLM ({last['role']}) ─\n{_indent(_brief(last['content']))}\n└─{_RESET}")

    resp = client.messages.create(
        model=MODEL, max_tokens=2048, temperature=0, system=system,
        tools=[{"name": name, "description": "Return structured data.", "input_schema": schema}],
        tool_choice={"type": "tool", "name": name},
        messages=messages,
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == name:
            if debug:
                # Show what the LLM RETURNED (the raw structured object).
                print(f"{_DIM}┌─ ← LLM returned ─\n{_indent(json.dumps(block.input, indent=2))}\n└─{_RESET}")
            return block.input
    raise RuntimeError("model did not return structured output")


def _ask_step(client, system: str, messages: list[dict], *, retries: int = 1, debug: bool = False) -> AgentStep:
    """One inner-loop turn → a VALIDATED AgentStep (retry on schema-invalid)."""
    for attempt in range(retries + 1):
        raw = _structured(client, system, messages, ACTION_SCHEMA, "step", debug=debug)
        try:
            return AgentStep.model_validate(raw)
        except ValidationError as e:
            if attempt >= retries:
                raise
            messages.append({"role": "assistant", "content": json.dumps(raw)})
            messages.append({"role": "user", "content": f"Your previous step was invalid:\n{e}\nReturn a valid step."})
    raise RuntimeError("unreachable")


def _make_plan(client, company: str, url: str, goal: str, *, debug: bool = False) -> Plan:
    """The OUTER plan turn → which stages to run, in order."""
    raw = _structured(
        client, plan_system_prompt(),
        [{"role": "user", "content": plan_user_prompt(company, url, goal)}],
        PLAN_SCHEMA, "plan", debug=debug,
    )
    return Plan.model_validate(raw)


# --------------------------------------------------------------------------- #
# Inner ReAct loop — one stage
# --------------------------------------------------------------------------- #
def run_stage(client, stage: str, company: str, url: str, *, files: FileTools,
              prior: dict | None = None, verbose: bool = True, debug: bool = False) -> StageOutcome:
    """Run the inner ReAct loop for ONE stage until it solves or gives up."""
    system = stage_system_prompt(stage)
    messages: list[dict] = [{"role": "user", "content": stage_user_prompt(stage, company, url, prior)}]

    def say(s): _say(verbose, s)

    say(f"{_CYAN}── stage: {stage} ──{_RESET}")

    for step in range(1, MAX_STEPS + 1):
        # Transient "contacting LLM…" line — but NOT in debug (the I/O blocks print there).
        if verbose and not debug:
            print(f"{_DIM}[{stage} - step {step}] contacting LLM…{_RESET}", end="\r", flush=True)
        turn = _ask_step(client, system, messages, debug=debug)
        if verbose and not debug:
            print("\033[2K", end="\r")  # clear the transient line
        action = turn.action

        say(f"{_GREEN}[{stage} - step {step}]{_RESET} {turn.summary}")
        if turn.thought:
            say(f"  {_DIM}thought: {turn.thought if debug else turn.thought[:140]}{_RESET}")
        messages.append({"role": "assistant", "content": turn.model_dump_json()})

        if action.tool == "done":
            result = action.result or {}
            say(f"{_GREEN}  ✓ {stage} done:{_RESET} {json.dumps(result)}")
            return StageOutcome(stage=stage, ok=True, result=result, steps=step)

        if action.tool == "fail":
            reason = action.reason or "(no reason)"
            say(f"{_RED}  ✗ {stage} failed:{_RESET} {reason}")
            return StageOutcome(stage=stage, ok=False, reason=reason, steps=step)

        if action.tool == "run_trial":
            code = action.code or ""
            say(f"  {_DIM}→ run_trial ({len(code)} chars) in sandbox…{_RESET}")
            if debug:
                say(f"{_DIM}--- trial code ---\n{code}\n------------------{_RESET}")
            tr = run_trial(code)
            observation = {"ok": tr.ok, "result": tr.result, "stdout": (tr.stdout or "")[:1500],
                           "error": tr.error, "timed_out": tr.timed_out}
            outcome_str = "ok" if tr.ok else ("timeout" if tr.timed_out else f"error: {tr.error}")
            say(f"  {_DIM}← {outcome_str}{(': ' + json.dumps(tr.result)[:120]) if tr.ok and tr.result is not None else ''}{_RESET}")
            messages.append({"role": "user", "content": f"Trial result:\n{json.dumps(observation)}"})
            continue

        if action.tool == "read_file":
            try:
                res = files.read_file(action.path or "")
                say(f"  {_DIM}→ read_file {action.path} (exists={res['exists']}, {len(res['content'])} chars){_RESET}")
                messages.append({"role": "user", "content": f"read_file result:\n{json.dumps(res)}"})
            except FileToolError as e:
                say(f"  {_RED}→ read_file refused: {e}{_RESET}")
                messages.append({"role": "user", "content": f"read_file error: {e}"})
            continue

        if action.tool == "write_file":
            try:
                if debug:
                    say(f"{_DIM}--- write {action.path} ---\n{action.content or ''}\n------------------{_RESET}")
                res = files.write_file(action.path or "", action.content or "")
                verb = "overwrote" if res["overwrote"] else "wrote"
                say(f"  {_GREEN}→ {verb} {action.path}{_RESET} {_DIM}({res['bytes']} bytes){_RESET}")
                messages.append({"role": "user", "content": f"write_file result:\n{json.dumps(res)}"})
            except FileToolError as e:
                say(f"  {_RED}→ write_file refused: {e}{_RESET}")
                messages.append({"role": "user", "content": f"write_file error: {e}"})
            continue
        # (Action.tool is a Literal — Pydantic rejects anything else.)

    say(f"{_YELLOW}  ⚠ {stage}: hit max steps ({MAX_STEPS}) without converging{_RESET}")
    return StageOutcome(stage=stage, ok=False, reason=f"exceeded {MAX_STEPS} steps", steps=MAX_STEPS)


# --------------------------------------------------------------------------- #
# Outer Plan-and-Execute
# --------------------------------------------------------------------------- #
def run_agent(company: str, url: str, *, goal: str = "onboard the company (icon + write the extractor)",
              verbose: bool = True, debug: bool = False) -> AgentOutcome:
    """Plan the stages, then execute each one's ReAct loop. Returns AgentOutcome."""
    client = _client()
    files = FileTools()   # one read/write session shared across stages (read-before-write)

    _say(verbose, f"{_CYAN}{_BOLD}=== extractor agent: {company} ({url}) ==={_RESET}")
    _say(verbose, f"{_DIM}goal: {goal}{_RESET}")
    if verbose and not debug:
        print(f"{_DIM}planning…{_RESET}", end="\r", flush=True)
    plan = _make_plan(client, company, url, goal, debug=debug)
    if verbose:
        print("\033[2K", end="\r")
    # Show the plan clearly: the reasoning + the ordered stage list.
    _say(verbose, f"{_BOLD}PLAN{_RESET} {_DIM}({plan.thought}){_RESET}")
    for i, st in enumerate(plan.stages, 1):
        _say(verbose, f"  {_BOLD}{i}.{_RESET} {st}")
    _say(verbose, "")

    outcome = AgentOutcome(company=company, url=url, ok=True, plan=plan.stages)
    prior: dict = {}
    for stage in plan.stages:
        so = run_stage(client, stage, company, url, files=files, prior=prior, verbose=verbose, debug=debug)
        outcome.stages.append(so)

        # A stage can fail two ways: (1) it returned `fail`, or (2) it returned `done`
        # but its result says valid=false (a GATE stage like validate_company judged the
        # input invalid). We ENFORCE the gate in code — the LLM does the judgment
        # (valid:false), our code stops the pipeline, rather than trusting the LLM to
        # route judgment → the `fail` tool. Don't proceed to write anything.
        result = so.result or {}
        gated_out = result.get("valid") is False
        if not so.ok or gated_out:
            outcome.ok = False
            if gated_out:
                so.ok = False
                so.reason = result.get("reasoning") or so.reason or f"{stage}: not valid"
                _say(verbose, f"{_RED}  ✗ {stage}: invalid → stopping (nothing written){_RESET}")
            break
        if so.result:
            prior.update(so.result)        # later stages see earlier results (8D)

    return outcome
