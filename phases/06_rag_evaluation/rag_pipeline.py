"""A deliberately tiny RAG (Retrieval-Augmented Generation) system - our system under test.

RAG = 1) RETRIEVE relevant text chunks for a question, then
      2) GENERATE an answer from those chunks.

It has two retrievers so you can compare them:
  keyword    - BM25 word matching (classic search, no model needed)
  embedding  - semantic similarity using an embedding model (e.g. nomic-embed-text)

Everything is in-memory and readable. Real systems swap in a vector database,
but the evaluation ideas are exactly the same.
"""
from __future__ import annotations

import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import get_client, load_config, load_prompt, render  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parent / "data" / "corpus"
STOPWORDS = set("a an the is are was were be to of and or in on for with at by from it its this that "
                "i my me do does did you your we our can how what which who when where why".split())


@dataclass
class Chunk:
    id: str        # e.g. "shipping#1"
    doc: str       # e.g. "shipping"
    text: str


def load_chunks(chunk_size_words: int | None = None) -> list[Chunk]:
    """Split each document into chunks of roughly chunk_size_words, on paragraph boundaries."""
    size = chunk_size_words or load_config().rag.get("chunk_size_words", 50)
    chunks: list[Chunk] = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        paras = [p.strip() for p in path.read_text(encoding="utf-8").split("\n\n") if p.strip()]
        title = paras[0].lstrip("# ").strip() if paras and paras[0].startswith("#") else path.stem
        buf: list[str] = []
        for para in paras:
            if para.startswith("#"):
                continue
            if buf and len(" ".join(buf + [para]).split()) > size:
                chunks.append(Chunk(f"{path.stem}#{len([c for c in chunks if c.doc == path.stem])}",
                                    path.stem, f"[{title}] " + " ".join(buf)))
                buf = []
            buf.append(para)
        if buf:
            chunks.append(Chunk(f"{path.stem}#{len([c for c in chunks if c.doc == path.stem])}",
                                path.stem, f"[{title}] " + " ".join(buf)))
    return chunks


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9$]+", text.lower()) if w not in STOPWORDS]


class KeywordRetriever:
    """BM25: scores chunks by shared words, weighting rare words more."""
    name = "keyword"

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.docs = [tokenize(c.text) for c in chunks]
        self.avgdl = sum(map(len, self.docs)) / len(self.docs)
        df = Counter(w for d in self.docs for w in set(d))
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        q = tokenize(query)
        scored = []
        for chunk, d in zip(self.chunks, self.docs):
            tf = Counter(d)
            s = sum(self.idf.get(w, 0) * tf[w] * (self.k1 + 1) /
                    (tf[w] + self.k1 * (1 - self.b + self.b * len(d) / self.avgdl)) for w in q)
            scored.append((chunk, s))
        return sorted(scored, key=lambda x: x[1], reverse=True)[:k]


class EmbeddingRetriever:
    """Embeds every chunk once, then ranks by cosine similarity to the question."""
    name = "embedding"

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.client = get_client("embeddings")
        # nomic-embed-text works best with task prefixes; harmless for other models
        self.vectors = self.client.embed([f"search_document: {c.text}" for c in chunks])

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        qv = self.client.embed([f"search_query: {query}"])[0]
        scored = [(c, _cosine(qv, v)) for c, v in zip(self.chunks, self.vectors)]
        return sorted(scored, key=lambda x: x[1], reverse=True)[:k]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def make_retriever(kind: str | None = None, chunks: list[Chunk] | None = None):
    kind = kind or load_config().rag.get("retriever", "embedding")
    chunks = chunks or load_chunks()
    if kind == "keyword":
        return KeywordRetriever(chunks)
    if kind == "embedding":
        return EmbeddingRetriever(chunks)
    raise ValueError(f"Unknown retriever '{kind}' (use keyword or embedding)")


def answer(question: str, retrieved: list[tuple[Chunk, float]]) -> str:
    context = "\n\n".join(f"<excerpt id='{c.id}'>\n{c.text}\n</excerpt>" for c, _ in retrieved)
    prompt = render(load_prompt("rag_answer"), context=context, question=question)
    return get_client("target").ask(prompt).strip()


if __name__ == "__main__":
    # Try it interactively: python phases/06_rag_evaluation/rag_pipeline.py "Do you ship to Canada?"
    q = " ".join(sys.argv[1:]) or "Do you ship to Canada?"
    r = make_retriever()
    hits = r.search(q, load_config().rag.get("top_k", 3))
    print(f"Retriever: {r.name}")
    for c, s in hits:
        print(f"  {s:6.3f}  {c.id:<20} {c.text[:70]}...")
    print("\nAnswer:", answer(q, hits))
