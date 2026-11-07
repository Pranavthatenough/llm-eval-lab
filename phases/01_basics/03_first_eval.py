"""Phase 1.3 - Your first evaluation: the metric decides the result.

Run:  python phases/01_basics/03_first_eval.py

Lesson: we score the SAME answers three ways. The model doesn't change - only
our definition of "correct" does - yet the pass rate moves a lot.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import checks, get_client, here, load_jsonl, report

cases = load_jsonl(here(__file__) / "data" / "golden.jsonl")
report.banner(
    "Phase 1.3 - First eval",
    f"Ask {len(cases)} factual questions from a 'golden set' and score each answer with "
    "three different metrics: exact match, normalized match, and 'contains expected'.",
)
llm = get_client("target")
rows = []
for c in cases:
    answer = llm.ask(c["question"]).strip()
    rows.append({
        "id": c["id"],
        "expected": c["expected"],
        "answer": answer,
        "exact": checks.exact_match(answer, c["expected"]).passed,
        "normalized": checks.normalized_match(answer, c["expected"]).passed,
        "contains": checks.contains_all(answer, [c["expected"]]).passed,
    })

report.print_table(rows, [("id", "id", 4), ("expected", "expected", 9), ("answer", "model answer", 40),
                          ("exact", "exact", 6), ("normalized", "norm.", 6), ("contains", "contains", 8)])
n = len(rows)
print()
for metric in ("exact", "normalized", "contains"):
    print("  " + report.rate_line(f"{metric:<11}", sum(r[metric] for r in rows), n))

report.save_results("p1_first_eval", rows)
report.explain(
    "Exact match probably failed almost everything - the model said 'The capital of Australia is "
    "Canberra.' instead of 'Canberra'. Correct answer, failed test. That's a false negative caused "
    "by the METRIC, not the model.",
    "'Contains' is more forgiving but can produce false positives: an answer like 'It is not "
    "Canberra, it's Sydney' contains 'Canberra' and would pass. Open the saved CSV and read the "
    "answers yourself - never trust a score you haven't spot-checked.",
    "Look at the confidence interval. With 8 cases, a pass rate of 75% is statistically "
    "compatible with anything from roughly 40% to 93%. Small eval sets can't tell small "
    "differences apart - one of the most common mistakes in real LLM evaluation.",
    "Fix it two ways: (1) constrain the output ('Answer with only the answer') and/or (2) use a "
    "smarter check. Try adding system='Answer with only the answer, no sentence.' to llm.ask() "
    "and rerun. Did exact match jump? You just did prompt engineering *driven by a test*.",
)
