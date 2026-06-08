"""
Phase 7E — grade step (Python, hand-rolled LLM-as-judge).

Loads the triples captured by capture.js (eval/cases.captured.json) and scores them
for FAITHFULNESS — the anti-fabrication metric — using a hand-written LLM-as-judge
(the Anthropic SDK directly; no ragas/langchain).

Why hand-rolled, not Ragas: ragas 0.4.x has a broken dependency chain against
langchain 1.x (imports a removed module), and its answer_relevancy needs OpenAI
embeddings we don't have. A hand-rolled judge is fewer deps, fully owned/explainable
(ADR-029), and implements the SAME core algorithm Ragas uses for faithfulness:

  faithfulness = (answer claims SUPPORTED by the contexts) / (total answer claims)

  1. ask the judge to decompose the answer into atomic factual claims
  2. ask the judge, per claim, whether the contexts support it (yes/no)
  3. score = supported / total   (1.0 = fully grounded, low = fabricated)

Decomposing into binary per-claim judgments is far more stable than a holistic
"rate 0-1" (Decision C). Judge model is PINNED (Decision D).

Refusal cases (expectRefusal) are checked with a keyword heuristic, NOT faithfulness
(an empty-context refusal has no claims to ground).

Run:  ANTHROPIC_API_KEY=... python eval/run_eval.py
"""

import json
import os
import sys
from pathlib import Path

import anthropic

HERE = Path(__file__).parent
CAPTURED = HERE / "cases.captured.json"
ADVERSARIAL = HERE / "adversarial.json"  # hand-authored known-bad cases (detector self-test)

# An adversarial case must score AT OR BELOW this to prove the detector "bites".
ADVERSARIAL_MAX = float(os.environ.get("EVAL_ADVERSARIAL_MAX", "0.5"))

# PINNED judge model (Decision D — the measuring instrument). Record + re-baseline if changed.
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "claude-sonnet-4-6")
FAITHFULNESS_MIN = float(os.environ.get("EVAL_FAITHFULNESS_MIN", "0.85"))

# (Refusal detection used to be a brittle keyword list — it kept needing new
#  phrasings. Replaced with an LLM-judge check, consistent with faithfulness:
#  prose is too varied for keywords. See judge_refusal().)

_client = None
def client():
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("[eval] ANTHROPIC_API_KEY not set — export it before running.")
        _client = anthropic.Anthropic()
    return _client


def judge_json(prompt: str) -> dict:
    """Call the pinned judge at temp 0, expecting a JSON object back."""
    msg = client().messages.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    # Be tolerant of code fences.
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(text)


def judge_refusal(question: str, answer: str) -> bool:
    """
    LLM-judge: did the assistant appropriately DECLINE / say it lacks the data,
    rather than fabricating? Returns True if it correctly refused.

    (Replaces the old keyword heuristic — prose phrasings are too varied to
    enumerate; same LLM-as-judge pattern as faithfulness, just a yes/no question.)
    """
    prompt = f"""An assistant for a job-hunt app was asked something it should NOT answer with invented data — either because the data doesn't exist (no such saved job) or it's out of scope (not job-related).

QUESTION: {question}
ANSWER: {answer}

Did the assistant correctly DECLINE — i.e. say it doesn't have that data / can't help with that — WITHOUT fabricating specifics (fake jobs, companies, details)?

Respond with ONLY JSON: {{"declined": true|false}}"""
    return bool(judge_json(prompt).get("declined"))


def faithfulness_score(question: str, answer: str, contexts: list[str]) -> dict:
    """
    Decompose → judge each claim → score. Returns {score, claims:[{claim,supported}]}.
    """
    context_blob = "\n".join(contexts) or "(no context was retrieved)"
    prompt = f"""You are evaluating whether an AI assistant's answer is grounded in the data it retrieved.

QUESTION:
{question}

RETRIEVED CONTEXT (the only facts the assistant should rely on):
{context_blob}

ANSWER TO EVALUATE:
{answer}

Task:
1. Break the ANSWER into atomic factual CLAIMS (specific facts: job ids, titles, companies, counts, locations). Ignore generic offers/pleasantries ("want me to...", "let me check") — those are not factual claims.
2. For EACH claim, decide if it is SUPPORTED by the RETRIEVED CONTEXT (true/false). A claim is supported only if the context contains or directly entails it. Inventing a fact not in the context = not supported.

Respond with ONLY a JSON object, no prose:
{{"claims": [{{"claim": "<text>", "supported": true|false}}, ...]}}
If there are no factual claims, return {{"claims": []}}."""
    result = judge_json(prompt)
    claims = result.get("claims", [])
    if not claims:
        # No factual claims to ground → vacuously faithful (e.g. a pure clarifying reply).
        return {"score": 1.0, "claims": []}
    supported = sum(1 for c in claims if c.get("supported"))
    return {"score": supported / len(claims), "claims": claims}


def load_cases():
    if not CAPTURED.exists():
        sys.exit(f"[eval] {CAPTURED} not found — run `node eval/capture.js` first.")
    cases = json.loads(CAPTURED.read_text())
    errored = [c for c in cases if c.get("error")]
    if errored:
        print(f"[eval] WARNING: {len(errored)} case(s) errored in capture: {[c['id'] for c in errored]}")
    return cases


def load_adversarial():
    """Hand-authored known-bad cases — they MUST score low, proving the detector works.
    A faithfulness metric that never sees a hallucination is unproven (negative test)."""
    return json.loads(ADVERSARIAL.read_text()) if ADVERSARIAL.exists() else []


def check_adversarial(adv_cases):
    """Inverted assertion: each adversarial case must score <= ADVERSARIAL_MAX."""
    if not adv_cases:
        return []
    print(f"\n=== Adversarial self-test ({len(adv_cases)}) — these SHOULD score low ===")
    failures = []
    for c in adv_cases:
        r = faithfulness_score(c["question"], c["answer"], c.get("contexts") or [])
        bites = r["score"] <= ADVERSARIAL_MAX
        print(f"  {'✓' if bites else '✗'} {c['id']}: faithfulness={r['score']:.3f} "
              f"({'detector caught the hallucination' if bites else 'DETECTOR MISSED IT'})")
        if not bites:
            failures.append(c["id"])
    return failures


def check_refusals(cases):
    refusal_cases = [c for c in cases if c.get("expectRefusal")]
    print(f"\n=== Refusal / grounding-on-empty checks ({len(refusal_cases)}, LLM-judged) ===")
    failures = []
    for c in refusal_cases:
        declined = judge_refusal(c["question"], c.get("answer") or "")
        print(f"  {'✓' if declined else '✗'} {c['id']}: {'declined' if declined else 'DID NOT decline (fabricated?)'}")
        if not declined:
            failures.append(c["id"])
    return failures


def grade(cases):
    graded = [c for c in cases if not c.get("expectRefusal") and not c.get("error") and c.get("answer")]
    print(f"\n=== Faithfulness ({len(graded)} cases, judge={JUDGE_MODEL}) ===")
    scores = []
    for c in graded:
        r = faithfulness_score(c["question"], c["answer"], c.get("contexts") or [])
        scores.append(r["score"])
        n_unsupported = sum(1 for cl in r["claims"] if not cl.get("supported"))
        flag = "" if n_unsupported == 0 else f"  ⚠ {n_unsupported} unsupported claim(s)"
        print(f"  {c['id']:24s} faithfulness={r['score']:.3f}  ({len(r['claims'])} claims){flag}")
        for cl in r["claims"]:
            if not cl.get("supported"):
                print(f"        ✗ unsupported: {cl['claim'][:90]}")
    mean = sum(scores) / len(scores) if scores else 1.0
    print(f"\n  MEAN faithfulness = {mean:.3f}  (min {FAITHFULNESS_MIN})")
    return mean


def main():
    cases = load_cases()
    refusal_failures = check_refusals(cases)
    mean_faith = grade(cases)
    adversarial_failures = check_adversarial(load_adversarial())

    print("\n=== Verdict ===")
    failed = False
    if refusal_failures:
        print(f"  ✗ refusal cases that fabricated: {refusal_failures}")
        failed = True
    if mean_faith < FAITHFULNESS_MIN:
        print(f"  ✗ faithfulness {mean_faith:.3f} < {FAITHFULNESS_MIN}")
        failed = True
    if adversarial_failures:
        print(f"  ✗ adversarial cases the detector MISSED (scored too high): {adversarial_failures}")
        failed = True

    print("  RESULT:", "FAIL" if failed else "PASS ✅")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
