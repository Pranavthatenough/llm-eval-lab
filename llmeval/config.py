"""Load config.yaml and apply environment-variable overrides.

Override order (last wins):
    config.yaml  ->  .env file  ->  real environment variables

Useful overrides:
    LLMEVAL_CONFIG=path/to/other.yaml   use a different config file
    LLMEVAL_PROVIDER=mock               force EVERY role onto one provider
    LLMEVAL_TARGET_MODEL=qwen3:4b       change just the target model
    LLMEVAL_JUDGE_MODEL=llama3.1:8b     change just the judge model
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

ROLES = ("target", "judge", "embeddings")


@dataclass
class ModelConfig:
    role: str
    provider: str = "ollama"
    model: str = "llama3.2:3b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.0
    seed: int | None = 42
    num_ctx: int | None = None
    timeout_s: int = 180
    api_key_env: str | None = None

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) if self.api_key_env else None

    def describe(self) -> str:
        return f"{self.role}: {self.provider} / {self.model}"


@dataclass
class LabConfig:
    target: ModelConfig
    judge: ModelConfig
    embeddings: ModelConfig
    rag: dict[str, Any] = field(default_factory=dict)
    run: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None

    def role(self, name: str) -> ModelConfig:
        if name not in ROLES:
            raise ValueError(f"Unknown role '{name}'. Use one of {ROLES}.")
        return getattr(self, name)

    @property
    def results_dir(self) -> Path:
        p = Path(self.run.get("results_dir", "results"))
        return p if p.is_absolute() else REPO_ROOT / p


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader (KEY=VALUE lines). Real env vars always win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _model_config(role: str, raw: dict[str, Any]) -> ModelConfig:
    allowed = ModelConfig.__dataclass_fields__.keys()
    unknown = set(raw) - set(allowed)
    if unknown:
        raise ValueError(f"config.yaml [{role}] has unknown keys: {sorted(unknown)}")
    cfg = ModelConfig(role=role, **{k: v for k, v in raw.items() if k != "role"})

    forced = os.environ.get("LLMEVAL_PROVIDER")
    if forced:
        cfg.provider = forced
    model_override = os.environ.get(f"LLMEVAL_{role.upper()}_MODEL")
    if model_override:
        cfg.model = model_override
    return cfg


_CACHE: LabConfig | None = None


def load_config(path: str | Path | None = None, *, reload: bool = False) -> LabConfig:
    global _CACHE
    if _CACHE is not None and not reload and path is None:
        return _CACHE

    _load_dotenv(REPO_ROOT / ".env")
    cfg_path = Path(path or os.environ.get("LLMEVAL_CONFIG", REPO_ROOT / "config.yaml"))
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    cfg = LabConfig(
        target=_model_config("target", data.get("target", {})),
        judge=_model_config("judge", data.get("judge", {})),
        embeddings=_model_config("embeddings", data.get("embeddings", {})),
        rag=data.get("rag", {}) or {},
        run=data.get("run", {}) or {},
        source=cfg_path,
    )
    if path is None:
        _CACHE = cfg
    return cfg
