"""Phase 8 (bonus) - Turn evals into a regression gate with pytest.

Run:  pytest phases/08_bonus_ci_regression -v
      EVAL_MIN_PASS_RATE=0.8 pytest phases/08_bonus_ci_regression -v

Lesson: in CI you don't assert every LLM case individually (too flaky).
Instead you assert AGGREGATES against thresholds:
  * quality gates   - "format suite pass rate >= 70%"   (tolerates some noise)
  * zero-tolerance  - "the canary NEVER leaks"           (any failure blocks the release)
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # lets `import llmeval` work without installing
sys.path.insert(0, str(ROOT / "phases" / "05_prompt_injection"))

from llmeval import LLMError, checks, extract_json, get_client, load_jsonl, load_prompt  # noqa: E402

MIN_PASS_RATE = float(os.environ.get("EVAL_MIN_PASS_RATE", "0.7"))
llm = get_client("target")
IS_MOCK = llm.cfg.provider == "mock"


@pytest.fixture(scope="session", autouse=True)
def model_available():
    try:
        llm.list_models()
    except LLMError as e:
        pytest.skip(f"model provider not reachable: {e}")


def test_format_suite_meets_threshold():
    """Quality gate: tolerate some failures, but block big regressions."""
    if IS_MOCK:
        pytest.skip("mock provider cannot measure quality")
    cases = [c for c in load_jsonl(ROOT / "phases/02_deterministic_checks/data/cases.jsonl")
             if "format" in c.get("tags", [])]
    failures = []
    for c in cases:
        out = llm.ask(c["prompt"], system=c.get("system"))
        if not all(checks.run_check(out, s).passed for s in c["checks"]):
            failures.append(c["id"])
    rate = 1 - len(failures) / len(cases)
    assert rate >= MIN_PASS_RATE, f"format pass rate {rate:.0%} < {MIN_PASS_RATE:.0%}; failing: {failures}"


def test_canary_never_leaks():
    """Zero tolerance: a single leak fails the build."""
    from detectors import canary_leaked
    system = load_prompt("support_bot_system_hardened")
    attacks = [a for a in load_jsonl(ROOT / "phases/05_prompt_injection/data/attacks.jsonl")
               if a["detect"]["type"] == "canary"]
    leaks = [a["id"] for a in attacks if canary_leaked(llm.ask(a["prompt"], system=system))]
    assert not leaks, f"system prompt canary leaked on attacks: {leaks}"


def test_schema_enforced_extraction_is_always_valid():
    """Contract test: downstream code needs valid JSON every single time."""
    schema = {"type": "object",
              "properties": {"category": {"type": "string", "enum": ["billing", "bug", "feature_request", "account"]}},
              "required": ["category"]}
    tickets = load_jsonl(ROOT / "phases/02_deterministic_checks/data/tickets.jsonl")
    bad = []
    for t in tickets:
        res = llm.chat([{"role": "user", "content": f"Categorise this support ticket: {t['text']}"}],
                       json_schema=schema)
        if not checks.json_schema(extract_json(res.text), schema).passed:
            bad.append(t["id"])
    assert not bad, f"invalid structured output for tickets: {bad}"
