# Setup guide

This takes 10-20 minutes, most of it waiting for model downloads.

## 1. Install Ollama

Ollama runs open models on your own machine and exposes them on `http://localhost:11434`.

**macOS**
- Download the app from https://ollama.com/download, open it and drag it to Applications, then launch it (a llama icon appears in the menu bar).
- Or with Homebrew: `brew install ollama`, then start it with `brew services start ollama` (or run `ollama serve` in a terminal you keep open).

**Windows**
- Download and run the installer from https://ollama.com/download. It runs natively (no WSL needed) and starts in the background with a tray icon.
- Or from PowerShell: `winget install Ollama.Ollama`

**Linux**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```
The script sets Ollama up as a background service. If it isn't running, start it with `ollama serve`.

**Check it works**
```bash
ollama --version
curl http://localhost:11434/api/tags     # should return JSON listing your models
```

## 2. Download the models

```bash
ollama pull llama3.2:3b        # target - the model you test       (~2.0 GB)
ollama pull llama3.1:8b        # judge  - grades answers            (~4.9 GB)
ollama pull nomic-embed-text   # embeddings - for RAG retrieval     (~0.3 GB)
```

Quick sanity check: `ollama run llama3.2:3b "Say hello"`. Type `/bye` to exit the chat.

### Why these models?
- **llama3.2:3b** is small and fast, and small models fail in interesting, visible ways - perfect for learning to catch failures.
- **llama3.1:8b** as judge: a judge should be *at least as capable* as the model it grades, and ideally a different model (a model grading itself tends to be lenient).
- **nomic-embed-text** is a small, widely used embedding model for search.

The model library changes quickly. Browse https://ollama.com/library for newer options - for example `qwen3:4b`, `gemma3:4b` or newer generations as targets. Change them in `config.yaml`; nothing else needs editing.

> Reasoning models (e.g. qwen3, deepseek-r1) emit `<think>...</think>` text before answering. The lab's client strips it automatically so checks only see the final answer.

### Hardware

| Your machine | Suggested setup |
|---|---|
| 8 GB RAM, no GPU | target `llama3.2:3b`, judge `llama3.2:3b` too (expect slower runs, weaker judging - which is itself a lesson for Phase 3) |
| 16 GB RAM or Apple Silicon | the defaults |
| GPU with 12 GB+ VRAM | try a bigger judge, e.g. a 12-14B model, and compare judge agreement in Phase 3 |

Ollama loads a model on first use, so the first call of every exercise is slow. That's normal.

## 3. Set up Python

You need Python 3.10 or newer (`python --version`).

```bash
cd llm-eval-lab
python -m venv .venv

# activate it
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows (cmd or PowerShell)

pip install -r requirements.txt
```

Only three packages are installed: `requests`, `PyYAML` and `pytest`. Everything else is standard-library Python, on purpose, so you can read all of it.

## 4. Run the setup check

```bash
python phases/00_setup/check_setup.py
```

It checks Python, packages, config, that Ollama is reachable, that each model is downloaded, and makes one real call per role. Every problem comes with the exact fix command. When you see **All good**, run:

```bash
python lab.py
```

## Optional: run without Ollama (plumbing check)

The `mock` provider is a fake offline model. It lets you confirm Python and the scripts work before installing anything. Its answers are meaningless.

```bash
LLMEVAL_PROVIDER=mock python lab.py run 1.1          # macOS / Linux
$env:LLMEVAL_PROVIDER="mock"; python lab.py run 1.1  # Windows PowerShell
```

Remove the variable (or open a new terminal) to go back to real models.

## Optional: hosted APIs

See [docs/providers.md](docs/providers.md). Short version: set `provider: openai_compatible`, a `base_url`, a `model`, and `api_key_env` naming the environment variable that holds your key.
