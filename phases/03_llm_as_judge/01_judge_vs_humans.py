"""Phase 3.1 - Can you trust your judge? Calibrate it against human labels.

Run:  python phases/03_llm_as_judge/01_judge_vs_humans.py

Lesson: an LLM judge is a measuring instrument. Before using it, you test it -
just like you'd calibrate a scale. We take 12 answers that a HUMAN already
scored (including deliberate traps), let the judge score them with and without
a reference answer, and measure how often it agrees with the human.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import here, judge, load_jsonl, report

CRITERIA = "Is the answer factually correct and does it actually answer the question asked?"

items = load_jsonl(here(__file__) / "data" / "graded_answers.jsonl")
report.banner("Phase 3.1 - Judge vs humans",
              f"Score {len(items)} pre-labelled answers with the judge, twice: once with a reference "
              "answer and once without. Compare against human scores.", roles=("judge",))
rows = []
for it in items:
    with_ref = judge.judge_score(it["question"], it["answer"], CRITERIA, reference=it["reference"])
    no_ref = judge.judge_score(it["question"], it["answer"], CRITERIA)
    rows.append({
        "id": it["id"], "trap": it["trap"], "human": it["human_score"],
        "judge_ref": with_ref.score, "judge_noref": no_ref.score,
        "reason_ref": with_ref.reasoning, "answer": it["answer"],
    })

report.print_table(rows, [("id", "id", 4), ("trap", "what the answer is", 36), ("human", "human", 6),
                          ("judge_ref", "judge+ref", 9), ("judge_noref", "judge no-ref", 12)])


def agreement(key: str) -> dict:
    valid = [r for r in rows if r[key] is not None]
    n = len(valid)
    exact = sum(r[key] == r["human"] for r in valid)
    within1 = sum(abs(r[key] - r["human"]) <= 1 for r in valid)
    pass_agree = sum((r[key] >= 4) == (r["human"] >= 4) for r in valid)
    false_pass = [r["id"] for r in valid if r[key] >= 4 and r["human"] < 4]
    false_fail = [r["id"] for r in valid if r[key] < 4 and r["human"] >= 4]
    mae = sum(abs(r[key] - r["human"]) for r in valid) / n if n else 0
    return dict(n=n, exact=exact, within1=within1, pass_agree=pass_agree, mae=mae,
                false_pass=false_pass, false_fail=false_fail, unparsed=len(rows) - n)


summary = {}
for key, label in (("judge_ref", "WITH reference"), ("judge_noref", "WITHOUT reference")):
    a = agreement(key)
    summary[key] = a
    report.section(f"Judge {label}")
    print("  " + report.rate_line("exact score match     ", a["exact"], a["n"]))
    print("  " + report.rate_line("within 1 point        ", a["within1"], a["n"]))
    print("  " + report.rate_line("same pass/fail (>=4)  ", a["pass_agree"], a["n"]))
    print(f"  mean absolute error   : {a['mae']:.2f} points")
    print(f"  FALSE PASSES (judge ok, human not): {a['false_pass'] or 'none'}")
    print(f"  false fails  (judge not, human ok): {a['false_fail'] or 'none'}")
    if a["unparsed"]:
        print(report.yellow(f"  judge output unparseable on {a['unparsed']} item(s)"))

disagree = [r for r in rows if r["judge_ref"] is not None and abs(r["judge_ref"] - r["human"]) >= 2]
if disagree:
    report.section("Biggest disagreements (read the judge's reasoning!)")
    for r in disagree:
        print(f"  {r['id']} human={r['human']} judge={r['judge_ref']}  [{r['trap']}]")
        print(report.dim(f"     judge said: {report.shorten(r['reason_ref'], 160)}"))

report.save_results("p3_judge_vs_humans", rows, summary)
report.explain(
    "FALSE PASSES are the dangerous number. A judge that rates a wrong answer 4-5 will let real "
    "bugs ship with a green dashboard. Look at which traps caused them - long confident answers "
    "(j2, j12) and plausible-sounding fabrications (j8) are classic judge blind spots.",
    "Compare WITH vs WITHOUT reference. A reference answer usually makes the judge much more "
    "accurate, because it no longer relies on its own (possibly wrong) knowledge. If you can "
    "write reference answers for your test set, do it.",
    "Rough industry rule: if a judge agrees with humans on pass/fail less than ~80-85% of the time "
    "on YOUR data, don't automate decisions with it yet - fix the rubric, use a stronger judge "
    "model, or add references, then re-calibrate. Re-run this whenever you change the judge.",
    "Experiment: edit prompts/judge_score.txt (e.g. remove the 'Judge correctness, NOT length' "
    "rule) and rerun. Watching the agreement number move is how you learn to write rubrics.",
)
