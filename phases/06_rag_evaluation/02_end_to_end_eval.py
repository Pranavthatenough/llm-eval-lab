"""Phase 6.2 - End-to-end RAG evaluation, and WHERE it broke.

Run:  python phases/06_rag_evaluation/02_end_to_end_eval.py
      python phases/06_rag_evaluation/02_end_to_end_eval.py --retriever keyword --top-k 1

Lesson: for each question we measure the whole chain and then DIAGNOSE.
  retrieval  - did the right document reach the model?        (labels, no LLM)
  correct    - does the answer match the reference?            (judge + reference)
  faithful   - is every claim backed by the retrieved context? (judge)
  abstain    - for unanswerable questions, did it say "I don't know"?

A single "accuracy" number tells you THAT it fails. The diagnosis tells you
WHICH COMPONENT to fix - which is what a bug report needs.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rag_pipeline as rag  # noqa: E402

from llmeval import here, judge, load_config, load_jsonl, report  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--retriever", choices=["keyword", "embedding"], default=None)
ap.add_argument("--top-k", type=int, default=None)
args = ap.parse_args()
cfg = load_config()
top_k = args.top_k or cfg.rag.get("top_k", 3)

questions = load_jsonl(here(__file__) / "data" / "questions.jsonl")
retriever = rag.make_retriever(args.retriever)
report.banner("Phase 6.2 - End-to-end RAG",
              f"retriever={retriever.name}, top_k={top_k}, {len(questions)} questions "
              f"({sum(not q['answerable'] for q in questions)} unanswerable).",
              roles=("target", "judge", "embeddings"))


def diagnose(q: dict, retrieved_ok: bool, correct: bool, faithful: bool, abstained: bool) -> str:
    if not q["answerable"]:
        return "OK (abstained)" if abstained else "GENERATION: answered the unanswerable"
    if correct and faithful:
        return "OK"
    if abstained:
        return "RETRIEVAL: context missing" if not retrieved_ok else "GENERATION: wrongly abstained"
    if not retrieved_ok:
        return ("SUSPICIOUS: right answer w/o right context" if correct
                else "RETRIEVAL: wrong/missing context")
    if not faithful:
        return "GENERATION: added unsupported claims"
    return "GENERATION: wrong answer despite context"


rows = []
for q in questions:
    hits = retriever.search(q["question"], top_k)
    got_docs = {c.doc for c, _ in hits}
    relevant = set(q["relevant_docs"])
    retrieved_ok = relevant <= got_docs if q["answerable"] else True
    ans = rag.answer(q["question"], hits)
    abstained = "don't know" in ans.lower() or "do not know" in ans.lower()
    context = "\n".join(c.text for c, _ in hits)

    faith = judge.judge_binary(
        f"Context:\n{context}\n\nAnswer:\n{ans}\n\n"
        "Is EVERY factual claim in the answer supported by the context? "
        "(An answer that only says it doesn't know counts as yes.)")
    faithful = faith.score == 1
    if q["answerable"]:
        corr = judge.judge_score(q["question"], ans, "Does the answer correctly answer the customer's "
                                 "question, consistent with the reference?", reference=q["reference"])
        correct = corr.passed
    else:
        correct = abstained
    verdict = diagnose(q, retrieved_ok, correct, faithful, abstained)
    rows.append({"id": q["id"], "question": q["question"], "answer": ans,
                 "retrieved": sorted(got_docs), "retrieval_ok": retrieved_ok, "correct": correct,
                 "faithful": faithful, "diagnosis": verdict, "passed": verdict.startswith("OK")})

report.print_table(rows, [("id", "id", 4), ("answer", "answer", 40), ("retrieval_ok", "retr.", 5),
                          ("correct", "corr.", 5), ("faithful", "faith", 5), ("diagnosis", "diagnosis", 38)])

report.section("Scorecard")
ans_rows = [r for r in rows if r["id"] in {q["id"] for q in questions if q["answerable"]}]
una_rows = [r for r in rows if r not in ans_rows]
print("  " + report.rate_line("retrieval got all relevant docs", sum(r["retrieval_ok"] for r in ans_rows), len(ans_rows)))
print("  " + report.rate_line("answers correct               ", sum(r["correct"] for r in ans_rows), len(ans_rows)))
print("  " + report.rate_line("answers faithful to context   ", sum(r["faithful"] for r in rows), len(rows)))
print("  " + report.rate_line("unanswerable -> abstained     ", sum(r["correct"] for r in una_rows), len(una_rows)))
print("  " + report.rate_line("OVERALL OK                    ", sum(r["passed"] for r in rows), len(rows)))
report.section("Where it broke")
for diag, n in Counter(r["diagnosis"] for r in rows).most_common():
    print(f"  {n:>2} x {diag}")

report.save_results("p6_end_to_end", rows, {"retriever": retriever.name, "top_k": top_k})
report.explain(
    "Read the 'Where it broke' list as a triage report. RETRIEVAL failures go to whoever owns "
    "search/indexing (chunking, embeddings, top_k). GENERATION failures go to whoever owns the "
    "prompt/model. Same symptom - wrong answer - completely different fix.",
    "'SUSPICIOUS: right answer without right context' means the model answered from its own "
    "knowledge. Our corpus is fictional, so that's either luck or a judge error. In a real "
    "product it's a red flag: the next time, its 'own knowledge' will be out of date or wrong.",
    "Experiments that teach the most: --top-k 1 (retrieval starves the model), --retriever "
    "keyword (vocabulary mismatch), or edit a corpus file to contradict the reference answer and "
    "see whether 'faithful' and 'correct' disagree. Faithful-but-incorrect = your DOCS have a bug.",
    "These scores rely on the judge. Before trusting them, spot-check 3-4 rows in the CSV by hand "
    "- the Phase 3 habit.",
)
