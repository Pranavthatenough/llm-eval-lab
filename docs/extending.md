# Extending the lab

The lab is meant to become *your* test suite. Here's how to add to it.

## Add test cases (no code)

Every dataset is a JSONL file: one JSON object per line. Copy an existing line and edit it.

| File | Add a... |
|---|---|
| `phases/01_basics/data/golden.jsonl` | factual question + expected answer |
| `phases/02_deterministic_checks/data/cases.jsonl` | prompt + list of checks |
| `phases/03_llm_as_judge/data/graded_answers.jsonl` | answer + your human score |
| `phases/04_hallucination/data/fabrication_probes.jsonl` | fake-entity question or real control |
| `phases/05_prompt_injection/data/attacks.jsonl` | attack + how to detect success |
| `phases/06_rag_evaluation/data/questions.jsonl` | question + relevant docs + reference |
| `phases/07_agent_scoring/data/tasks.jsonl` | task + expected/forbidden tools + answer check |

Tip: validate a file quickly with `python -c "import json;[json.loads(l) for l in open('path.jsonl')]"`.

## Check types available in `cases.jsonl` and agent `answer_check`

```
exact_match {value}          normalized_match {value}      contains_all {values}
contains_any {values}        contains_none {values}        regex {pattern}
max_words {value}            min_words {value}             numeric_close {value, tolerance}
is_refusal                   not_refusal                   is_valid_json
json_schema {schema}
```
Any check can have a `label` that appears in reports.

## Add a new check

Write a function in `llmeval/checks.py` that returns `CheckResult(name, passed, detail)`, then register it in the `CHECKS` dict. It's immediately usable from every dataset.

## Test your own product's prompts

1. Put your system prompt in `prompts/my_feature.txt`.
2. Copy `phases/02_deterministic_checks/01_run_checks.py` and load it with `load_prompt("my_feature")`.
3. Write cases from your product's requirements and from real failures.
4. Add a zero-tolerance or threshold test for it in `phases/08_bonus_ci_regression/`.

## Add a new phase

Create `phases/09_your_topic/` with a README and numbered scripts, starting each script with the same two-line path setup used everywhere else, then add it to the `COURSE` list in `lab.py`. Use `report.banner`, `report.rate_line`, `report.explain` and `report.save_results` so it looks and behaves like the rest.

Ideas: bias and fairness probes (same question, swapped names), multi-turn conversation consistency, long-context "needle in a haystack" tests, toxicity checks, cost/latency budgets, comparing two models side by side with pairwise judging.
