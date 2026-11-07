# LLM Eval Lab

**A hands-on course in testing LLM systems, built for QA and test engineers.**
Everything runs locally with [Ollama](https://ollama.com) - no API keys, no cloud bill.

You'll start by making one model call with nothing hidden, and finish by scoring a tool-using agent on safety and trajectory. Along the way you will *see things break*: hallucinated research papers, leaked secrets, judges fooled by long answers, RAG systems answering from the wrong document. Every exercise ends by explaining **what the numbers mean** - because a score you can't interpret is worse than no score.

```
 Phase 0  Setup ............................ is everything wired up?
 Phase 1  Basics ........................... what are you actually testing?
 Phase 2  Deterministic checks ............. assertions that survive non-determinism
 Phase 3  LLM as a judge ................... using a model to grade a model (and testing the grader)
 Phase 4  Hallucination .................... catching confident nonsense
 Phase 5  Prompt injection ................. attacking your own bot, measuring defences
 Phase 6  RAG evaluation ................... retrieval vs generation: where did it break?
 Phase 7  Agent scoring .................... outcome, trajectory, safety, cost
 Phase 8  Bonus: CI regression gate ........ evals as pytest quality gates
```

## Quick start (about 10 minutes)

```bash
# 1. Install Ollama from https://ollama.com/download (or see SETUP.md), then pull 3 models:
ollama pull llama3.2:3b        # the model you'll TEST   (~2 GB)
ollama pull llama3.1:8b        # the JUDGE model          (~5 GB)
ollama pull nomic-embed-text   # EMBEDDINGS for RAG       (~0.3 GB)

# 2. Set up Python (3.10+)
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Check everything works
python phases/00_setup/check_setup.py

# 4. Start the course
python lab.py                  # shows the course map
python lab.py run 1.1          # runs the first exercise
```

No Ollama yet? You can still check the plumbing with the fake offline model:
`LLMEVAL_PROVIDER=mock python lab.py run 1.1` (PowerShell: `$env:LLMEVAL_PROVIDER="mock"`). Mock answers are meaningless - it only proves the code runs.

Low on RAM (8 GB)? Use the 3B model as the judge too - see [SETUP.md](SETUP.md#hardware).

## How each phase works

Every phase folder has the same shape:

```
phases/04_hallucination/
  README.md                      <- read first: concepts, exercises, how to read results, challenges
  01_fabrication_probe.py        <- runnable exercises, in order
  02_grounded_faithfulness.py
  data/*.jsonl                   <- the test cases (edit them! add your own!)
```

And every exercise prints the same four things:

1. **A banner** - what is being tested and which models are in play
2. **Results** - per case, with PASS/FAIL and the reason
3. **A pass rate with a 95% confidence interval** - so you don't over-trust 10 test cases
4. **"What this means"** - how to interpret the result, what typically goes wrong, what to try next

Results are saved to `results/<exercise>_<time>.json` and `.csv`. Open the CSV in Excel or Google Sheets and **read the actual model outputs** - that habit matters more than any metric.

## The repo at a glance

```
config.yaml            <- the ONLY file you edit to change model/provider
lab.py                 <- course launcher: list, run, next
llmeval/               <- small shared toolkit (read it - ~1,000 commented lines)
  client.py            <- talks to Ollama / OpenAI-compatible APIs / mock
  checks.py            <- deterministic checks (contains, regex, JSON schema, ...)
  judge.py             <- LLM-as-judge helpers (score, pairwise, yes/no)
  report.py            <- tables, confidence intervals, saved results
prompts/               <- every prompt the lab uses, as plain text files
phases/                <- the course
docs/                  <- concepts, reading results, providers, troubleshooting, glossary
results/               <- your run outputs (git-ignored)
```

## Changing models and providers

Edit `config.yaml`. There are three roles - `target` (model under test), `judge` (grader) and `embeddings` (RAG search). Try swapping the target to `qwen3:4b` or `gemma3:4b` and re-running a phase: comparing models on *your* test cases is one of the most useful things this lab teaches.

To use a hosted API (OpenAI, Groq, OpenRouter, ...) or another local server (LM Studio, vLLM), set `provider: openai_compatible` - see [docs/providers.md](docs/providers.md). API keys are read from environment variables, never from the config file.

## Suggested pace

| Session | Phases | Time |
|---|---|---|
| 1 | 0, 1, 2 | ~1.5 h |
| 2 | 3, 4 | ~1.5 h |
| 3 | 5 | ~1 h |
| 4 | 6, 7, 8 | ~2 h |

Small local models are slow on CPU. Judge-heavy exercises (4.2, 6.2) can take several minutes - that's normal.

## Where to go next

- [docs/concepts.md](docs/concepts.md) - how classic QA ideas map onto LLM testing
- [docs/reading_results.md](docs/reading_results.md) - interpreting pass rates, CIs, ASR, faithfulness and agent scores
- [docs/extending.md](docs/extending.md) - add your own test cases, checks and phases
- [docs/troubleshooting.md](docs/troubleshooting.md) - when something doesn't run
- [docs/glossary.md](docs/glossary.md) - every term used in the lab

When you outgrow this lab, the ideas carry straight over to open-source eval frameworks such as promptfoo, DeepEval, Ragas and Inspect - you'll recognise every concept.
