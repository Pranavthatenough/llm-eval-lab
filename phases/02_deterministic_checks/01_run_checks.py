"""Phase 2.1 - Data-driven deterministic checks.

Run:  python phases/02_deterministic_checks/01_run_checks.py
      python phases/02_deterministic_checks/01_run_checks.py --tag format

Lesson: you can't assert the exact output, but you CAN assert properties of it:
format, length, required facts, forbidden content, valid JSON. These checks are
plain Python - fast, free, explainable and 100% repeatable.

Test cases live in data/cases.jsonl. Each one has a prompt and a list of checks.
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import checks, get_client, here, load_jsonl, report

ap = argparse.ArgumentParser()
ap.add_argument("--tag", help="only run cases with this tag (e.g. format, safety)")
args = ap.parse_args()

cases = load_jsonl(here(__file__) / "data" / "cases.jsonl")
if args.tag:
    cases = [c for c in cases if args.tag in c.get("tags", [])]

report.banner("Phase 2.1 - Deterministic checks",
              f"Run {len(cases)} cases. A case passes only if ALL of its checks pass.")
llm = get_client("target")
rows, by_tag = [], defaultdict(lambda: [0, 0])

for c in cases:
    output = llm.ask(c["prompt"], system=c.get("system"))
    results = [checks.run_check(output, spec) for spec in c["checks"]]
    passed = all(r.passed for r in results)
    for t in c.get("tags", []):
        by_tag[t][0] += passed
        by_tag[t][1] += 1
    print(f"\n{report.mark(passed)}  {report.bold(c['id'])}")
    print(report.dim("      output: " + report.shorten(output, 80)))
    for r in results:
        print(f"      {report.mark(r.passed)} {r.name}  {report.dim(r.detail)}")
    rows.append({"id": c["id"], "passed": passed, "output": output,
                 "failed_checks": [str(r) for r in results if not r.passed]})

report.section("Summary")
print("  " + report.rate_line("cases passed", sum(r["passed"] for r in rows), len(rows)))
for tag, (p, n) in sorted(by_tag.items()):
    print("    " + report.rate_line(f"tag:{tag:<14}", p, n))

report.save_results("p2_checks", rows)
report.explain(
    "Read each FAIL and ask: is the MODEL wrong, or is my CHECK wrong? Both happen. A check that "
    "fails a correct answer is a broken test, exactly like in traditional QA.",
    "Notice how many failures are about FORMAT (extra words, quotes, markdown fences) rather than "
    "knowledge. In real products format failures break parsers and UIs - they matter.",
    "The tag breakdown is your first 'quality dashboard': it tells you WHERE the model is weak "
    "(format? safety? accuracy?), which is more useful than one overall number.",
    "Deterministic checks can't judge meaning ('is this summary faithful?'). That's the job of "
    "Phase 3. Rule of thumb: use code checks wherever possible, judges only where you must.",
)
