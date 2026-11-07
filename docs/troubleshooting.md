# Troubleshooting

Start with `python phases/00_setup/check_setup.py` - it diagnoses most problems and prints the fix.

| Symptom | Likely cause | Fix |
|---|---|---|
| `Could not reach Ollama at http://localhost:11434` | Ollama isn't running | Open the Ollama app, or run `ollama serve` in a separate terminal |
| `Ollama does not have model 'x'` | model not pulled, or name typo | `ollama pull x`; check `ollama list` for the exact name/tag |
| `Timed out after 180s` | first call loads the model; CPU is slow | rerun; raise `timeout_s` in `config.yaml`; use a smaller model |
| Very slow everything | running on CPU, or model too big for RAM | use `llama3.2:3b` for both target and judge; close other apps; check `ollama ps` |
| `ModuleNotFoundError: yaml` / `requests` | venv not active or deps not installed | activate `.venv`, then `pip install -r requirements.txt` |
| `judge output could not be parsed` | small judge produced invalid JSON | use a larger judge model; confirm your Ollama version supports structured outputs (update Ollama) |
| RAG answers ignore the context | context truncated | raise `num_ctx` in `config.yaml` |
| Phase 6 embedding errors | `nomic-embed-text` not pulled | `ollama pull nomic-embed-text`, or set `rag.retriever: keyword` |
| Every case passes instantly with `[MOCK]` text | `LLMEVAL_PROVIDER=mock` still set | `unset LLMEVAL_PROVIDER` (PowerShell: `Remove-Item Env:LLMEVAL_PROVIDER`) or open a new terminal |
| Garbled colours on Windows | old console | set `NO_COLOR=1` |
| `Authentication failed (401)` | hosted API key missing/wrong | check the env var named in `api_key_env` |
| `Rate limited (429)` | hosted API quota | slow down, use fewer repeats, or a local model |

## Useful Ollama commands

```bash
ollama list            # downloaded models
ollama ps              # models currently loaded in memory (and CPU vs GPU)
ollama pull <model>    # download / update a model
ollama rm <model>      # free disk space
ollama run <model>     # interactive chat, handy for quick manual checks
```

## Still stuck?

Run the failing script, copy the full error, and check:
1. Which role failed (target, judge, embeddings) - the error message names it.
2. Whether `curl http://localhost:11434/api/tags` returns JSON.
3. Whether the same model works in `ollama run <model>`.
