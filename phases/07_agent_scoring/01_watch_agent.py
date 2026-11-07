"""Phase 7.1 - Watch an agent think, act and observe.

Run:  python phases/07_agent_scoring/01_watch_agent.py            (task t2)
      python phases/07_agent_scoring/01_watch_agent.py t3
      python phases/07_agent_scoring/01_watch_agent.py "Where is order 1004?"

Lesson: before scoring agents, look at a few traces by hand. An agent is a
loop of decisions; every decision is a place it can go wrong.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent import run_agent  # noqa: E402

from llmeval import here, load_jsonl, report  # noqa: E402

tasks = {t["id"]: t for t in load_jsonl(here(__file__) / "data" / "tasks.jsonl")}
arg = " ".join(sys.argv[1:]) or "t2"
task = tasks[arg]["task"] if arg in tasks else arg

report.banner("Phase 7.1 - Watch the agent", "Run one task and print every step of the trace.")
print(report.bold(f"TASK: {task}\n"))
trace = run_agent(task, verbose=True)
print()
print(f"stopped because: {trace.stopped}  |  steps: {len(trace.steps) + (trace.stopped == 'final_answer')}  "
      f"|  tool calls: {[s.action for s in trace.tool_calls]}")
if arg in tasks:
    t = tasks[arg]
    print(f"expected tools:  {t['expected_tools']}   forbidden: {t['forbidden_tools']}")

report.explain(
    "Questions to ask of every trace: Did it pick the right tool? With the right arguments? Did "
    "it USE the observation, or ignore it and answer from imagination? Did it stop at the right "
    "time? Did it do anything with side effects (issue_refund) it shouldn't have?",
    "Try t3 and t8: both push the agent to refund $480, above its $50 limit. A final answer that "
    "politely says 'I've escalated this' looks perfect - but if the trace shows issue_refund was "
    "called first, real money moved. That's why Phase 7.2 scores the TRAJECTORY, not just the text.",
)
