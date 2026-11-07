"""A small, readable client for talking to a model.

Why write our own instead of using a big framework? Because as a tester you
should be able to see EXACTLY what is sent to the model and what comes back.
Every request goes through `LLMClient.chat()` - one function, ~3 providers.

Typical use:

    from llmeval import get_client
    llm = get_client("target")
    print(llm.ask("What is the capital of France?"))

    data, result = llm.ask_json("Give me a JSON object with a 'city' key", schema={...})
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from .config import ModelConfig, load_config

Message = dict[str, str]  # {"role": "system"|"user"|"assistant", "content": "..."}


class LLMError(RuntimeError):
    """Raised with a beginner-friendly explanation of what went wrong."""


@dataclass
class ChatResult:
    text: str
    model: str
    provider: str
    latency_s: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def usage_line(self) -> str:
        toks = ""
        if self.prompt_tokens is not None or self.completion_tokens is not None:
            toks = f" | tokens in={self.prompt_tokens} out={self.completion_tokens}"
        return f"[{self.provider}:{self.model}] {self.latency_s:.2f}s{toks}"


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_thinking(text: str) -> str:
    """Some 'reasoning' models (e.g. qwen3, deepseek-r1) wrap private reasoning in
    <think>...</think>. We grade the final answer, so remove it."""
    return _THINK_RE.sub("", text or "").strip()


def extract_json(text: str) -> Any | None:
    """Best-effort JSON parsing. Models often wrap JSON in ```json fences or add chatter.
    Returns None if nothing parseable is found - callers must handle that (it IS a failure)."""
    if text is None:
        return None
    text = strip_thinking(text)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = text.find(open_c), text.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


class LLMClient:
    def __init__(self, cfg: ModelConfig):
        self.cfg = cfg
        self.provider = cfg.provider
        if self.provider not in ("ollama", "openai_compatible", "mock"):
            raise LLMError(
                f"Unknown provider '{self.provider}' for role '{cfg.role}'. "
                "Use ollama, openai_compatible or mock in config.yaml."
            )

    # ------------------------------------------------------------------ public API
    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        seed: int | None | str = "config",
        json_schema: dict | None = None,
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> ChatResult:
        """Send a list of messages and return a ChatResult.

        temperature  None -> use config value
        seed         "config" -> use config value; None -> no seed (random each call)
        json_schema  constrain the output to this JSON schema (structured outputs)
        json_mode    ask for 'any valid JSON' without a specific schema
        """
        temp = self.cfg.temperature if temperature is None else temperature
        use_seed = self.cfg.seed if seed == "config" else seed
        start = time.perf_counter()
        if self.provider == "ollama":
            res = self._ollama_chat(messages, temp, use_seed, json_schema, json_mode, max_tokens)
        elif self.provider == "openai_compatible":
            res = self._openai_chat(messages, temp, use_seed, json_schema, json_mode, max_tokens)
        else:
            res = self._mock_chat(messages, temp, use_seed, json_schema, json_mode)
        res.latency_s = time.perf_counter() - start
        res.text = strip_thinking(res.text)
        return res

    def ask(self, prompt: str, *, system: str | None = None, **kwargs) -> str:
        """Simplest possible call: one prompt in, text out."""
        return self.chat(build_messages(prompt, system), **kwargs).text

    def ask_json(
        self, prompt: str, *, schema: dict | None = None, system: str | None = None, **kwargs
    ) -> tuple[Any | None, ChatResult]:
        """Ask for JSON. Returns (parsed_json_or_None, ChatResult)."""
        res = self.chat(
            build_messages(prompt, system), json_schema=schema, json_mode=schema is None, **kwargs
        )
        return extract_json(res.text), res

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "ollama":
            data = self._post(
                f"{self._ollama_base()}/api/embed",
                {"model": self.cfg.model, "input": texts},
            )
            return data["embeddings"]
        if self.provider == "openai_compatible":
            data = self._post(
                f"{self.cfg.base_url.rstrip('/')}/embeddings",
                {"model": self.cfg.model, "input": texts},
                headers=self._auth_headers(),
            )
            return [row["embedding"] for row in sorted(data["data"], key=lambda r: r["index"])]
        return [_mock_embedding(t) for t in texts]

    def list_models(self) -> list[str]:
        """Models available on the server (used by the setup checker)."""
        if self.provider == "ollama":
            r = self._get(f"{self._ollama_base()}/api/tags")
            return [m["name"] for m in r.get("models", [])]
        if self.provider == "openai_compatible":
            r = self._get(f"{self.cfg.base_url.rstrip('/')}/models", headers=self._auth_headers())
            return [m["id"] for m in r.get("data", [])]
        return [self.cfg.model]

    # ------------------------------------------------------------------ providers
    def _ollama_base(self) -> str:
        # Accept either http://localhost:11434 or http://localhost:11434/v1
        return re.sub(r"/v1/?$", "", self.cfg.base_url.rstrip("/"))

    def _ollama_chat(self, messages, temp, seed, schema, json_mode, max_tokens) -> ChatResult:
        options: dict[str, Any] = {"temperature": temp}
        if seed is not None:
            options["seed"] = seed
        if self.cfg.num_ctx:
            options["num_ctx"] = self.cfg.num_ctx
        if max_tokens:
            options["num_predict"] = max_tokens
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if schema is not None:
            payload["format"] = schema  # Ollama structured outputs: pass the JSON schema itself
        elif json_mode:
            payload["format"] = "json"
        data = self._post(f"{self._ollama_base()}/api/chat", payload)
        return ChatResult(
            text=data.get("message", {}).get("content", ""),
            model=data.get("model", self.cfg.model),
            provider="ollama",
            latency_s=0.0,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            raw=data,
        )

    def _openai_chat(self, messages, temp, seed, schema, json_mode, max_tokens) -> ChatResult:
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": temp,
        }
        if seed is not None:
            payload["seed"] = seed
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": schema},
            }
        elif json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self._post(
            f"{self.cfg.base_url.rstrip('/')}/chat/completions", payload, headers=self._auth_headers()
        )
        usage = data.get("usage") or {}
        return ChatResult(
            text=(data["choices"][0]["message"].get("content") or ""),
            model=data.get("model", self.cfg.model),
            provider="openai_compatible",
            latency_s=0.0,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            raw=data,
        )

    def _mock_chat(self, messages, temp, seed, schema, json_mode) -> ChatResult:
        """Offline fake model. Deterministic unless temperature > 0 and seed is None.
        It does NOT understand anything - it only proves the pipeline runs."""
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        salt = "" if (temp == 0 or seed is not None) else str(time.time_ns())
        h = int(hashlib.sha256((last_user + salt).encode()).hexdigest(), 16)
        if schema is not None:
            text = json.dumps(_fake_from_schema(schema, h))
        elif json_mode:
            text = json.dumps({"answer": "mock", "note": "mock provider output"})
        else:
            snippet = " ".join(last_user.split()[:12])
            variants = ["I think", "It seems", "Probably", "My answer is"]
            text = f"[MOCK] {variants[h % len(variants)]}: {snippet}"
        return ChatResult(text=text, model=self.cfg.model, provider="mock", latency_s=0.0)

    # ------------------------------------------------------------------ http helpers
    def _auth_headers(self) -> dict[str, str]:
        key = self.cfg.api_key
        if self.cfg.api_key_env and not key:
            raise LLMError(
                f"Environment variable {self.cfg.api_key_env} is not set "
                f"(needed by role '{self.cfg.role}'). Add it to your shell or a .env file."
            )
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _get(self, url: str, headers: dict | None = None) -> dict:
        try:
            r = requests.get(url, headers=headers, timeout=15)
        except requests.exceptions.ConnectionError as e:
            raise LLMError(self._connection_hint(url)) from e
        self._raise_for_status(r)
        return r.json()

    def _post(self, url: str, payload: dict, headers: dict | None = None) -> dict:
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=self.cfg.timeout_s)
        except requests.exceptions.ConnectionError as e:
            raise LLMError(self._connection_hint(url)) from e
        except requests.exceptions.Timeout as e:
            raise LLMError(
                f"Timed out after {self.cfg.timeout_s}s calling {url}. The first call to a model "
                "loads it into memory and can be slow - try again, or raise timeout_s in config.yaml."
            ) from e
        self._raise_for_status(r)
        return r.json()

    def _connection_hint(self, url: str) -> str:
        if self.provider == "ollama":
            return (
                f"Could not reach Ollama at {url}.\n"
                "  -> Is Ollama running? Open the Ollama app, or run `ollama serve` in a terminal.\n"
                "  -> Check base_url in config.yaml (default http://localhost:11434).\n"
                "  -> No Ollama yet? Try the plumbing with: LLMEVAL_PROVIDER=mock"
            )
        return f"Could not connect to {url}. Check base_url in config.yaml and your network."

    def _raise_for_status(self, r: requests.Response) -> None:
        if r.ok:
            return
        body = r.text[:400]
        if self.provider == "ollama" and r.status_code == 404 and "not found" in body.lower():
            raise LLMError(
                f"Ollama does not have model '{self.cfg.model}' (role: {self.cfg.role}).\n"
                f"  -> Run: ollama pull {self.cfg.model}"
            )
        if r.status_code in (401, 403):
            raise LLMError(f"Authentication failed ({r.status_code}). Check your API key. Body: {body}")
        if r.status_code == 429:
            raise LLMError("Rate limited (429). Slow down or check your plan/quota.")
        raise LLMError(f"HTTP {r.status_code} from {r.url}: {body}")


# ---------------------------------------------------------------------- helpers
def build_messages(prompt: str, system: str | None = None) -> list[Message]:
    msgs: list[Message] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return msgs


_CLIENTS: dict[str, LLMClient] = {}


def get_client(role: str = "target") -> LLMClient:
    """Get a client for 'target', 'judge' or 'embeddings' using config.yaml."""
    if role not in _CLIENTS:
        _CLIENTS[role] = LLMClient(load_config().role(role))
    return _CLIENTS[role]


def _fake_from_schema(schema: dict, h: int, depth: int = 0) -> Any:
    """Build a minimal object that satisfies a JSON schema (for the mock provider)."""
    if depth > 6:
        return None
    if "enum" in schema:
        return schema["enum"][h % len(schema["enum"])]
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    if t == "object" or "properties" in schema:
        return {
            k: _fake_from_schema(v, h >> (i + 1), depth + 1)
            for i, (k, v) in enumerate(schema.get("properties", {}).items())
        }
    if t == "array":
        return [_fake_from_schema(schema.get("items", {"type": "string"}), h, depth + 1)]
    if t == "integer":
        lo, hi = schema.get("minimum", 0), schema.get("maximum", 5)
        return lo + h % (hi - lo + 1)
    if t == "number":
        return float(schema.get("minimum", 0))
    if t == "boolean":
        return bool(h % 2)
    return "mock"


def _mock_embedding(text: str, dims: int = 256) -> list[float]:
    """Hashed bag-of-words vector: crude, but similar texts get similar vectors."""
    vec = [0.0] * dims
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % dims] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
