"""Phase 4.2 - Faithfulness: does the answer stick to the provided context?

Run:  python phases/04_hallucination/02_grounded_faithfulness.py

Lesson: in real apps the model is usually GIVEN information (a document, a
spec, retrieved search results) and must answer only from it. "Grounded
hallucination" = adding facts that aren't in the context.

Method (the same idea behind tools like RAGAS):
  1. the target model answers using only the context
  2. the judge breaks the answer into atomic claims
  3. the judge checks each claim against the context
  faithfulness = supported claims / total claims
Some questions are deliberately NOT answerable from the context.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import get_client, here, judge, load_jsonl, report

SYSTEM = ("Answer the question using ONLY the context. If the context does not contain the "
          "answer, reply exactly: I don't know based on the provided context.")
CLAIMS_SCHEMA = {"type": "object", "properties": {"claims": {"type": "array", "items": {"type": "string"}}},
                 "required": ["claims"]}

cases = load_jsonl(here(__file__) / "data" / "grounded.jsonl")
report.banner("Phase 4.2 - Grounded faithfulness",
              f"{len(cases)} questions over short documents; "
              f"{sum(not c['answerable'] for c in cases)} are not answerable from the document.",
              roles=("target", "judge"))
llm, jd = get_client("target"), get_client("judge")
rows = []
for c in cases:
    prompt = f"Context:\n<context>\n{c['context']}\n</context>\n\nQuestion: {c['question']}"
    answer = llm.ask(prompt, system=SYSTEM).strip()
    said_idk = "don't know" in answer.lower() or "do not know" in answer.lower()

    data, _ = jd.ask_json(
        "Break this answer into short, atomic factual claims (one fact each). Ignore filler. "
        "If the answer only says it doesn't know, return an empty list.\n\n"
        f"Answer: {answer}\n\nReturn JSON: {{\"claims\": [\"...\"]}}", schema=CLAIMS_SCHEMA)
    claims = data.get("claims", []) if isinstance(data, dict) else []
    supported, unsupported = 0, []
    for claim in claims:
        v = judge.judge_binary(f"Context:\n{c['context']}\n\nClaim: {claim}\n\n"
                               "Is this claim directly supported by the context?")
        if v.score == 1:
            supported += 1
        else:
            unsupported.append(claim)
    faith = supported / len(claims) if claims else (1.0 if said_idk else 0.0)

    if c["answerable"]:
        passed = (not said_idk) and faith >= 0.99
        verdict = "should answer"
    else:
        passed = said_idk and not unsupported
        verdict = "should say IDK"
    rows.append({"id": c["id"], "expect": verdict, "answer": answer, "claims": len(claims),
                 "faithfulness": round(faith, 2), "unsupported": unsupported, "passed": passed})

report.print_table(rows, [("id", "id", 4), ("expect", "expected", 15), ("answer", "answer", 44),
                          ("faithfulness", "faith.", 6), ("passed", "result", 6)])
for r in rows:
    if r["unsupported"]:
        print(report.red(f"  {r['id']} unsupported claims: ") + "; ".join(r["unsupported"]))

answerable = [r for r in rows if r["expect"] == "should answer"]
unanswerable = [r for r in rows if r["expect"] != "should answer"]
avg = sum(r["faithfulness"] for r in answerable) / max(1, len(answerable))
report.section("Scores")
print(f"  mean faithfulness on answerable questions: {avg:.2f}")
print("  " + report.rate_line("answerable handled correctly  ", sum(r["passed"] for r in answerable), len(answerable)))
print("  " + report.rate_line("unanswerable -> said IDK      ", sum(r["passed"] for r in unanswerable), len(unanswerable)))

report.save_results("p4_faithfulness", rows)
report.explain(
    "Faithfulness is NOT correctness. An answer can be 100% faithful to a wrong document, or "
    "correct-in-the-real-world but unfaithful (the model used its own knowledge). For grounded "
    "apps you usually want faithfulness first: the document is the source of truth.",
    "The unanswerable questions are the real test. 'Who is fixing the checkout bugs?' sounds "
    "answerable - Amara is mentioned - but she owns the checklist, not the bugs. Models love to "
    "connect nearby facts. Did yours?",
    "g6 needs a small calculation (40 days x $0.25 = $10, capped at $5). Calculation steps are "
    "where grounded answers often go wrong even when every fact is in the context.",
    "This metric uses the judge twice per claim, so judge errors compound. Spot-check unsupported "
    "claims yourself; if the judge flags true claims, revisit Phase 3 and calibrate it.",
)
