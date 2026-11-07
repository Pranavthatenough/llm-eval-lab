"""Phase 2.2 - Structured output: valid is not the same as correct.

Run:  python phases/02_deterministic_checks/02_structured_output.py

Lesson: many LLM features extract data into JSON that other code consumes.
We test the same extraction task two ways:
  A) "prompt only"      - ask nicely for JSON in the prompt
  B) "schema enforced"  - pass a JSON schema so the provider constrains output
and measure three separate things: parseable? matches schema? fields correct?
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import checks, extract_json, get_client, here, load_jsonl, report

SCHEMA = {
    "type": "object",
    "properties": {
        "customer_name": {"type": "string"},
        "category": {"type": "string", "enum": ["billing", "bug", "feature_request", "account"]},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["customer_name", "category", "priority"],
}
INSTRUCTIONS = (
    "Extract fields from the support ticket below.\n"
    "category must be one of: billing, bug, feature_request, account.\n"
    "priority must be one of: low, medium, high (high = money lost or users blocked).\n"
    'Return JSON like {"customer_name": "...", "category": "...", "priority": "..."}\n\n'
    "Ticket:\n"
)

tickets = load_jsonl(here(__file__) / "data" / "tickets.jsonl")
report.banner("Phase 2.2 - Structured output",
              f"Extract fields from {len(tickets)} support tickets, with and without schema enforcement.")
llm = get_client("target")
rows = []
for mode in ("prompt_only", "schema_enforced"):
    report.section(mode)
    for t in tickets:
        res = llm.chat([{"role": "user", "content": INSTRUCTIONS + t["text"]}],
                       json_schema=SCHEMA if mode == "schema_enforced" else None)
        strict = checks.is_valid_json(res.text).passed
        data = extract_json(res.text)
        schema_ok = checks.json_schema(data, SCHEMA).passed if data is not None else False
        exp = t["expected"]
        got = data if isinstance(data, dict) else {}
        fields = {
            "category": got.get("category") == exp["category"],
            "priority": got.get("priority") == exp["priority"],
            "name": checks.normalize(str(got.get("customer_name", ""))) == checks.normalize(exp["customer_name"]),
        }
        row = {"mode": mode, "id": t["id"], "strict_json": strict, "schema_ok": schema_ok,
               "all_fields_ok": all(fields.values()), **{f"{k}_ok": v for k, v in fields.items()},
               "output": res.text}
        rows.append(row)
        wrong = [f"{k}: expected {exp[k if k != 'name' else 'customer_name']!r} got "
                 f"{got.get(k if k != 'name' else 'customer_name')!r}" for k, v in fields.items() if not v]
        print(f"  {t['id']}  strict_json={report.mark(strict)}  schema={report.mark(schema_ok)}  "
              f"fields={report.mark(all(fields.values()))}  {report.dim('; '.join(wrong))}")

report.section("Summary")
for mode in ("prompt_only", "schema_enforced"):
    mr = [r for r in rows if r["mode"] == mode]
    print(f"  {report.bold(mode)}")
    for key, label in (("strict_json", "strictly valid JSON"), ("schema_ok", "matches schema"),
                       ("all_fields_ok", "all fields correct")):
        print("    " + report.rate_line(f"{label:<20}", sum(r[key] for r in mr), len(mr)))

report.save_results("p2_structured_output", rows)
report.explain(
    "Schema enforcement usually pushes 'valid JSON' and 'matches schema' close to 100% - the "
    "provider literally prevents the model from producing anything else. That's a cheap, huge win.",
    "But look at 'all fields correct'. Enforcement guarantees the SHAPE, not the TRUTH. The model "
    "can still put 'medium' where a human says 'high'. Priority is a judgement call - check whether "
    "you even agree with the expected labels. Ambiguous labels = noisy tests.",
    "In prompt-only mode, failures where JSON was 'only parseable after stripping extra text' are "
    "the classic production bug: works in the demo, breaks the parser when the model adds "
    "'Here is your JSON:'.",
    "Real-world rule: test layers separately - (1) parseable, (2) schema-valid, (3) semantically "
    "correct. Each layer fails for different reasons and needs a different fix.",
)
