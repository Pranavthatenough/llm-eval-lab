# Phase 0 - Setup

**Goal:** make sure Python, Ollama, the three models and the config all work before you start.

```bash
python phases/00_setup/check_setup.py
```

Full install instructions are in [SETUP.md](../../SETUP.md).

## What the check does

| Check | Why it matters |
|---|---|
| Python 3.10+ and packages | the scripts use modern Python syntax |
| `config.yaml` loads | every script reads models and providers from it |
| Provider reachable | Ollama must be running on `base_url` |
| Model downloaded | Ollama only runs models you've pulled |
| One chat call per role | proves target and judge both answer |
| One embedding call | needed for Phase 6 (optional - keyword retrieval works without it) |

## Things worth knowing before Phase 1

- **The three roles.** `target` is the system under test. `judge` grades answers. `embeddings` powers search in RAG. They're configured separately in `config.yaml` because in real projects they usually are different models.
- **The mock provider** (`LLMEVAL_PROVIDER=mock`) is for plumbing checks only. Never read meaning into mock results.
- **Cold starts.** The first call to each model loads it into memory and can take 10-60 seconds on CPU. Later calls are much faster.
