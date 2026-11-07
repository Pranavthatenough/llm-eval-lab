# Providers: local, hosted and mock

All model access goes through `llmeval/client.py`, configured per role in `config.yaml`. Three providers are built in.

## `ollama` (default)

Uses Ollama's native API on `http://localhost:11434`:

| Purpose | Endpoint |
|---|---|
| chat | `POST /api/chat` with `stream: false` |
| structured output | same call with `format` set to a JSON schema (or `"json"`) |
| embeddings | `POST /api/embed` |
| list models | `GET /api/tags` |

Settings sent as `options`: `temperature`, `seed`, `num_ctx` (context window) and `num_predict` (max tokens).

> **Context window gotcha.** Ollama defaults to a fairly small context window regardless of what the model supports, and silently truncates longer prompts. The lab sets `num_ctx: 8192` in `config.yaml`. If RAG answers ignore context, check this first.

Running Ollama on another machine? Point `base_url` at it, e.g. `http://192.168.1.50:11434` (that machine must allow remote connections - see Ollama's docs for `OLLAMA_HOST`).

## `openai_compatible` (hosted APIs and other local servers)

Many services expose the OpenAI-style `/v1/chat/completions` API. The client uses `response_format` for structured output and `/v1/embeddings` for embeddings.

```yaml
target:
  provider: openai_compatible
  model: gpt-4o-mini                  # whatever model name the service uses
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY         # the NAME of an env var, never the key itself
  temperature: 0.0
  seed: 42
```

Then set the key in your shell (`export OPENAI_API_KEY=...`; PowerShell: `$env:OPENAI_API_KEY="..."`) or in a `.env` file at the repo root (see `.env.example`; it's git-ignored).

Typical `base_url` values - check each provider's current docs, as these change:

| Service | base_url |
|---|---|
| OpenAI | `https://api.openai.com/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| LM Studio (local) | `http://localhost:1234/v1` |
| vLLM (local) | `http://localhost:8000/v1` |
| Ollama's own OpenAI-compatible layer | `http://localhost:11434/v1` (no key needed) |

Not every service supports every feature (seed, JSON-schema output, embeddings). If one fails, the error message includes the server's reply.

**Mixing providers is useful:** e.g. a local `llama3.2:3b` as target with a stronger hosted model as judge. Phase 3 will tell you whether the stronger judge agrees with humans more.

**Cost tip:** Phases 4.2 and 6.2 make several judge calls per case. With a paid judge, run them on a subset first.

## `mock`

An offline fake. It returns echo-style text, schema-shaped dummy JSON, and hashed bag-of-words embeddings. Use it to verify installation and to develop new exercises without waiting on a model:

```bash
LLMEVAL_PROVIDER=mock python lab.py run 2
```

Mock results are meaningless as quality measurements; every banner warns you when mock is active.

## Adding another provider

Add a `_yourprovider_chat()` method to `LLMClient` that returns a `ChatResult`, and route to it in `chat()`. Everything else in the lab - checks, judges, reports - works unchanged, because it only ever sees `ChatResult.text`.
