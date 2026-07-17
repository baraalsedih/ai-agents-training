"""Central configuration for the unified Session 7 system.

This file only holds paths and constants for labs/system/ itself. It does
NOT redefine anything already owned by Sessions 3-6 (model names, chunk
size, categories, judge model, prices, ...) -- run.py, dashboard.py, and
backup.py import each session's own config/lab_config directly for that,
exactly as Session 4-6 already import Session 3's config.py by sibling
path instead of copying its values.

Named system_config.py, not config.py: Sessions 3-5 already import their
own config.py by the bare module name "config" via sys.path insertion,
and Python caches modules in sys.modules by that bare name -- a second
top-level module also named "config" here would silently collide with
theirs instead of loading side by side. This is the exact same reasoning
labs/session6/lab_config.py documents for itself.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LABS_DIR = BASE_DIR.parent

# Sibling lab folders this system imports from directly (never copies from).
SESSION3_DIR = LABS_DIR / "session3"   # knowledge base: config, ingest, ask, report
SESSION4_DIR = LABS_DIR / "session4"   # source-analysis agent (reached via session5's subprocess wrapper, not imported directly)
SESSION5_DIR = LABS_DIR / "session5"   # agents/: source_analyst, consistency_auditor, researcher
SESSION6_DIR = LABS_DIR / "session6"   # tracing, evaluate, cost_report, lab_config

# evaluate.py takes 30-45 minutes and does its own argparse handling, so
# run.py shells out to it as a subprocess (in Session 6's own venv) rather
# than importing and re-entering its main() in-process.
SESSION6_VENV_PYTHON = SESSION6_DIR / "venv" / "bin" / "python3"

# New documents land here; ingest moves each one to processed/ once the
# source-analysis agent has finished with it (approved or rejected).
INBOX_DIR = BASE_DIR / "inbox"
INBOX_PROCESSED_DIR = INBOX_DIR / "processed"

# Generated dashboard -- a static file, regenerated on demand, not a server.
DASHBOARD_PATH = BASE_DIR / "dashboard.html"

# Where backup.py writes its dated archives.
BACKUP_DIR = BASE_DIR / "backups"
