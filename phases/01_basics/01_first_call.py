"""Phase 1.1 - Your first model call, with nothing hidden.

Run:  python phases/01_basics/01_first_call.py
      python phases/01_basics/01_first_call.py "Your own question here"

Lesson: a model call is just an HTTP request with a list of messages and some
settings. Before you can test something, you must know exactly what goes in and
what comes out - including time and token counts, which ARE test results too.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import get_client, report

question = " ".join(sys.argv[1:]) or "In one sentence, what is software testing?"
system = "You are a concise assistant. Answer in at most two sentences."

report.banner(
    "Phase 1.1 - First call",
    "Send one request and inspect every part of it: the messages we send, the settings, "
    "the text that comes back, how long it took and how many tokens it used.",
)

llm = get_client("target")
messages = [
    {"role": "system", "content": system},   # the 'rules' the app sets - users usually can't see this
    {"role": "user", "content": question},   # what the user typed
]

report.section("1. What we send")
print(json.dumps({"model": llm.cfg.model, "temperature": llm.cfg.temperature,
                  "seed": llm.cfg.seed, "messages": messages}, indent=2))

result = llm.chat(messages)

report.section("2. What comes back")
print(result.text)

report.section("3. Metadata (also test data!)")
print(f"  latency            : {result.latency_s:.2f}s")
print(f"  prompt tokens      : {result.prompt_tokens}")
print(f"  completion tokens  : {result.completion_tokens}")
words = len(result.text.split())
print(f"  words in answer    : {words}")

report.explain(
    "The system message is part of the input you control; the user message is the part real "
    "users control. Most LLM bugs live in the gap between the two.",
    "Latency and tokens are measurable, repeatable quality signals: a prompt change that doubles "
    "output tokens doubles cost and slows the product down even if the answer is still 'right'.",
    "The first call is often slow because Ollama loads the model into memory. Run this script "
    "twice and compare latency - that is a warm vs cold start, a classic performance-test concern.",
    "Try: change the system message to 'Answer like a pirate' and run again. Same question, very "
    "different output. The system prompt is code - version it and test it like code.",
)
