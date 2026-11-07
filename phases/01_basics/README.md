# Phase 1 - Basics: what are you actually testing?

**Goal:** understand what a model call really is, why its output varies, and why the way you score an answer can matter more than the answer itself.

## Concepts

**A model call is an HTTP request.** It contains a list of *messages* (system, user, assistant) and *settings* (temperature, seed, max tokens). The response contains text plus metadata - latency and token counts. All of it is testable.

**System vs user message.** The system message is the app's instructions (you control it). The user message is what the end user typed (you don't). Many LLM bugs - and all prompt-injection attacks - live in the tension between the two.

**Non-determinism.** The model predicts a probability for every possible next token, then *samples* one. Temperature controls how adventurous the sampling is. At 0 it nearly always picks the most likely token; above 0 it varies. Even at 0, outputs can change across hardware, versions and batching. So: `assert output == "expected"` is a flaky test by design.

**The oracle problem.** In classic testing you usually know the right output. With LLMs, many right answers exist ("Canberra", "The capital is Canberra.", "It's Canberra, not Sydney"). Deciding *what counts as correct* is the core skill of LLM evaluation.

## Exercises

| # | Run | What you'll see |
|---|---|---|
| 1.1 | `python lab.py run 1.1` | The exact request, response, latency and tokens. Run it twice to see a cold vs warm start. Pass your own question as an argument. |
| 1.2 | `python lab.py run 1.2` | The same prompt five times under three settings, and how many *distinct* answers come back. |
| 1.3 | `python lab.py run 1.3` | Eight factual questions scored three ways. Same answers, three very different pass rates. |
| 1.4 | `python lab.py run 1.4` | Hand-picked prompts that expose counting failures, reasoning traps, format sloppiness and hallucination. |

## Reading your results

- **1.2:** "1 distinct output out of 5" at temperature 0 with a seed is what you want for regression runs. Several distinct outputs at temperature 1.0 is normal - and is what production users get if your app runs at that temperature.
- **1.3:** a very low exact-match rate alongside a high "contains" rate means the model is *right but chatty*. That's a format problem, not a knowledge problem - fix the prompt or the metric. Then look at the confidence interval: with 8 cases, numbers are rough estimates, not facts.
- **1.4:** there is no automated score. You are the judge. Open the CSV in `results/` and fill in `your_verdict`. You've just made human labels - Phase 3 uses exactly this kind of data to test an automated judge.

## Break it (challenges)

1. In `03_first_eval.py`, add `system="Answer with only the answer, no sentence."` to `llm.ask()`. How much does exact match improve? Did anything get *worse*?
2. Add three questions of your own to `data/golden.jsonl`, including one where "contains" would give a false pass.
3. Change `target.model` in `config.yaml` to a different model (e.g. `qwen3:4b`), pull it, and rerun 1.3 and 1.4. Which model is better *on these cases*?

## Real-world notes

- Record the model name, version and settings with every result (the lab saves them in each JSON file). "It passed last week" means nothing if the model changed.
- Latency and token count are product metrics. A prompt that's 20% more accurate and 3x slower may still be the wrong choice.
