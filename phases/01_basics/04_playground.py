"""Phase 1.4 - Exploratory testing playground.

Run:  python phases/01_basics/04_playground.py                 (all categories)
      python phases/01_basics/04_playground.py hallucination_bait

Lesson: before writing automated evals, do what good testers always do -
explore. Prompts live in prompts/sample_prompts.yaml; add your own.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import get_client, report
from llmeval.prompts import load_prompt_set

prompt_set = load_prompt_set()
wanted = sys.argv[1:] or list(prompt_set)
unknown = [w for w in wanted if w not in prompt_set]
if unknown:
    sys.exit(f"Unknown category {unknown}. Choose from: {list(prompt_set)}")

report.banner("Phase 1.4 - Playground", "Run hand-picked prompts that expose different behaviours. "
              "Read each answer next to the 'watch for' note and decide yourself: pass or fail?")
llm = get_client("target")
rows = []
for category in wanted:
    report.section(category)
    for item in prompt_set[category]:
        res = llm.chat([{"role": "user", "content": item["prompt"]}])
        print(report.bold("PROMPT : ") + item["prompt"])
        print(report.dim("WATCH  : " + item["watch_for"]))
        print("ANSWER : " + res.text.strip().replace("\n", "\n         "))
        print(report.dim("         " + res.usage_line()))
        print()
        rows.append({"category": category, "prompt": item["prompt"], "answer": res.text,
                     "your_verdict": ""})

report.save_results("p1_playground", rows)
report.explain(
    "Open the saved CSV and fill in the 'your_verdict' column. Congratulations: you just created "
    "human labels - the ground truth that Phase 3 uses to check whether an LLM judge can be trusted.",
    "Every surprising answer you found is a candidate test case. Real eval suites are built "
    "exactly like this: explore, find failures, turn each failure into a repeatable check.",
)
