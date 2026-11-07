"""Load prompt templates from the /prompts folder.

Templates use {{name}} placeholders (double braces) so that JSON examples with
single braces inside a prompt don't break formatting.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from .config import REPO_ROOT

PROMPTS_DIR = REPO_ROOT / "prompts"


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.suffix:
        path = path.with_suffix(".txt")
    return path.read_text(encoding="utf-8").strip()


def render(template: str, **values: object) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise KeyError(f"Template needs a value for {{{{{key}}}}}")
        return str(values[key])

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", sub, template)


def load_prompt_set(name: str = "sample_prompts.yaml") -> dict:
    return yaml.safe_load((PROMPTS_DIR / name).read_text(encoding="utf-8"))


def prompt_path(name: str) -> Path:
    return PROMPTS_DIR / name
