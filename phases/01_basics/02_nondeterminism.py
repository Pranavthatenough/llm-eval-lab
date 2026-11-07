"""Phase 1.2 - Same input, different output.

Run:  python phases/01_basics/02_nondeterminism.py

Lesson: traditional tests assume f(x) always returns the same y. LLMs don't.
We send the same prompt several times at different temperatures and count how
many DIFFERENT answers come back.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import get_client, report

N = 5
PROMPT = "Suggest a name for a coffee shop run by software testers. Reply with only the name."

report.banner(
    "Phase 1.2 - Non-determinism",
    f"Send the same prompt {N} times under three settings and count distinct outputs.",
)
llm = get_client("target")
msgs = [{"role": "user", "content": PROMPT}]

settings = [
    ("temperature 0, fixed seed", dict(temperature=0.0, seed=42)),
    ("temperature 0, no seed", dict(temperature=0.0, seed=None)),
    ("temperature 1.0, no seed", dict(temperature=1.0, seed=None)),
]
rows = []
for label, kw in settings:
    report.section(label)
    outputs = []
    for i in range(N):
        text = llm.chat(msgs, **kw).text.strip()
        outputs.append(text)
        print(f"  run {i+1}: {report.shorten(text, 70)}")
    counts = Counter(outputs)
    print(report.bold(f"  -> {len(counts)} distinct output(s) out of {N}"))
    rows.append({"setting": label, "distinct": len(counts), "runs": N, "outputs": outputs})

report.save_results("p1_nondeterminism", rows)
report.explain(
    "Temperature controls randomness. At 0 the model (almost) always picks its most likely next "
    "token, so outputs tend to repeat. At 1.0 it samples, so you get variety - which is what "
    "creative features want and what assertions hate.",
    "Even temperature 0 is not a guarantee: batching, GPU maths and server versions can change "
    "outputs. Treat 'same every time' as likely, never as promised.",
    "QA takeaway #1: an assertion like `assert output == 'Bug & Brew'` is a flaky test waiting to "
    "happen. Phase 2 replaces exact matches with checks on PROPERTIES of the output.",
    "QA takeaway #2: pin temperature/seed for regression runs (less noise), but ALSO test at the "
    "temperature production uses - that's what your users actually get.",
)
