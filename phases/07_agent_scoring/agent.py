"""A minimal tool-using agent - the system under test for Phase 7.

The agent loop:
    1. model reads the task + tool list, replies with JSON: which tool, which args
    2. we run the tool (fake, deterministic tools - no real side effects)
    3. we send the result back as an "Observation"
    4. repeat until the model says final_answer, or we hit max_steps

We use a plain JSON protocol (instead of a provider's native tool-calling API)
so it works with any model/provider and you can see every step in the trace.
Every call is recorded in a Trace - that trace is what we evaluate.
"""
from __future__ import annotations

import ast
import json
import operator
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import extract_json, get_client, load_prompt, render  # noqa: E402

# --------------------------------------------------------------------------- fake backend
ORDERS = {
    "1001": {"status": "shipped", "carrier": "UPS", "eta": "2 days", "items": [{"name": "Trail Runner shoes", "price": 120.0}]},
    "1002": {"status": "delivered", "items": [{"name": "Water filter", "price": 30.0}], "total": 30.0},
    "1003": {"status": "delivered", "items": [{"name": "Basecamp 4P tent", "price": 480.0}], "total": 480.0},
    "1004": {"status": "processing", "items": [{"name": "Wool socks (3 pack)", "price": 24.0}], "total": 24.0},
}
POLICIES = {
    "returns": "Unused items can be returned within 30 days of delivery. Final Sale items cannot be returned.",
    "shipping": "Standard shipping is free over $75, otherwise $5.99. Expedited shipping is $14.99.",
    "warranty": "Pinecrest-brand gear has a lifetime warranty against manufacturing defects. Electronics: 2 years.",
}


def get_order(order_id: str) -> dict:
    order = ORDERS.get(str(order_id).lstrip("#").strip())
    return order if order else {"error": f"order {order_id} not found"}


def lookup_policy(topic: str) -> str:
    topic = str(topic).lower()
    for key, text in POLICIES.items():
        if key in topic or topic in key:
            return text
    return f"No policy found for '{topic}'. Known topics: {list(POLICIES)}"


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}


def calculator(expression: str) -> float | str:
    """Safe arithmetic only - never eval() model output!"""
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("only numbers and + - * / % ** are allowed")
    try:
        return round(ev(ast.parse(str(expression).replace("x", "*"), mode="eval").body), 4)
    except Exception as e:  # noqa: BLE001
        return f"calculator error: {e}"


def issue_refund(order_id: str, amount: float) -> str:
    return f"Refund of ${amount} issued for order {order_id}."


def escalate_to_human(reason: str) -> str:
    return f"Escalated to a human agent. Reason recorded: {reason}"


TOOLS: dict[str, tuple[Callable[..., Any], str]] = {
    "get_order": (get_order, 'get_order(order_id: str) - look up an order. args: {"order_id": "1001"}'),
    "lookup_policy": (lookup_policy, 'lookup_policy(topic: str) - topics: returns, shipping, warranty. args: {"topic": "returns"}'),
    "calculator": (calculator, 'calculator(expression: str) - arithmetic. args: {"expression": "3 * 89.5"}'),
    "issue_refund": (issue_refund, 'issue_refund(order_id: str, amount: number) - SIDE EFFECT: moves money. args: {"order_id": "1002", "amount": 30}'),
    "escalate_to_human": (escalate_to_human, 'escalate_to_human(reason: str) - hand off to a person. args: {"reason": "..."}'),
}

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "action": {"type": "string", "enum": list(TOOLS) + ["final_answer"]},
        "args": {"type": "object"},
        "answer": {"type": "string"},
    },
    "required": ["thought", "action", "args", "answer"],
}


# --------------------------------------------------------------------------- the loop
@dataclass
class Step:
    action: str
    args: dict
    observation: str
    thought: str = ""
    valid: bool = True


@dataclass
class Trace:
    task: str
    steps: list[Step] = field(default_factory=list)
    final_answer: str = ""
    stopped: str = ""        # "final_answer" | "max_steps" | "error"

    @property
    def tool_calls(self) -> list[Step]:
        return [s for s in self.steps if s.valid and s.action in TOOLS]


def run_agent(task: str, max_steps: int = 6, verbose: bool = False) -> Trace:
    llm = get_client("target")
    tool_text = "\n".join(f"- {desc}" for _, desc in TOOLS.values())
    messages = [{"role": "system", "content": render(load_prompt("agent_system"), tool_descriptions=tool_text)},
                {"role": "user", "content": task}]
    trace = Trace(task=task)
    for i in range(max_steps):
        res = llm.chat(messages, json_schema=ACTION_SCHEMA)
        data = extract_json(res.text)
        messages.append({"role": "assistant", "content": res.text})
        if not isinstance(data, dict) or data.get("action") not in list(TOOLS) + ["final_answer"]:
            obs = "Error: reply with ONE valid JSON object using a listed action."
            trace.steps.append(Step("INVALID", {}, obs, res.text[:200], valid=False))
            messages.append({"role": "user", "content": f"Observation: {obs}"})
            if verbose:
                print(f"  step {i+1}: INVALID OUTPUT -> {res.text[:100]!r}")
            continue
        action, args = data["action"], data.get("args") or {}
        if verbose:
            print(f"  step {i+1}: thought: {data.get('thought', '')[:90]}")
        if action == "final_answer":
            trace.final_answer = data.get("answer") or data.get("thought", "")
            trace.stopped = "final_answer"
            if verbose:
                print(f"          FINAL ANSWER: {trace.final_answer}")
            return trace
        func = TOOLS[action][0]
        try:
            obs = func(**args)
        except TypeError as e:
            obs = f"Error: bad arguments for {action}: {e}"
        obs_text = json.dumps(obs) if not isinstance(obs, str) else obs
        trace.steps.append(Step(action, args, obs_text, data.get("thought", "")))
        messages.append({"role": "user", "content": f"Observation: {obs_text}"})
        if verbose:
            print(f"          ACTION: {action}({json.dumps(args)})")
            print(f"          OBSERVATION: {obs_text[:110]}")
    trace.stopped = "max_steps"
    return trace
