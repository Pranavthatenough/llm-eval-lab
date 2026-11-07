"""The lab launcher - your map of the course.

    python lab.py                 show every exercise, in order
    python lab.py run 2.1         run exercise 2.1
    python lab.py run 4           run every exercise in phase 4
    python lab.py next            run the first exercise you haven't run yet

Every script can also be run directly, e.g. python phases/02_deterministic_checks/01_run_checks.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

COURSE = [
    ("0", "Setup", [
        ("0.1", "00_setup/check_setup.py", "Check Python, Ollama, models and config", None)]),
    ("1", "Basics: what you're actually testing", [
        ("1.1", "01_basics/01_first_call.py", "One call with nothing hidden", None),
        ("1.2", "01_basics/02_nondeterminism.py", "Same input, different output", "p1_nondeterminism"),
        ("1.3", "01_basics/03_first_eval.py", "The metric decides the result", "p1_first_eval"),
        ("1.4", "01_basics/04_playground.py", "Exploratory testing playground", "p1_playground")]),
    ("2", "Deterministic checks", [
        ("2.1", "02_deterministic_checks/01_run_checks.py", "Data-driven property checks", "p2_checks"),
        ("2.2", "02_deterministic_checks/02_structured_output.py", "Valid JSON is not correct JSON", "p2_structured_output"),
        ("2.3", "02_deterministic_checks/03_flakiness.py", "Measure flakiness instead of hiding it", "p2_flakiness")]),
    ("3", "LLM as a judge", [
        ("3.1", "03_llm_as_judge/01_judge_vs_humans.py", "Calibrate the judge against humans", "p3_judge_vs_humans"),
        ("3.2", "03_llm_as_judge/02_judge_biases.py", "Position, verbosity and consistency bias", "p3_judge_biases")]),
    ("4", "Hallucination testing", [
        ("4.1", "04_hallucination/01_fabrication_probe.py", "Questions with no true answer", "p4_fabrication"),
        ("4.2", "04_hallucination/02_grounded_faithfulness.py", "Faithfulness to a given context", "p4_faithfulness"),
        ("4.3", "04_hallucination/03_self_consistency.py", "Guessing models disagree with themselves", "p4_self_consistency")]),
    ("5", "Prompt injection", [
        ("5.1", "05_prompt_injection/01_direct_injection.py", "Attack a support bot, basic vs hardened", "p5_direct_injection"),
        ("5.2", "05_prompt_injection/02_indirect_injection.py", "Attacks hidden inside data", "p5_indirect_injection")]),
    ("6", "RAG evaluation", [
        ("6.1", "06_rag_evaluation/01_retrieval_eval.py", "Test the retriever on its own", "p6_retrieval"),
        ("6.2", "06_rag_evaluation/02_end_to_end_eval.py", "End to end + where it broke", "p6_end_to_end")]),
    ("7", "Agent scoring", [
        ("7.1", "07_agent_scoring/01_watch_agent.py", "Watch an agent think and act", None),
        ("7.2", "07_agent_scoring/02_score_agent.py", "Score outcome, trajectory and safety", "p7_agent_scores")]),
    ("8", "Bonus: CI regression gate", [
        ("8.1", "08_bonus_ci_regression/test_llm_regression.py", "Evals as pytest quality gates", None)]),
]


def done(result_prefix):
    return bool(result_prefix) and any(RESULTS.glob(f"{result_prefix}_*.json"))


def show():
    print("\nLLM Eval Lab - course map   (x = you have saved results for it)\n")
    for num, title, exercises in COURSE:
        print(f"Phase {num}: {title}")
        for ex_id, _, desc, prefix in exercises:
            tick = "x" if done(prefix) else " "
            print(f"   [{tick}] {ex_id:<4} {desc}")
        print()
    print("Run one:  python lab.py run 1.1     Run a phase:  python lab.py run 2     Next:  python lab.py next\n")


def run(path, extra=()):
    full = ROOT / "phases" / path
    print(f"\n>>> {full.relative_to(ROOT)}")
    if path.endswith("test_llm_regression.py"):
        cmd = [sys.executable, "-m", "pytest", str(full), "-v", *extra]
    else:
        cmd = [sys.executable, str(full), *extra]
    return subprocess.call(cmd, cwd=ROOT)


def main(argv):
    if not argv or argv[0] in ("list", "ls", "-h", "--help"):
        return show()
    all_ex = [ex for _, _, exs in COURSE for ex in exs]
    if argv[0] == "next":
        for ex_id, path, _, prefix in all_ex:
            if prefix and not done(prefix):
                return run(path)
        print("You've run every scored exercise. Try the 'Break it' challenges in each phase README!")
        return 0
    if argv[0] == "run" and len(argv) >= 2:
        key, extra = argv[1], argv[2:]
        matches = [ex for ex in all_ex if ex[0] == key or ex[0].split(".")[0] == key]
        if not matches:
            sys.exit(f"No exercise or phase '{key}'. Run `python lab.py` to see the list.")
        code = 0
        for _, path, _, _ in matches:
            code = run(path, extra) or code
        return code
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
