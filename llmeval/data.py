"""Tiny helpers for loading test datasets (JSONL = one JSON object per line)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{n} is not valid JSON: {e}") from e
    return rows


def here(file: str) -> Path:
    """Folder of the calling script: data paths work no matter where you run from."""
    return Path(file).resolve().parent
