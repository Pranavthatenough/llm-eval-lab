"""Phase 4.3 - Self-consistency: if it's guessing, it won't guess the same twice.

Run:  python phases/04_hallucination/03_self_consistency.py

Lesson: when a model KNOWS a fact, sampling it several times at high
temperature gives the same answer. When it's making something up, answers
scatter. Agreement across samples is a reference-free hallucination signal
(the idea behind SelfCheckGPT) - useful when you have no ground truth.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import checks, get_client, report

N = 5
QUESTIONS = [
    ("known", "In what year did the Berlin Wall fall?"),
    ("known", "What is the chemical symbol for sodium?"),
    ("known", "Who painted the Mona Lisa?"),
    ("unknown", "In what year was the Okonkwo-Lindqvist sorting theorem first proved?"),
    ("unknown", "What was the name of the first cat to live aboard the International Space Station?"),
    ("unknown", "What is the middle name of the inventor of the Quorbel test framework?"),
]
SYSTEM = "Answer with just the answer, in five words or fewer. No explanation."

report.banner("Phase 4.3 - Self-consistency",
              f"Ask each question {N} times at temperature 1.0 and measure how often the answers agree.")
llm = get_client("target")
rows = []
for kind, q in QUESTIONS:
    answers = [checks.normalize(llm.ask(q, system=SYSTEM, temperature=1.0, seed=None)) for _ in range(N)]
    top, count = Counter(answers).most_common(1)[0]
    agreement = count / N
    rows.append({"kind": kind, "question": q, "agreement": agreement, "top_answer": top,
                 "distinct": len(set(answers)), "answers": answers,
                 "flag": "LIKELY GUESSING" if agreement < 0.6 else ""})

report.print_table(rows, [("kind", "truth", 8), ("question", "question", 42), ("top_answer", "most common", 18),
                          ("agreement", "agree", 6), ("flag", "", 16)])
for kind in ("known", "unknown"):
    sub = [r for r in rows if r["kind"] == kind]
    print(f"  mean agreement on {kind:<7} questions: {sum(r['agreement'] for r in sub)/len(sub):.2f}")

report.save_results("p4_self_consistency", rows)
report.explain(
    "If the 'unknown' questions show lower agreement than the 'known' ones, you've seen the "
    "signal: inconsistent answers point to fabrication. This needs no reference answer, so it "
    "works on questions where you don't know the truth either.",
    "It's a SIGNAL, not proof. A model can be consistently wrong (it learned a false fact), and "
    "it can consistently say 'unknown'. Look at the top answers: is 'unknown'-type text the "
    "consistent answer? That's the good outcome.",
    "Cost: N calls per question. In practice teams use this on a sample of production traffic or "
    "on high-risk answers, not on everything.",
    "Exact-string agreement is strict: '1989' and 'in 1989' count as different after normalising "
    "only punctuation. A better version compares answers with an LLM judge ('do these mean the "
    "same?'). Try building that as an extension.",
)
