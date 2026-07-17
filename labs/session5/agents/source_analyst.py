"""Source-analysis agent wrapper -- Session 5.

Wraps Session 4's already-built source-analysis agent (labs/session4/
agent.py) as one callable step inside the Session 5 team, without copying
or re-implementing any of its graph, nodes, or human checkpoints.

Usage (standalone, same as calling Session 4 directly):
    python3 source_analyst.py <path-to-file>
"""

import subprocess
import sys
import time
from pathlib import Path

SESSION4_DIR = Path(__file__).resolve().parent.parent.parent / "session4"
SESSION4_AGENT = SESSION4_DIR / "agent.py"
SESSION4_VENV_PYTHON = SESSION4_DIR / "venv" / "bin" / "python3"

# session6: tracing added -- labs/session6/ is a sibling directory, not an
# installed package, same import convention this lab already uses for
# labs/session3/.
SESSION6_DIR = Path(__file__).resolve().parent.parent.parent / "session6"
sys.path.insert(0, str(SESSION6_DIR))
import tracing  # noqa: E402


def _resolve_file_path(file_path: str) -> Path:
    """Accepts an absolute path, a path relative to the caller's working
    directory, a path relative to labs/session4/, or a bare filename that
    lives in labs/session4/incoming/ -- whichever the supervisor's routing
    step happened to extract from the user's request."""
    candidates = [
        Path(file_path),
        Path.cwd() / file_path,
        SESSION4_DIR / file_path,
        SESSION4_DIR / "incoming" / file_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return Path(file_path)  # let Session 4's own agent.py report "file not found"


def run_source_analyst(file_path: str) -> dict:
    """Runs Session 4's agent.py on one document, interactively -- its
    human-review and approval prompts appear directly on this same
    terminal, nothing is silently auto-approved on the user's behalf.

    Design note -- subprocess, not a LangGraph subgraph: Session 4's graph
    pauses with interrupt() and resumes through its OWN SqliteSaver
    checkpointer (labs/session4/checkpoints.sqlite), keyed by a thread_id
    derived from the file name. Nesting it as a true subgraph here would
    require this team's own graph to share that exact checkpointer/
    thread-id scheme and propagate a resume Command() through two nested
    interrupt() layers -- solvable, but it would tightly couple Session 5's
    supervisor to Session 4's internal persistence details for no benefit
    in a single-process CLI lab. A subprocess call keeps Session 4 fully
    independent (it still runs standalone, completely unchanged) while
    still reusing 100% of its real graph, nodes, and human checkpoints --
    not a re-implementation of any of it.
    """
    resolved = _resolve_file_path(file_path)
    python_executable = str(SESSION4_VENV_PYTHON) if SESSION4_VENV_PYTHON.exists() else sys.executable

    # flush=True: this print precedes a subprocess.run() call that inherits
    # stdout directly -- without an explicit flush, the child's unbuffered
    # output can appear before this line when stdout isn't a real terminal
    # (e.g. redirected to a file or piped), making the transcript look
    # out of order even though this line genuinely printed first.
    print(f"🎯 Supervisor: handing off to the source-analysis agent (Session 4) for {resolved.name}...", flush=True)
    # session6: tracing added -- Session 4 runs in its own OS process with
    # its own checkpointer (see the docstring above), so nothing inside it
    # can be traced from here without modifying Session 4. One honest
    # black-box event (start/end/duration) is logged instead of pretending
    # to see inside it -- this same passthrough-or-open pattern as the
    # other two agents means it also opens its own operation when this
    # module runs standalone.
    with tracing.operation("analyze_document", {"file_path": str(resolved)}):
        start = time.monotonic()
        result = subprocess.run([python_executable, str(SESSION4_AGENT), str(resolved)], cwd=str(SESSION4_DIR))
        tracing.log_subprocess(agent="source_analyst", target="labs/session4/agent.py", duration_sec=time.monotonic() - start, return_code=result.returncode)

    return {
        "file_path": str(resolved),
        "return_code": result.returncode,
        "message": (
            f"Source-analysis agent finished for {resolved.name} (exit code {result.returncode}). "
            f"See labs/session4/reports/ for the dated analysis report."
        ),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 source_analyst.py <path-to-file>")
        sys.exit(1)
    result = run_source_analyst(sys.argv[1])
    print(result["message"])
    sys.exit(result["return_code"])


if __name__ == "__main__":
    main()
