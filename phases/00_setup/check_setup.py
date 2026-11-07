"""Phase 0 - Is everything wired up?

Run:  python phases/00_setup/check_setup.py

Checks, in order: Python version, packages, config file, provider reachable,
models downloaded, one real chat call per role, and one embedding call.
Each failure prints the exact command to fix it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `import llmeval` work without installing

OK, BAD, WARN = "  [ok]  ", "  [!!]  ", "  [--]  "
problems = 0


def step(ok: bool, msg: str, fix: str = "", warn_only: bool = False) -> bool:
    global problems
    if ok:
        print(OK + msg)
    else:
        print((WARN if warn_only else BAD) + msg)
        if fix:
            for line in fix.splitlines():
                print("          -> " + line)
        if not warn_only:
            problems += 1
    return ok


print("\nLLM Eval Lab - setup check\n" + "-" * 40)

step(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}", "Install Python 3.10 or newer.")

try:
    import requests  # noqa: F401
    import yaml  # noqa: F401
    step(True, "Packages requests + PyYAML installed")
except ImportError as e:
    step(False, f"Missing package: {e.name}", "pip install -r requirements.txt")
    sys.exit(1)

from llmeval import LLMError, get_client, load_config  # noqa: E402

try:
    cfg = load_config()
    step(True, f"Config loaded from {cfg.source.name}")
except Exception as e:  # noqa: BLE001
    step(False, f"Config problem: {e}", "Check config.yaml for typos (YAML is indentation-sensitive).")
    sys.exit(1)

for role in ("target", "judge", "embeddings"):
    mc = cfg.role(role)
    print(f"\n{role.upper()}  ->  {mc.provider} / {mc.model}")
    client = get_client(role)
    if mc.provider == "mock":
        step(False, "Using the MOCK provider (offline fake model)",
             "Fine for checking plumbing. Set provider: ollama in config.yaml for real results.",
             warn_only=True)
    try:
        models = client.list_models()
        where = "offline mock" if mc.provider == "mock" else mc.base_url
        step(True, f"Provider reachable: {where} ({len(models)} models available)")
        if mc.provider == "ollama":
            have = any(m == mc.model or m == f"{mc.model}:latest" or m.split(":")[0] == mc.model for m in models)
            step(have, f"Model '{mc.model}' is downloaded", f"ollama pull {mc.model}")
            if not have:
                continue
    except LLMError as e:
        step(False, "Cannot reach the provider", str(e))
        continue

    try:
        if role == "embeddings":
            vecs = client.embed(["hello world"])
            step(len(vecs) == 1 and len(vecs[0]) > 0, f"Embedding call works (vector size {len(vecs[0])})")
        else:
            res = client.chat([{"role": "user", "content": "Reply with the single word: ready"}])
            step(bool(res.text.strip()), f"Chat call works: {res.text.strip()[:40]!r}  {res.usage_line()}")
    except LLMError as e:
        step(False, f"{role} call failed", str(e),
             warn_only=(role == "embeddings"))
        if role == "embeddings":
            print("          -> Phase 6 can still run: set rag.retriever: keyword in config.yaml")

print("\n" + "-" * 40)
if problems == 0:
    print("All good. Start with:  python phases/01_basics/01_first_call.py")
else:
    print(f"{problems} problem(s) found. Fix the items marked [!!] and run this again.")
sys.exit(1 if problems else 0)
