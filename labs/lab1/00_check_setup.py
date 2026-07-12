"""
Environment check script — run this first, before any other lab.
Verifies: Python version, required packages, Ollama connectivity and
model, and the HuggingFace token (optional, only needed for the
HuggingFace Inference API path).

Usage:
    python 00_check_setup.py
"""

import importlib.util
import os
import sys
import urllib.request
import urllib.error

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

OK = "\033[92m✅\033[0m"
FAIL = "\033[91m❌\033[0m"
WARN = "\033[93m⚠️ \033[0m"

results = []  # (passed: bool, message: str)


def check(label, passed, detail=""):
    icon = OK if passed else FAIL
    line = f"{icon} {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    results.append(passed)


def warn(label, detail=""):
    line = f"{WARN} {label}"
    if detail:
        line += f" — {detail}"
    print(line)


print("=" * 60)
print("labs/ environment check — Session 2: Tool Calling")
print("=" * 60)

# 1) Python version (we ask for 3.11+, but cap at 3.13 since some
#    ML packages don't yet ship wheels for the very latest Python)
py_version = sys.version_info
py_ok = (3, 11) <= (py_version.major, py_version.minor) <= (3, 13)
check(
    "Python 3.11 - 3.13",
    py_ok,
    f"found {py_version.major}.{py_version.minor}.{py_version.micro}"
    + ("" if py_ok else " — Python 3.12 is recommended for best compatibility with chromadb/torch"),
)

# 2) Required packages
required_packages = [
    ("langchain", "langchain"),
    ("langchain_community", "langchain-community"),
    ("langchain_huggingface", "langchain-huggingface"),
    ("langchain_ollama", "langchain-ollama"),
    ("langgraph", "langgraph"),
    ("chromadb", "chromadb"),
    ("sentence_transformers", "sentence-transformers"),
    ("pydantic", "pydantic"),
    ("dotenv", "python-dotenv"),
    ("wikipediaapi", "wikipedia-api"),
]
for module_name, pip_name in required_packages:
    installed = importlib.util.find_spec(module_name) is not None
    check(f"package {pip_name}", installed, "" if installed else f"run: pip install {pip_name}")

# 3) Is Ollama running?
ollama_running = False
try:
    with urllib.request.urlopen("http://localhost:11434/api/version", timeout=3) as resp:
        ollama_running = resp.status == 200
except (urllib.error.URLError, OSError):
    ollama_running = False
check(
    "Ollama service running on localhost:11434",
    ollama_running,
    "" if ollama_running else "run: ollama serve (or open the Ollama app)",
)

# 4) Is a tool-calling-capable model pulled locally?
tool_capable_models = ["qwen2.5", "llama3.1", "llama3.2", "mistral-nemo", "firefunction"]
if ollama_running:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as resp:
            import json as _json

            tags = _json.loads(resp.read())
            model_names = [m["name"] for m in tags.get("models", [])]
            found = [m for m in model_names if any(m.startswith(t) for t in tool_capable_models)]
            check(
                "A tool-calling-capable model is pulled in Ollama",
                bool(found),
                f"found: {', '.join(found)}" if found else "run: ollama pull qwen2.5:7b",
            )
    except (urllib.error.URLError, OSError):
        check("A tool-calling-capable model is pulled in Ollama", False, "could not reach Ollama")
else:
    check("A tool-calling-capable model is pulled in Ollama", False, "start Ollama first")

# 5) HuggingFace token (optional — only needed for the HuggingFace path)
hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
if hf_token:
    check("HUGGINGFACEHUB_API_TOKEN is set", True)
else:
    warn(
        "HUGGINGFACEHUB_API_TOKEN is not set",
        "expected if you're using Ollama locally only — only required for the HuggingFace fallback path (see SETUP.md, section 5)",
    )

# 6) Google API packages (optional — only needed for 05_gmail_calendar_agent.py)
google_packages = [
    ("googleapiclient", "google-api-python-client"),
    ("google_auth_oauthlib", "google-auth-oauthlib"),
]
if all(importlib.util.find_spec(m) is not None for m, _ in google_packages):
    check("Google API packages (optional, for 05_gmail_calendar_agent.py)", True)
else:
    warn(
        "Google API packages not installed",
        "only needed for 05_gmail_calendar_agent.py — run: pip install -r requirements.txt, see GOOGLE_SETUP.md",
    )

# 7) peft (optional — only needed for 06_fine_tuning_demo.py; torch and
#    transformers are already required above via sentence-transformers)
if importlib.util.find_spec("peft") is not None:
    check("peft (optional, for 06_fine_tuning_demo.py)", True)
else:
    warn(
        "peft not installed",
        "only needed for 06_fine_tuning_demo.py — run: pip install -r requirements.txt",
    )

print("=" * 60)
passed_count = sum(results)
total_count = len(results)
if all(results):
    print(f"{OK} All core checks passed ({passed_count}/{total_count}). Ready to start 01_hello_world.py")
else:
    print(f"{FAIL} {total_count - passed_count} of {total_count} checks failed. Review the messages above and SETUP.md")
    sys.exit(1)
