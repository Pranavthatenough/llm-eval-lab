"""Console output + saved reports, kept deliberately simple.

Every exercise:
  * prints a banner saying WHAT it tests and WHICH models are in play
  * prints a results table
  * prints a pass rate WITH a confidence interval (small samples lie!)
  * prints a "What this means" section
  * saves results/<exercise>_<timestamp>.json and .csv (open the CSV in Excel/Sheets)
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .config import load_config

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
WIDTH = 92


def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _COLOR else s


def green(s: str) -> str: return _c("32", s)
def red(s: str) -> str: return _c("31", s)
def yellow(s: str) -> str: return _c("33", s)
def bold(s: str) -> str: return _c("1", s)
def dim(s: str) -> str: return _c("2", s)


def mark(passed: bool | None) -> str:
    if passed is None:
        return yellow("ERR ")
    return green("PASS") if passed else red("FAIL")


def banner(title: str, goal: str, roles: Iterable[str] = ("target",)) -> None:
    cfg = load_config()
    print()
    print(bold("=" * WIDTH))
    print(bold(f" {title}"))
    print("=" * WIDTH)
    for line in textwrap.wrap(goal, WIDTH - 2):
        print(f" {line}")
    print(dim(" " + " | ".join(cfg.role(r).describe() for r in roles)))
    if any(cfg.role(r).provider == "mock" for r in roles):
        print(yellow(" NOTE: mock provider - results only prove the code runs, not model quality."))
    print("-" * WIDTH)


def section(title: str) -> None:
    print()
    print(bold(f"--- {title} " + "-" * max(0, WIDTH - len(title) - 5)))


def shorten(value: Any, width: int) -> str:
    s = " ".join(str(value).split())
    return s if len(s) <= width else s[: width - 3] + "..."


def print_table(rows: list[dict], columns: list[tuple[str, str, int]]) -> None:
    """columns = [(key, header, width), ...]. Booleans render as PASS/FAIL."""
    head = "  ".join(h.ljust(w) for _, h, w in columns)
    print(bold(head))
    print(dim("-" * len(head)))
    for row in rows:
        cells = []
        for key, _, w in columns:
            v = row.get(key, "")
            if isinstance(v, bool) or (v is None and key in ("passed",)):
                txt = mark(v)
                cells.append(txt + " " * max(0, w - 4))
            else:
                if isinstance(v, float):
                    v = f"{v:.2f}"
                cells.append(shorten(v, w).ljust(w))
        print("  ".join(cells))


def wilson_interval(passes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a pass rate. With 10 cases, 70% really means 'somewhere
    between ~40% and ~89%'. This is the single most important number for not fooling yourself."""
    if n == 0:
        return (0.0, 0.0)
    p = passes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate_line(label: str, passes: int, n: int) -> str:
    if n == 0:
        return f"{label}: n/a (0 cases)"
    lo, hi = wilson_interval(passes, n)
    pct = passes / n * 100
    colour = green if pct >= 80 else yellow if pct >= 50 else red
    return f"{label}: {colour(f'{passes}/{n} = {pct:.0f}%')}  {dim(f'(95% CI {lo*100:.0f}%-{hi*100:.0f}%)')}"


def explain(*paragraphs: str) -> None:
    section("What this means")
    for p in paragraphs:
        for line in textwrap.wrap(p, WIDTH - 4):
            print(f"  {line}")
        print()


def save_results(name: str, rows: list[dict], summary: dict | None = None) -> Path:
    cfg = load_config()
    out_dir = cfg.results_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = out_dir / f"{name}_{stamp}"
    meta = {
        "exercise": name,
        "timestamp": stamp,
        "models": {r: cfg.role(r).describe() for r in ("target", "judge", "embeddings")},
        "summary": summary or {},
    }
    with open(f"{base}.json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "rows": rows}, f, indent=2, default=str)
    if rows:
        keys: list[str] = []
        for r in rows:
            keys.extend(k for k in r if k not in keys)
        with open(f"{base}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})
    print(dim(f"\n  Saved: {base}.json (+ .csv)"))
    return Path(f"{base}.json")
