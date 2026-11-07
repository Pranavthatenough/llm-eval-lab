# Phase 3 - LLM as a judge

**Goal:** use a model to grade open-ended answers - and, more importantly, test whether that grader can be trusted.

## Concepts

**When code can't judge.** "Is this summary faithful?", "Is this explanation correct?", "Is this answer helpful?" No regex can answer those. An LLM judge can, approximately.

**Anatomy of a good judge** (see `prompts/judge_score.txt`):
1. **A rubric** that defines each score level in words, not just "rate 1-5".
2. **Reasoning first, score second.** The judge explains, then decides - this measurably improves consistency.
3. **Structured output** (JSON schema) so scores parse every time.
4. **Temperature 0** for repeatability.
5. **A reference answer**, when you have one - by far the biggest accuracy boost.

**Three judge styles** (all in `llmeval/judge.py`):
- *Score* (1-5 against criteria) - for absolute quality
- *Pairwise* (A vs B) - for comparing two prompts/models; often more reliable than absolute scores
- *Binary* (yes/no question) - for narrow facts like "is this claim supported by the context?" Used heavily in Phases 4-6.

**The judge is a measuring instrument.** Before you trust a thermometer, you calibrate it against known temperatures. Before you trust a judge, you compare it against **human labels** on your own data.

**Known biases:**
- *Position bias* - prefers the first (or second) answer shown
- *Verbosity bias* - prefers longer, more confident answers
- *Self-preference* - rates outputs from its own model family higher
- *Inconsistency* - different grade for the same input on re-runs

## Exercises

| # | Run | What you'll see |
|---|---|---|
| 3.1 | `python lab.py run 3.1` | 12 human-labelled answers (with deliberate traps) graded by the judge with and without a reference. Agreement, error and false passes. |
| 3.2 | `python lab.py run 3.2` | Pairs with one objectively better answer, judged in both orders; then one answer graded 5 times. |

## Reading your results

- **Pass/fail agreement** (judge's >=4 vs human's >=4) is the number to watch. Rough guide: below ~80-85% on your data, don't automate decisions with this judge.
- **False passes** (judge says good, human says bad) are worse than false fails. They let bugs ship with a green dashboard.
- **With vs without reference:** the gap shows how much the judge relies on its own knowledge. A big gap means: write reference answers.
- **3.2:** a pair judged right in one order and wrong in the other means the judge is reacting to *position*, not content. A long wrong answer beating a short right one is verbosity bias.

## Break it (challenges)

1. Delete the line "Judge correctness and substance, NOT length or confidence" from `prompts/judge_score.txt` and rerun 3.1. Did false passes on j2/j12 go up?
2. Set `judge.model` to the same model as the target (`llama3.2:3b`) and rerun both exercises. How much worse is a small judge?
3. Add your own labelled answers to `data/graded_answers.jsonl` from Phase 1.4's CSV.
4. Implement "judge both orders, count a win only if both agree" in a copy of `02_judge_biases.py`.

## Real-world notes

- Version the judge prompt and judge model like code. Changing either changes every score built on top.
- A judge's score is only comparable to scores from the *same* judge setup. Don't compare last month's numbers from a different judge.
- Keep a small "judge calibration set" of human-labelled examples and rerun it whenever the judge changes. That's exactly what 3.1 is.
