/**
 * Phase 7E — chat agent evaluation test set.
 *
 * Curated cases over the chatbox's real query types (drawn from the 7C/7D E2E
 * traces), plus a hallucination-bait case. Each case is run through the REAL agent
 * by capture.js, which records {question, answer, contexts} for Ragas to grade.
 *
 * Fields:
 *   id        - stable case id (for reports)
 *   uid       - which user to run as. Use a user with real data (prod uid=1 has
 *               489 embedded jobs). Override via EVAL_UID env if needed.
 *   question  - the user message for this turn
 *   history   - optional prior turns [{role,content}] for multi-turn cases
 *               (the driver threads these as the conversation before `question`)
 *   expectRefusal - true for "no data" cases: the agent SHOULD say it has nothing,
 *                   NOT fabricate. (Used for a grounding assertion, not Ragas.)
 *
 * NOTE: faithfulness is reference-free — we do NOT predefine "good answers".
 * We only need the question; the answer + contexts are captured at run time.
 */

// Default eval user — a user with real embedded jobs (prod uid=1). Override: EVAL_UID=18
export const EVAL_UID = Number(process.env.EVAL_UID || 1);

export const CASES = [
  {
    id: 'topic-backend',
    question: 'show me my top 3 backend infrastructure jobs, with names and ids',
  },
  {
    id: 'topic-ml',
    question: 'what machine learning jobs do I have? list a couple with ids',
  },
  {
    id: 'company-filter',
    question: 'do I have any jobs at OpenAI? name a few',
  },
  {
    id: 'job-detail',
    // 163 isn't saved for this user → get_job returns null → agent says so.
    // It's a grounded-on-empty REFUSAL (like Walmart): faithfulness doesn't apply
    // (no claims to ground); the refusal check verifies it declined, not fabricated.
    question: 'tell me about job 163 — what does the role involve?',
    expectRefusal: true,
  },
  {
    id: 'no-data-walmart',
    // Hallucination bait: there are (almost certainly) no Walmart jobs saved.
    // The agent MUST say so, not invent one.
    question: 'I think I have a job at Walmart — tell me about it',
    expectRefusal: true,
  },
  {
    id: 'off-topic-weather',
    // Out of scope: should decline / redirect, not fabricate a job answer.
    question: "what's the weather today?",
    expectRefusal: true,
  },
  {
    id: 'multi-turn-followup',
    // Multi-turn: the answer to "which is #1?" must come from the prior turn's list.
    history: [
      { role: 'user', content: 'list my top 2 backend jobs with ids' },
      {
        role: 'assistant',
        content:
          'Your top 2 backend jobs are: 1) Job 163 — Software Engineer, Backend at OpenAI; 2) Job 1527 — Backend Software Engineer, Applied Foundations at OpenAI.',
      },
    ],
    question: 'what is the id of the number 1 job you just listed?',
  },
];

// Pass thresholds (Decision C: thresholds with margin, not exact scores).
export const THRESHOLDS = {
  faithfulness: 0.85, // mean faithfulness across grounded cases must be >= this
  answer_relevancy: 0.7,
};
