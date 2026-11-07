"""LLM-as-a-judge helpers (taught in Phase 3, reused in Phases 4-7).

A judge is just another model call with:
  1. a clear rubric (what does a 1 vs a 5 look like?)
  2. a structured output (JSON with reasoning FIRST, then the score)
  3. temperature 0, so the same input gets the same grade as often as possible

The prompt templates live in /prompts so you can read and edit them.
Treat the judge as a measuring instrument that must itself be tested -
that's exactly what Phase 3 does.
"""
from __future__ import annotations

from dataclasses import dataclass

from .client import LLMClient, get_client
from .prompts import load_prompt, render

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "score": {"type": "integer", "minimum": 1, "maximum": 5},
    },
    "required": ["reasoning", "score"],
}

PAIRWISE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "winner": {"type": "string", "enum": ["A", "B", "tie"]},
    },
    "required": ["reasoning", "winner"],
}

BINARY_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "verdict": {"type": "string", "enum": ["yes", "no"]},
    },
    "required": ["reasoning", "verdict"],
}


@dataclass
class Verdict:
    score: int | None          # 1-5 for score judges, 1/0 for binary judges, None if unparseable
    reasoning: str
    parse_ok: bool
    raw: str = ""

    @property
    def passed(self) -> bool:
        return self.score is not None and self.score >= 4


def _judge() -> LLMClient:
    return get_client("judge")


def judge_score(
    question: str,
    answer: str,
    criteria: str,
    reference: str | None = None,
    client: LLMClient | None = None,
    **chat_kwargs,
) -> Verdict:
    """Grade one answer from 1 (bad) to 5 (excellent) against the criteria."""
    ref_block = (
        f"A reference answer written by an expert:\n<reference>\n{reference}\n</reference>\n"
        if reference
        else "No reference answer is available; use your own knowledge carefully.\n"
    )
    prompt = render(
        load_prompt("judge_score"),
        criteria=criteria, question=question, answer=answer, reference_block=ref_block,
    )
    data, res = (client or _judge()).ask_json(prompt, schema=SCORE_SCHEMA, **chat_kwargs)
    if not isinstance(data, dict) or not isinstance(data.get("score"), int):
        return Verdict(None, "judge output could not be parsed", False, res.text)
    score = max(1, min(5, data["score"]))
    return Verdict(score, str(data.get("reasoning", "")), True, res.text)


def judge_pairwise(
    question: str, answer_a: str, answer_b: str, criteria: str, client: LLMClient | None = None
) -> tuple[str | None, str]:
    """Which answer is better? Returns (winner 'A'|'B'|'tie'|None, reasoning)."""
    prompt = render(
        load_prompt("judge_pairwise"),
        criteria=criteria, question=question, answer_a=answer_a, answer_b=answer_b,
    )
    data, _ = (client or _judge()).ask_json(prompt, schema=PAIRWISE_SCHEMA)
    if not isinstance(data, dict) or data.get("winner") not in ("A", "B", "tie"):
        return None, "unparseable"
    return data["winner"], str(data.get("reasoning", ""))


def judge_binary(question_for_judge: str, client: LLMClient | None = None, **chat_kwargs) -> Verdict:
    """Ask the judge a yes/no question about some content. score=1 for yes, 0 for no."""
    prompt = render(load_prompt("judge_binary"), question=question_for_judge)
    data, res = (client or _judge()).ask_json(prompt, schema=BINARY_SCHEMA, **chat_kwargs)
    if not isinstance(data, dict) or data.get("verdict") not in ("yes", "no"):
        return Verdict(None, "judge output could not be parsed", False, res.text)
    return Verdict(1 if data["verdict"] == "yes" else 0, str(data.get("reasoning", "")), True, res.text)
