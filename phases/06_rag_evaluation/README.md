# Phase 6 - RAG evaluation

**Goal:** evaluate a retrieval-augmented generation system piece by piece, so a wrong answer becomes a precise bug report: *search* failed, or *generation* failed.

## Concepts

**RAG** = Retrieve relevant chunks from a knowledge base, then Generate an answer from them. Our system under test is `rag_pipeline.py` - ~120 readable lines - over a fictional outdoor shop's help centre (`data/corpus/`). The facts are invented on purpose: the model *can't* know them from training, so any correct answer must come from retrieval.

Try it directly:
```bash
python phases/06_rag_evaluation/rag_pipeline.py "Do you ship to Canada?"
```

**Evaluate the two halves separately:**

| Stage | Metric | Needs | Question it answers |
|---|---|---|---|
| Retrieval | hit@k | labels | did *any* relevant doc make the top k? |
| Retrieval | recall@k | labels | did *all* the needed docs make the top k? |
| Retrieval | MRR | labels | how high was the first relevant result? |
| Generation | faithfulness | judge | is every claim supported by the retrieved text? |
| End to end | correctness | judge + reference | does the answer match the reference? |
| End to end | abstention | string check | does it say "I don't know" when it should? |

**Diagnosis beats a single score.** 6.2 classifies each question:

| Retrieved right docs? | Answer correct? | Diagnosis | Who fixes it |
|---|---|---|---|
| yes | yes | OK | - |
| no | no | RETRIEVAL failure | search / chunking / embeddings |
| yes | no | GENERATION failure | prompt / model |
| no | yes | SUSPICIOUS | model used outside knowledge - or the judge erred |

**Two retrievers to compare:** `keyword` (BM25, classic search) and `embedding` (semantic similarity via `nomic-embed-text`).

## Exercises

| # | Run | What you'll see |
|---|---|---|
| 6.1 | `python lab.py run 6.1` | hit@k, recall@k and MRR for keyword vs embedding retrieval, no LLM answers involved |
| 6.2 | `python lab.py run 6.2` | full pipeline with per-question correctness, faithfulness and a "where it broke" triage list |

Useful flags: `01_retrieval_eval.py --chunk-size 20`, `02_end_to_end_eval.py --retriever keyword --top-k 1`.

## Reading your results

- **Keyword misses on "Do you deliver to Mexico?"** - the docs say "ship", the user said "deliver". Vocabulary mismatch is keyword search's classic weakness; embeddings usually handle it (check whether yours did).
- **q8 and q9 need two documents each.** hit@3 can look perfect while recall@3 is 0.5. Half the facts in, half an answer (or a guess) out.
- **Faithful but incorrect** = the answer matches the context, but the context is wrong. That's a *content* bug.
- **Correct but unfaithful** = the model ignored the context. With a fictional corpus, treat it as a red flag (or a judge error to check by hand).

## Break it (challenges)

1. Run 6.2 with `--top-k 1`. Watch retrieval failures pile up while the model and prompt stay identical.
2. Edit `data/corpus/shipping.md` so standard shipping is $7.99, but leave the reference answer at $5.99. Which metric catches it - faithfulness or correctness?
3. Add a near-duplicate, outdated document (e.g. an old returns policy saying 14 days). Does retrieval pick the wrong one? This is the "stale document" bug teams hit constantly.
4. Change `chunk_size_words` in `config.yaml` to 20 and to 200 and compare 6.1 results.

## Real-world notes

- The labelled question set (question -> which docs answer it -> reference answer) is the most valuable asset in RAG testing. Build it with domain experts and grow it from real user questions and failures.
- Retrieval eval is cheap (no LLM calls). Run it on every index or chunking change.
- Popular frameworks (Ragas, DeepEval, TruLens) compute variants of exactly these metrics - now you know what they mean under the hood.
