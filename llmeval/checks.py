"""Deterministic checks: plain code that inspects model output. No model involved.

These are the LLM-world equivalent of classic assertions. They are fast, free,
repeatable and explainable - use them for everything they CAN catch, and only
reach for an LLM judge for what they can't.

Every check returns a CheckResult(name, passed, detail) so reports stay uniform.
Checks are also usable from data files: {"type": "contains_all", "values": [...]}
"""
from __future__ import annotations

import json
import re
import string
from dataclasses import dataclass
from typing import Any, Callable

from .client import extract_json


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

    def __str__(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"{mark} {self.name}" + (f" - {self.detail}" if self.detail else "")


# ------------------------------------------------------------------ normalisation
def normalize(text: str) -> str:
    """Lowercase, drop punctuation and extra whitespace. 'Paris.' == 'paris'."""
    text = (text or "").lower().strip()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


# ------------------------------------------------------------------ text checks
def exact_match(output: str, expected: str) -> CheckResult:
    ok = output.strip() == expected.strip()
    return CheckResult("exact_match", ok, f"expected {expected!r}, got {output.strip()[:60]!r}")


def normalized_match(output: str, expected: str) -> CheckResult:
    ok = normalize(output) == normalize(expected)
    return CheckResult("normalized_match", ok, f"expected {expected!r}")


def contains_all(output: str, values: list[str], case_sensitive: bool = False) -> CheckResult:
    hay = output if case_sensitive else output.lower()
    missing = [v for v in values if (v if case_sensitive else v.lower()) not in hay]
    return CheckResult("contains_all", not missing, f"missing: {missing}" if missing else "")


def contains_any(output: str, values: list[str]) -> CheckResult:
    hay = output.lower()
    hit = [v for v in values if v.lower() in hay]
    return CheckResult("contains_any", bool(hit), f"found: {hit}" if hit else f"none of {values}")


def contains_none(output: str, values: list[str]) -> CheckResult:
    hay = output.lower()
    found = [v for v in values if v.lower() in hay]
    return CheckResult("contains_none", not found, f"forbidden text present: {found}" if found else "")


def regex_match(output: str, pattern: str) -> CheckResult:
    ok = re.search(pattern, output, re.IGNORECASE | re.MULTILINE) is not None
    return CheckResult("regex_match", ok, f"pattern {pattern!r}")


def max_words(output: str, value: int) -> CheckResult:
    n = len(output.split())
    return CheckResult("max_words", n <= value, f"{n} words (limit {value})")


def min_words(output: str, value: int) -> CheckResult:
    n = len(output.split())
    return CheckResult("min_words", n >= value, f"{n} words (minimum {value})")


def numeric_close(output: str, expected: float, tolerance: float = 0.01) -> CheckResult:
    """Find numbers in the output; pass if ANY is within tolerance of expected."""
    nums = [float(n.replace(",", "")) for n in re.findall(r"-?\d[\d,]*\.?\d*", output)]
    ok = any(abs(n - expected) <= tolerance for n in nums)
    return CheckResult("numeric_close", ok, f"expected {expected}, found {nums[:5]}")


REFUSAL_MARKERS = [
    "i can't", "i cannot", "i can not", "i'm not able", "i am not able", "i won't",
    "i'm unable", "i am unable", "i don't have", "i do not have", "not able to provide",
    "i'm sorry", "i am sorry", "as an ai", "i don't know", "i do not know", "no information",
    "not aware of", "couldn't find", "could not find", "doesn't exist", "does not exist",
    "no record", "not familiar", "unable to find", "there is no", "i'm not sure", "not sure",
]


def is_refusal(output: str) -> CheckResult:
    """Heuristic: does the output decline / admit not knowing? Cheap, but leaky -
    Phase 4 shows when you need a judge instead."""
    low = output.lower()
    hits = [m for m in REFUSAL_MARKERS if m in low]
    return CheckResult("is_refusal", bool(hits), f"markers: {hits[:3]}" if hits else "no refusal markers")


def not_refusal(output: str) -> CheckResult:
    r = is_refusal(output)
    return CheckResult("not_refusal", not r.passed, r.detail)


# ------------------------------------------------------------------ JSON checks
def is_valid_json(output: str) -> CheckResult:
    try:
        json.loads(output)
        return CheckResult("is_valid_json", True, "strict parse ok")
    except (json.JSONDecodeError, TypeError):
        lenient = extract_json(output)
        if lenient is not None:
            return CheckResult("is_valid_json", False, "only parseable after stripping extra text")
        return CheckResult("is_valid_json", False, "not JSON")


def json_schema(output: str | Any, schema: dict) -> CheckResult:
    """Validate against a SUBSET of JSON Schema: type, required, properties, enum, items,
    minimum/maximum. Enough for learning; use the `jsonschema` package in real projects."""
    data = extract_json(output) if isinstance(output, str) else output
    if data is None:
        return CheckResult("json_schema", False, "could not parse JSON")
    errors = _validate(data, schema, "$")
    return CheckResult("json_schema", not errors, "; ".join(errors[:3]))


_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "integer": int, "number": (int, float), "null": type(None),
}


def _validate(data: Any, schema: dict, path: str) -> list[str]:
    errs: list[str] = []
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        ok = any(
            isinstance(data, _TYPES[x]) and not (x in ("integer", "number") and isinstance(data, bool))
            for x in types
        )
        if not ok:
            return [f"{path}: expected {t}, got {type(data).__name__}"]
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{path}: {data!r} not in {schema['enum']}")
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errs.append(f"{path}: {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errs.append(f"{path}: {data} > maximum {schema['maximum']}")
    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errs.append(f"{path}: missing required key '{key}'")
        for key, sub in schema.get("properties", {}).items():
            if key in data:
                errs.extend(_validate(data[key], sub, f"{path}.{key}"))
    if isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            errs.extend(_validate(item, schema["items"], f"{path}[{i}]"))
    return errs


# ------------------------------------------------------------------ data-driven runner
CHECKS: dict[str, Callable[..., CheckResult]] = {
    "exact_match": lambda out, c: exact_match(out, c["value"]),
    "normalized_match": lambda out, c: normalized_match(out, c["value"]),
    "contains_all": lambda out, c: contains_all(out, c["values"], c.get("case_sensitive", False)),
    "contains_any": lambda out, c: contains_any(out, c["values"]),
    "contains_none": lambda out, c: contains_none(out, c["values"]),
    "regex": lambda out, c: regex_match(out, c["pattern"]),
    "max_words": lambda out, c: max_words(out, c["value"]),
    "min_words": lambda out, c: min_words(out, c["value"]),
    "numeric_close": lambda out, c: numeric_close(out, c["value"], c.get("tolerance", 0.01)),
    "is_refusal": lambda out, c: is_refusal(out),
    "not_refusal": lambda out, c: not_refusal(out),
    "is_valid_json": lambda out, c: is_valid_json(out),
    "json_schema": lambda out, c: json_schema(out, c["schema"]),
}


def run_check(output: str, spec: dict) -> CheckResult:
    kind = spec["type"]
    if kind not in CHECKS:
        raise ValueError(f"Unknown check type '{kind}'. Known: {sorted(CHECKS)}")
    result = CHECKS[kind](output, spec)
    if spec.get("label"):
        result.name = f"{result.name}[{spec['label']}]"
    return result
