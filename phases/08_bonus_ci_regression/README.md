# Phase 8 (bonus) - Evals as a CI regression gate

**Goal:** turn what you've built into automated checks that can block a bad prompt or model change from shipping.

```bash
pytest phases/08_bonus_ci_regression -v
EVAL_MIN_PASS_RATE=0.8 pytest phases/08_bonus_ci_regression -v     # stricter gate
```

## Concepts

You can't assert every LLM case individually - the suite would be red half the time from noise. Instead, use two kinds of gate:

| Gate | Example in `test_llm_regression.py` | Tolerance |
|---|---|---|
| **Quality threshold** | format-suite pass rate >= 70% | some failures OK; blocks big drops |
| **Zero tolerance** | canary never leaks; structured output always schema-valid | one failure blocks the build |

Choose zero-tolerance for security, safety and contracts other code depends on. Choose thresholds for fuzzy quality.

## The example workflow

`github_actions_example.yml` shows one way to run this on GitHub Actions: install Ollama on the runner, pull a small model, run pytest, upload `results/`. It only triggers when prompts, config or eval code change. Treat it as a starting point; CPU runners are slow, so keep CI suites small and run the big suites nightly.

## Challenges

1. Add a test that runs `07_agent_scoring` tasks and fails if *any* forbidden tool is called.
2. Store last week's pass rate in a file and fail if this week drops by more than 10 points (a trend gate instead of a fixed threshold).
3. Pick the right threshold: run the format suite 5 times and set the threshold just below the *lowest* rate you saw, so normal noise never fails the build.
