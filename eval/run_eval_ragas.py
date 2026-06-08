"""
Phase 7E — Ragas runner (the recognizable RAG-eval library).

A SECOND grader alongside the hand-rolled run_eval.py — same captured data, scored
by Ragas instead. Purpose: (1) use the standard, named tool; (2) cross-validate the
hand-rolled judge (if both agree, the metric is trustworthy).

Same metric: FAITHFULNESS (claims supported by context / total claims). Ragas does
the claim-decomposition + per-claim judgment internally; we just feed it the triples.

Judge = Anthropic (Claude), NOT OpenAI — Ragas defaults to OpenAI but is configurable.
Faithfulness is LLM-only (no embeddings), so we need NO embedding provider at all.

Install (isolated venv — ragas 0.4.x is broken vs langchain 1.x, so pin 0.2.x):
    python3 -m venv eval/.venv-ragas
    eval/.venv-ragas/bin/pip install ragas==0.2.10 langchain-community==0.3.3 \
        langchain-anthropic datasets

Run:
    ANTHROPIC_API_KEY=... eval/.venv-ragas/bin/python eval/run_eval_ragas.py
"""

import json
import os
import re
import sys
from pathlib import Path

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, AspectCritic
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_anthropic import ChatAnthropic
from langchain_voyageai import VoyageAIEmbeddings

HERE = Path(__file__).parent
CAPTURED = HERE / "cases.captured.json"

JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "claude-sonnet-4-6")
FAITHFULNESS_MIN = float(os.environ.get("EVAL_FAITHFULNESS_MIN", "0.85"))


def normalize_markdown(text: str) -> str:
    """
    Flatten markdown to plain prose so Ragas's statement-segmenter can extract clean
    claims. Ragas chokes on markdown tables/lists/bold (it mis-segmented a fully
    grounded answer to faithfulness=0.000 — a tool artifact, not a hallucination).
    Stripping formatting preserves the FACTS while removing what trips the segmenter.
    This is input normalization (fit-the-tool), not score-gaming — the claims are
    unchanged; only the markup is removed.
    """
    t = text
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)      # **bold** → bold
    t = re.sub(r"\*(.+?)\*", r"\1", t)          # *italic* → italic
    t = re.sub(r"`(.+?)`", r"\1", t)            # `code` → code
    t = re.sub(r"^\s*[-*]\s+", "", t, flags=re.M)   # bullet markers
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.M)  # numbered-list markers
    t = re.sub(r"\|", " ", t)                   # table pipes → spaces
    t = re.sub(r"^[\s:|-]+$", "", t, flags=re.M)    # table separator rows
    t = re.sub(r"#(\d+)", r"number \1", t)      # "Job #1930" → "Job number 1930"
    t = re.sub(r"\n{2,}", ". ", t)              # paragraph breaks → sentence breaks
    t = re.sub(r"\s+", " ", t).strip()          # collapse whitespace
    return t


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("[ragas] ANTHROPIC_API_KEY not set.")
    if not os.environ.get("VOYAGE_API_KEY"):
        sys.exit("[ragas] VOYAGE_API_KEY not set (needed for answer_relevancy embeddings).")
    if not CAPTURED.exists():
        sys.exit(f"[ragas] {CAPTURED} not found — run `node eval/capture.js` first.")

    cases = json.loads(CAPTURED.read_text())
    # Grade the same gradable cases as the hand-rolled runner (skip refusals/errors).
    graded = [c for c in cases if not c.get("expectRefusal") and not c.get("error") and c.get("answer")]
    if not graded:
        sys.exit("[ragas] no gradable cases.")

    # Judge = Anthropic (NOT OpenAI). Ragas's claim-decomposition prompts are verbose
    # → give generous output room (1024 caused LLMDidNotFinishException on long answers).
    judge = LangchainLLMWrapper(ChatAnthropic(model=JUDGE_MODEL, temperature=0, max_tokens=4096))

    # Embeddings = Voyage (same model the app uses, voyage-3). Needed by
    # answer_relevancy (it embeds the question vs. a question regenerated from the
    # answer, and measures cosine similarity). faithfulness ignores this.
    embeddings = LangchainEmbeddingsWrapper(VoyageAIEmbeddings(model="voyage-3"))

    # --- Customize faithfulness to grade FACTS only (Approach #1) ---
    # Off-the-shelf faithfulness turns conversational framing ("Let me check!",
    # "Want me to dive deeper?") into statements and marks them unsupported — which
    # penalizes warmth, not fabrication. We append an exclusion clause to its
    # statement-EXTRACTION prompt so filler never becomes a gradable claim. This is
    # the principled fix: faithfulness should concern verifiable facts, not tone.
    extract_prompt = faithfulness.get_prompts()["long_form_answer_prompt"]
    extract_prompt.instruction += (
        " IMPORTANT: extract ONLY verifiable factual claims (entities, ids, names, "
        "counts, attributes). DO NOT create statements from conversational framing — "
        "greetings, offers to help, follow-up questions, or hedges (e.g. 'Let me "
        "check', 'Want me to dive deeper?', 'Here are your top jobs'). Such filler is "
        "not a factual claim and must be omitted."
    )
    faithfulness.set_prompts(long_form_answer_prompt=extract_prompt)

    # --- Multi-dimensional eval (Approach #2): warmth & conciseness as their OWN
    # metrics, graded POSITIVELY and independently of faithfulness. AspectCritic =
    # a yes/no LLM rubric judge (score = pass-rate). This closes the blind spot where
    # a cold, robotic-but-grounded answer would score faithfulness=1.0 and look fine.
    warmth = AspectCritic(
        name="warmth",
        definition="Is the response friendly, warm, and helpful in tone — does it "
        "engage conversationally (e.g. acknowledges the user, offers a helpful next "
        "step) rather than being terse or robotic?",
        llm=judge,
    )
    conciseness = AspectCritic(
        name="conciseness",
        definition="Is the response appropriately concise — informative without "
        "unnecessary padding or repetition?",
        llm=judge,
    )

    print(f"=== Ragas ({len(graded)} cases, judge={JUDGE_MODEL}, embeddings=voyage-3) ===")
    print("    faithfulness (facts, filler-excluded #1) · answer_relevancy ·")
    print("    warmth & conciseness (AspectCritic, multi-dimensional #2)")

    # FACT metrics run on NORMALIZED text (clean claim extraction); TONE metrics run
    # on the ORIGINAL answer (warmth lives in the markdown/phrasing we'd strip).
    ds_facts = Dataset.from_list([
        {
            "user_input": c["question"],
            "response": normalize_markdown(c["answer"]),
            "retrieved_contexts": c["contexts"] or [""],
        }
        for c in graded
    ])
    ds_tone = Dataset.from_list([
        {
            "user_input": c["question"],
            "response": c["answer"],  # original, formatting + warmth intact
            "retrieved_contexts": c["contexts"] or [""],
        }
        for c in graded
    ])

    # faithfulness = grounded-ness (LLM); answer_relevancy = addresses the Q (LLM+emb).
    fact_df = evaluate(
        ds_facts,
        metrics=[faithfulness, answer_relevancy],
        llm=judge,
        embeddings=embeddings,
    ).to_pandas()

    # warmth + conciseness on the ORIGINAL answer (tone dimension).
    tone_df = evaluate(ds_tone, metrics=[warmth, conciseness], llm=judge).to_pandas()

    print()
    print(f"  {'case':24s} {'faith':>6s} {'relev':>6s} {'warmth':>7s} {'concise':>8s}")
    for i, c in enumerate(graded):
        f = fact_df.iloc[i]
        t = tone_df.iloc[i]
        print(f"  {c['id']:24s} {f['faithfulness']:6.3f} {f['answer_relevancy']:6.3f} "
              f"{t['warmth']:7.0f} {t['conciseness']:8.0f}")

    mean_faith = float(fact_df["faithfulness"].mean())
    mean_rel = float(fact_df["answer_relevancy"].mean())
    mean_warmth = float(tone_df["warmth"].mean())      # AspectCritic = 0/1 → pass-rate
    mean_concise = float(tone_df["conciseness"].mean())
    print(f"\n  MEAN faithfulness     = {mean_faith:.3f}   (min {FAITHFULNESS_MIN}, fact grounding)")
    print(f"  MEAN answer_relevancy = {mean_rel:.3f}   (addresses the question)")
    print(f"  warmth pass-rate      = {mean_warmth:.0%}   (friendly/helpful tone)")
    print(f"  conciseness pass-rate = {mean_concise:.0%}   (not bloated)")

    # Gate on faithfulness (the safety-critical dim). warmth/conciseness are tracked
    # signals, not hard gates (Approach #2: measure each dimension on its own terms).
    print("\n  RESULT:", "PASS ✅" if mean_faith >= FAITHFULNESS_MIN else "FAIL (faithfulness)")
    sys.exit(0 if mean_faith >= FAITHFULNESS_MIN else 1)


if __name__ == "__main__":
    main()
