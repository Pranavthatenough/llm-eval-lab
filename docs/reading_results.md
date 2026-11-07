# Reading your results

A number without interpretation is noise. This page explains every metric the lab prints and the traps that come with each.

## Pass rates and confidence intervals

Every exercise prints lines like:

```
cases passed: 7/10 = 70%  (95% CI 40%-89%)
```

The **confidence interval** (Wilson interval, computed in `llmeval/report.py`) is the range the *true* pass rate plausibly sits in, given how few cases you ran. Rules of thumb:

| Cases | Roughly how precise is a ~70% pass rate? |
|---|---|
| 10 | +/- 25 points - only big differences are real |
| 50 | +/- 12 points |
| 200 | +/- 6 points |
| 1000 | +/- 3 points |

So if prompt A scores 70% and prompt B 80% on 10 cases, **you have not shown B is better**. If the intervals overlap heavily, call it a tie and add more cases (or run more repeats).

## Metric by metric

| Metric | Where | Good looks like | Watch out for |
|---|---|---|---|
| Exact / normalized / contains match | 1.3 | rises as output format tightens | exact = false negatives; contains = false positives |
| Distinct outputs | 1.2 | 1 at temp 0 + seed | temp 0 is "usually", not "always", deterministic |
| Check pass rate by tag | 2.1 | even across tags | one weak tag hides inside a good overall number |
| Strict JSON / schema / fields | 2.2 | all three high | schema enforcement fixes shape, not meaning |
| Flaky cases | 2.3 | few | flaky = users get inconsistent behaviour too |
| Judge-human agreement | 3.1 | >= 80-85% on pass/fail | **false passes** are the dangerous direction |
| Position consistency | 3.2 | right in both orders | a judge flipping with order is judging position |
| Hallucination rate | 4.1 | low on fakes **and** high accuracy on controls | refusing everything also scores 0% hallucination |
| Faithfulness | 4.2, 6.2 | 1.0 | judge errors compound when checking many claims |
| Agreement across samples | 4.3 | high on known, low (or consistent "unknown") on unknown | consistent ≠ correct |
| Attack success rate (ASR) | 5.1, 5.2 | low | single runs underestimate; attackers retry |
| Benign helpfulness | 5.1 | high | hardening often breaks normal requests |
| hit@k / recall@k / MRR | 6.1 | recall@k near 1 | hit@k hides multi-document misses |
| Diagnosis counts | 6.2 | mostly OK | SUSPICIOUS rows need a human look |
| Composite agent score | 7.2 | >= 0.8 with safe = true | safety is a gate, never averaged away |

## When results look wrong

1. **Everything passes.** Suspicious. Are your checks too loose (e.g. `contains` with a common word)? Is the provider `mock`?
2. **Everything fails.** Check one output by hand. Usually a format mismatch (code fences, quotes, "Sure! Here's...") or a broken check, not a broken model.
3. **Results change every run.** Expected at temperature > 0. Pin temperature and seed for regression; use repeats for anything you'll decide on.
4. **Judge-based metrics disagree with your gut.** Trust your gut enough to check: read the judge's reasoning in the CSV, then recalibrate (Phase 3).

## Comparing two versions (prompts or models)

- Run **the same dataset** with **the same judge** and **the same settings**.
- Compare per-case, not just totals: which cases flipped from pass to fail? Those are your regressions, even if the total went up.
- Use repeats for close calls. A difference smaller than the interval width is not a finding.
