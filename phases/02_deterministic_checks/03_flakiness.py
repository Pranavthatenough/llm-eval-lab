"""Phase 2.3 - Flaky tests are a feature of LLMs, so measure them.

Run:  python phases/02_deterministic_checks/03_flakiness.py
      python phases/02_deterministic_checks/03_flakiness.py --repeats 5 --temperature 0.7

Lesson: run every case several times. A case that passes 3/5 times isn't
"passing" or "failing" - it has a 60% pass rate. That is the real result.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

from llmeval import checks, get_client, here, load_config, load_jsonl, report

ap = argparse.ArgumentParser()
ap.add_argument("--repeats", type=int, default=load_config().run.get("repeats", 3))
ap.add_argument("--temperature", type=float, default=0.7,
                help="use production-like randomness (default 0.7) to expose flakiness")
args = ap.parse_args()

cases = load_jsonl(here(__file__) / "data" / "cases.jsonl")
report.banner("Phase 2.3 - Flakiness",
              f"Run each case {args.repeats}x at temperature {args.temperature} with no fixed seed, "
              "then classify every case as stable-pass, stable-fail or FLAKY.")
llm = get_client("target")
rows = []
for c in cases:
    outcomes = []
    for _ in range(args.repeats):
        out = llm.ask(c["prompt"], system=c.get("system"), temperature=args.temperature, seed=None)
        outcomes.append(all(checks.run_check(out, s).passed for s in c["checks"]))
    rate = sum(outcomes) / len(outcomes)
    status = "stable-pass" if rate == 1 else "stable-fail" if rate == 0 else "FLAKY"
    rows.append({"id": c["id"], "pass_rate": rate, "status": status,
                 "runs": "".join("P" if o else "F" for o in outcomes)})

report.print_table(rows, [("id", "case", 14), ("runs", "runs", 12), ("pass_rate", "pass rate", 10),
                          ("status", "status", 12)])
flaky = [r for r in rows if r["status"] == "FLAKY"]
total_runs = len(rows) * args.repeats
total_pass = sum(round(r["pass_rate"] * args.repeats) for r in rows)
print()
print("  " + report.rate_line("all runs passed", total_pass, total_runs))
print(f"  flaky cases: {len(flaky)} of {len(rows)}")

report.save_results("p2_flakiness", rows, {"repeats": args.repeats, "temperature": args.temperature})
report.explain(
    "If you only ran each case once (as in 2.1), a FLAKY case would have looked like either a pass "
    "or a fail at random. Your test report would change between runs with no code change - "
    "the #1 complaint teams have about LLM test suites.",
    "How real teams handle it: (1) run N times and gate on a pass-RATE threshold (e.g. >= 80% over "
    "5 runs) instead of a single pass/fail; (2) track the rate over time - a drop from 100% to 60% "
    "is a regression even if the last single run happened to pass.",
    "A flaky case is also a product signal: real users hitting that prompt get inconsistent "
    "behaviour. Sometimes the fix is in the prompt (tighter instructions), not the test.",
    "Try --temperature 0. Fewer flaky cases? That tells you how much of your flakiness is "
    "sampling randomness versus the prompt being genuinely ambiguous.",
)
