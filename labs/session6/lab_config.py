"""Central configuration for the session 6 evaluation/cost/observability lab.

All tunable values live here so evaluate.py, cost_report.py, and judge.py
never hardcode a path, a model name, or a price.

Named lab_config.py, not config.py: Sessions 3-5 already import their own
config.py by bare module name via sys.path insertion (see judge.py's
import below), and Python caches modules in sys.modules by that bare
name -- a second top-level module also named "config" would silently
shadow theirs instead of loading side by side, since both would resolve
to the same sys.modules["config"] entry. A distinct name avoids the clash
entirely.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

GOLDEN_SET_PATH = BASE_DIR / "golden_set.yaml"
EVAL_REPORTS_DIR = BASE_DIR / "eval_reports"
BASELINE_PATH = EVAL_REPORTS_DIR / "baseline.json"
TRACES_DIR = BASE_DIR / "traces"

# Same local model the rest of the system already uses (see
# labs/session3/config.py). Pinning ONE fixed judge model, kept identical
# run over run, is what makes scores comparable across evaluate.py runs --
# swapping the judge model invalidates comparisons against an older
# baseline.json, same as changing CHAT_MODEL invalidates the knowledge base.
JUDGE_MODEL = "llama3.1:8b"

# A question's dimension average strictly below this is flagged in the
# report as a candidate for human review (see handbook chapter 4).
LOW_SCORE_THRESHOLD = 3.0

# ------------------------------------------------------------------------
# Placeholder cloud pricing -- USD per 1,000 tokens. These are illustrative
# placeholders for estimating "what would this cost on a cloud model
# instead of running locally", NOT live prices. Cloud model pricing
# changes often; check the provider's current pricing page before using
# these numbers for a real budgeting decision. Edit the two lines below to
# reprice against any model you're actually considering.
# ------------------------------------------------------------------------
CLOUD_PRICE_PER_1K_INPUT_TOKENS_USD = 0.003
CLOUD_PRICE_PER_1K_OUTPUT_TOKENS_USD = 0.015
