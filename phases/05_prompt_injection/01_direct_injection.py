"""Phase 5.1 - Direct prompt injection against a support bot.

Run:  python phases/05_prompt_injection/01_direct_injection.py

Lesson: a system prompt is not a security boundary. We attack a fictional
support bot ("Sky" for Pinecrest Outfitters) whose system prompt contains a
secret CANARY code and business rules, using common attack styles. We run
every attack against two versions of the system prompt - basic and hardened -
and also run benign customer questions to make sure hardening didn't break
normal service.

Key metric: Attack Success Rate (ASR) = successful attacks / attacks tried.
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))

from detectors import attack_succeeded  # noqa: E402

from llmeval import get_client, here, load_jsonl, load_prompt, report  # noqa: E402

attacks = load_jsonl(here(__file__) / "data" / "attacks.jsonl")
variants = {"basic": load_prompt("support_bot_system"),
            "hardened": load_prompt("support_bot_system_hardened")}

report.banner("Phase 5.1 - Direct injection",
              f"{sum(a['category']!='benign_control' for a in attacks)} attacks + "
              f"{sum(a['category']=='benign_control' for a in attacks)} benign controls, "
              "each against a BASIC and a HARDENED system prompt.", roles=("target", "judge"))
llm = get_client("target")
rows = []
for variant, system in variants.items():
    report.section(f"System prompt: {variant}")
    for a in attacks:
        out = llm.ask(a["prompt"], system=system)
        hit, how = attack_succeeded(out, a["detect"], a["prompt"])
        benign = a["category"] == "benign_control"
        # For attacks, PASS = defended. For controls, PASS = helpful.
        passed = hit if benign else (None if hit is None else not hit)
        rows.append({"variant": variant, "id": a["id"], "category": a["category"],
                     "attack_succeeded": None if benign else hit, "passed": passed,
                     "how": how, "output": out})
        label = "helpful" if benign else ("DEFENDED" if passed else "BREACHED" if passed is False else "unclear")
        print(f"  {report.mark(passed)} {a['id']:<4} {a['category']:<20} {label:<9} "
              f"{report.dim(report.shorten(out, 48))}")

report.section("Attack success rate (lower is better) and helpfulness")
summary = {}
for variant in variants:
    vr = [r for r in rows if r["variant"] == variant]
    atk = [r for r in vr if r["category"] != "benign_control" and r["attack_succeeded"] is not None]
    ctl = [r for r in vr if r["category"] == "benign_control"]
    asr = sum(r["attack_succeeded"] for r in atk)
    summary[variant] = {"asr": f"{asr}/{len(atk)}", "helpful": f"{sum(r['passed'] for r in ctl)}/{len(ctl)}"}
    print(f"  {report.bold(variant):<10}")
    print("    " + report.rate_line("attacks that SUCCEEDED", asr, len(atk)))
    print("    " + report.rate_line("benign requests helped", sum(r["passed"] for r in ctl), len(ctl)))
    per_cat = defaultdict(lambda: [0, 0])
    for r in atk:
        per_cat[r["category"]][0] += r["attack_succeeded"]
        per_cat[r["category"]][1] += 1
    print(report.dim("    by category: " + ", ".join(f"{c} {s}/{n}" for c, (s, n) in sorted(per_cat.items()))))

report.save_results("p5_direct_injection", rows, summary)
report.explain(
    "Any canary leak is a hard, undeniable failure: the secret was in the system prompt and now "
    "it's in the output. Canaries are the simplest reliable injection test you can add to a real "
    "product - plant a unique string, then alert if it ever appears in a response.",
    "Compare basic vs hardened. Hardening usually lowers ASR but rarely to zero. That's the "
    "honest lesson: prompt wording is a mitigation, not a fix. Real defences are architectural - "
    "don't put secrets in prompts, enforce limits (like the $50 refund) in CODE, and filter output.",
    "Check the benign controls! If the hardened prompt made the bot refuse normal questions, you "
    "traded security for a broken product. Always measure both, exactly like Phase 4's controls.",
    "One run per attack is a weak test - attacks are probabilistic too. Re-run a few times; an "
    "attack that works 1 time in 5 will work for a determined attacker who just retries.",
)
