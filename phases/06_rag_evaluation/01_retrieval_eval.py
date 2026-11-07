"""Phase 6.1 - Evaluate RETRIEVAL on its own (no LLM answers yet).

Run:  python phases/06_rag_evaluation/01_retrieval_eval.py
      python phases/06_rag_evaluation/01_retrieval_eval.py --chunk-size 200

Lesson: a RAG answer can only be as good as the context it's given. If the
right document never reaches the model, no prompt can save it. So test the
retriever first, like testing a search feature:

  hit@k     - did at least one relevant document appear in the top k?
  recall@k  - what fraction of ALL relevant documents appeared in the top k?
  MRR       - how high was the first relevant result? (1 = top, 0.5 = 2nd, ...)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rag_pipeline as rag  # noqa: E402

from llmeval import LLMError, here, load_jsonl, report  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--chunk-size", type=int, default=None, help="words per chunk (default from config)")
args = ap.parse_args()

questions = [q for q in load_jsonl(here(__file__) / "data" / "questions.jsonl") if q["answerable"]]
chunks = rag.load_chunks(args.chunk_size)
report.banner("Phase 6.1 - Retrieval evaluation",
              f"{len(questions)} answerable questions, {len(chunks)} chunks. Compare keyword (BM25) vs "
              "embedding retrieval at k = 1, 3, 5.", roles=("embeddings",))

retrievers = [rag.KeywordRetriever(chunks)]
try:
    retrievers.append(rag.EmbeddingRetriever(chunks))
except LLMError as e:
    print(report.yellow(f"  Embedding retriever unavailable, comparing keyword only.\n  {e}"))

rows, summary = [], {}
for r in retrievers:
    report.section(f"Retriever: {r.name}")
    stats = {k: {"hit": 0, "recall": 0.0, "mrr": 0.0} for k in (1, 3, 5)}
    for q in questions:
        results = r.search(q["question"], 5)
        docs_ranked = [c.doc for c, _ in results]
        relevant = set(q["relevant_docs"])
        first = next((i + 1 for i, d in enumerate(docs_ranked) if d in relevant), None)
        for k in stats:
            top = set(docs_ranked[:k])
            stats[k]["hit"] += bool(top & relevant)
            stats[k]["recall"] += len(top & relevant) / len(relevant)
            stats[k]["mrr"] += (1 / first) if first and first <= k else 0
        rows.append({"retriever": r.name, "id": q["id"], "question": q["question"],
                     "relevant": sorted(relevant), "top3": [c.id for c, _ in results[:3]],
                     "hit@3": bool(set(docs_ranked[:3]) & relevant), "first_relevant_rank": first})
    sub = [x for x in rows if x["retriever"] == r.name]
    report.print_table(sub, [("id", "id", 4), ("question", "question", 40), ("relevant", "should find", 22),
                             ("top3", "retrieved top 3", 46), ("hit@3", "hit@3", 6)])
    n = len(questions)
    print()
    for k, s in stats.items():
        print(f"  k={k}:  hit@k={s['hit']/n:.2f}   recall@k={s['recall']/n:.2f}   MRR@k={s['mrr']/n:.2f}")
    summary[r.name] = {f"k{k}": {m: round(v / n, 3) if m != "hit" else round(v / n, 3)
                                 for m, v in s.items()} for k, s in stats.items()}

report.save_results("p6_retrieval", rows, summary)
report.explain(
    "Look for questions where the keyword retriever misses but embeddings hit (or vice versa). "
    "'Do you deliver to Mexico?' shares almost no words with 'We ship only to the United States "
    "and Canada' - keyword search fails on vocabulary mismatch; embeddings usually match on meaning.",
    "Multi-document questions (q8, q9) drag recall down: hit@3 can be 1 while recall@3 is 0.5. "
    "The model then has half the facts and will either give half an answer or fill the gap with "
    "a guess. Recall matters most for questions that combine sources.",
    "Increasing k raises recall but adds irrelevant text the model must ignore (more noise, more "
    "cost, more chance of being distracted). Re-run with --chunk-size 20 and --chunk-size 200 and "
    "watch how chunking alone changes the numbers - with zero model changes.",
    "Retrieval metrics need labels (which doc answers which question). Building that labelled set "
    "is real QA work - and the most valuable asset in any RAG test suite.",
)
