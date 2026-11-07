# From classic QA to LLM evaluation

You already know most of what you need. This page maps familiar testing ideas onto LLM systems, and flags where they break.

| Classic QA | LLM equivalent | What changes |
|---|---|---|
| Test case | **Eval case**: input + expected properties (+ optional reference answer) | Expected *properties*, rarely an exact output |
| Assertion | **Check** (deterministic) or **judge** (model-graded) | Many "correct" outputs exist |
| Test oracle | Reference answer, rubric, or human label | The oracle problem is the central problem |
| Pass/fail | **Pass rate** over N runs or N cases | Results are statistical, so report intervals |
| Flaky test | Expected behaviour - **measure** it | Don't retry until green; record the rate |
| Regression suite | **Golden set** run on every prompt/model change | The "code" includes prompts and model versions |
| Test data | Datasets in JSONL, often grown from production failures | Labels need domain experts |
| Boundary testing | Unanswerable questions, fake entities, long contexts, edge formats | The "boundary" is fuzzy |
| Security testing | **Red teaming**, prompt injection, data exfiltration | Attacks are written in plain language |
| Performance testing | Latency, tokens, cost per request | Quality and cost trade off against each other |
| Exploratory testing | Prompt playground, reading outputs | Still the best way to find new failure modes |

## The eval pyramid

```
            /\         Human review: small samples, calibration, high-stakes calls
           /  \
          /    \       LLM judges: meaning, faithfulness, helpfulness - after calibration
         /------\
        /        \     Deterministic checks: format, schema, required/forbidden content,
       /__________\    length, canaries, tool-call rules - run on everything, always
```

Push as much as possible to the bottom layer. It's cheap, fast and exact. Use judges for what code can't see, and humans to keep the judges honest.

## What is the "system under test"?

Rarely just the model. It's the whole pipeline:

```
user input -> [system prompt + retrieved docs + tool results] -> MODEL -> output parsing -> actions
```

Bugs can live in any box: a bad system prompt, the wrong document retrieved, an injected instruction in a tool result, a parser that chokes on a code fence, a tool with no limits. Good LLM testing localises the failure to a box - Phase 6's diagnosis and Phase 7's trajectory scoring are both about that.

## Five habits that separate good LLM testers

1. **Read the outputs.** Metrics summarise; outputs explain. Open the CSV.
2. **Always include controls.** Every "does it refuse X" test needs a "does it still do Y" test.
3. **Report uncertainty.** "72% (95% CI 47-89%) on 15 cases" is honest. "72%" is not.
4. **Version everything.** Prompt, model, judge prompt, judge model, dataset. A score without those is unreproducible.
5. **Turn every bug into a case.** Every production failure becomes a row in a dataset, so it can never silently come back.
