"""Phase 3.2 - Known judge biases: position, verbosity, and inconsistency.

Run:  python phases/03_llm_as_judge/02_judge_biases.py

Lesson: LLM judges have systematic biases you can measure:
  * position bias  - prefers whichever answer is shown first (or second)
  * verbosity bias - prefers longer, more confident-sounding answers
  * inconsistency  - gives different grades to the same input on re-runs
Every pair here has an objectively better answer, so we know the truth.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import get_client, here, judge, load_jsonl, report

CRITERIA = "Which answer is more factually correct and useful?"
pairs = load_jsonl(here(__file__) / "data" / "pairs.jsonl")
report.banner("Phase 3.2 - Judge biases",
              "Show the judge each pair twice - better answer as A, then as B. A fair judge picks "
              "the better answer both times.", roles=("judge",))

rows = []
for p in pairs:
    w1, _ = judge.judge_pairwise(p["question"], p["better"], p["worse"], CRITERIA)  # better is A
    w2, _ = judge.judge_pairwise(p["question"], p["worse"], p["better"], CRITERIA)  # better is B
    right1, right2 = w1 == "A", w2 == "B"
    rows.append({"id": p["id"], "bias": p["bias"], "order1_pick": w1, "order2_pick": w2,
                 "correct_both": right1 and right2, "consistent": (right1 == right2),
                 "picked_first_both": w1 == "A" and w2 == "A"})

report.print_table(rows, [("id", "id", 4), ("bias", "testing", 10), ("order1_pick", "better=A -> pick", 17),
                          ("order2_pick", "better=B -> pick", 17), ("correct_both", "right both", 10)])

report.section("Position & verbosity")
for bias in ("position", "verbosity"):
    sub = [r for r in rows if r["bias"] == bias]
    print("  " + report.rate_line(f"{bias:<9} pairs judged correctly in BOTH orders",
                                  sum(r["correct_both"] for r in sub), len(sub)))
first = sum(r["picked_first_both"] for r in rows)
print(f"  pairs where judge picked 'A' regardless of order: {first} of {len(rows)}")

report.section("Consistency: grade the same answer 5 times at temperature 0.7")
judge_client = get_client("judge")
item = pairs[3]  # a verbosity trap: long answer with a wrong year
scores = []
for _ in range(5):
    v = judge.judge_score(item["question"], item["worse"],
                          "Is the answer factually correct?", client=judge_client,
                          temperature=0.7, seed=None)
    scores.append(v.score)
print(f"  question: {item['question']}")
print(f"  scores for the same wrong answer: {scores}")
valid = [s for s in scores if s is not None]
if len(valid) > 1:
    print(f"  spread: min={min(valid)} max={max(valid)} stdev={statistics.pstdev(valid):.2f}")
print(report.dim("  (Your real judge runs at temperature 0 - this shows what happens if it doesn't.)"))

report.save_results("p3_judge_biases", rows, {"repeat_scores": scores})
report.explain(
    "If a pair is right in one order but wrong in the other, the judge isn't judging content - "
    "the ORDER changed its mind. Standard mitigation: always judge both orders and only count a "
    "win if both agree (otherwise call it a tie). That doubles cost but removes this bias.",
    "Verbosity pairs hide a factual error inside a long, fluent answer. If the judge prefers the "
    "long one, it is rewarding style over truth - the same failure a busy human reviewer makes. "
    "Mitigations: a rubric that explicitly says 'ignore length', reference answers, and checking "
    "facts with deterministic checks where possible.",
    "Consistency: a judge that scores the same input 2 one time and 4 the next adds noise to "
    "every metric built on it. Keep judge temperature at 0, and for important decisions score "
    "multiple times and take the median.",
    "Big picture: the judge is code under test too. Version its prompt, track its agreement "
    "with humans, and re-check it whenever you change the judge model.",
)
