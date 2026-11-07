# Phase 2 - Deterministic checks

**Goal:** write assertions that still work when the output text changes every run, and learn to treat flakiness as a measurement rather than a nuisance.

## Concepts

**Assert properties, not strings.** You can't predict the exact words, but you can check:

| Property | Check (in `llmeval/checks.py`) | Example |
|---|---|---|
| Format | `regex`, `is_valid_json`, `json_schema` | "only a date in YYYY-MM-DD" |
| Required content | `contains_all`, `contains_any`, `numeric_close` | "mentions the breaking change" |
| Forbidden content | `contains_none` | "never names a competitor", "no DROP TABLE" |
| Length | `max_words`, `min_words` | "summary at most 30 words" |
| Behaviour | `is_refusal`, `not_refusal` | "doesn't refuse a harmless question" |

These checks are plain code: fast, free, explainable, 100% repeatable. **Use them for everything they can catch**, and only reach for an LLM judge (Phase 3) for meaning.

**Data-driven tests.** Cases live in `data/cases.jsonl`, separate from the code - just like a test-data sheet. Each case has a prompt, an optional system message, tags, and a list of checks:

```json
{"id": "commit-msg", "tags": ["format", "length"],
 "prompt": "Write a one-line git commit message for: ...",
 "checks": [{"type": "regex", "pattern": "\\A[^\\n]+\\Z", "label": "single line"},
            {"type": "max_words", "value": 15}]}
```

**Structured output.** Ollama (and most APIs) can *enforce* a JSON schema on output. That guarantees shape, never truth.

**Flakiness as a rate.** Run a case N times. 5/5 = stable pass, 0/5 = stable fail, anything else = flaky with a measurable pass rate. Gate releases on rates and thresholds, not single runs.

## Exercises

| # | Run | What you'll see |
|---|---|---|
| 2.1 | `python lab.py run 2.1` (or `... 01_run_checks.py --tag safety`) | 10 cases, each with several checks, plus pass rates by tag |
| 2.2 | `python lab.py run 2.2` | Ticket extraction with and without schema enforcement, scored on three separate layers |
| 2.3 | `python lab.py run 2.3` | Every case run 3x at temperature 0.7 and classified stable/flaky |

## Reading your results

- **2.1:** For every FAIL, decide: *model bug or test bug?* A check that rejects a correct answer is a broken test. The per-tag breakdown tells you where the model is weak.
- **2.2:** Expect schema enforcement to push "valid JSON" and "matches schema" near 100% while "all fields correct" barely moves. Three layers, three different failure causes, three different fixes.
- **2.3:** The number of FLAKY cases is your test suite's noise level. If it's high, a single CI run can't tell a regression from bad luck.

## Break it (challenges)

1. Write a case that *should* pass but your check wrongly fails (a false negative), then fix the check.
2. Add a case for a feature you test at work - for example "the error message must include the error code and must not include a stack trace."
3. In 2.2, the priority labels are judgement calls. Change one expected label you disagree with. Notice how ambiguous labels create "failures" that aren't real.
4. Run `03_flakiness.py --temperature 0` and compare. How much flakiness was sampling, and how much is a genuinely ambiguous prompt?

## Real-world notes

- Contract tests for LLM features are usually deterministic: valid JSON, required keys, allowed enum values, max length. These run on every commit.
- Always save the raw output next to the verdict. Debugging an LLM test failure without the output is guesswork.
