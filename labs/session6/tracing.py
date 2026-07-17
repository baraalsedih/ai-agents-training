"""Lightweight JSONL tracer -- Session 6.

Records what the Session 5 team actually did for every request: which
destination the supervisor routed to, every LLM call (agent, purpose,
prompt preview, token counts, duration), every retrieval, and every
routing/review decision -- one JSON object per line, appended to
traces/trace_<date>.jsonl.

Design: operations nest transparently through a contextvar. Whichever
function runs first (supervisor.route() when called through team.py, or
run_research()/run_consistency_check() when their module is run standalone)
opens the operation; every function called underneath it -- however deep,
across however many modules -- reuses the same operation_id automatically.
No Tracer object needs to be threaded through function signatures or
TeamState. This is what keeps the Session 5 integration to a few
call-site edits instead of a rewrite.

No external dependencies, no server -- just a directory of append-only
text files. Read them back with view_traces.py or cost_report.py.
"""

import json
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

TRACES_DIR = Path(__file__).resolve().parent / "traces"

_current_operation: ContextVar[Optional[str]] = ContextVar("_current_operation", default=None)


def _trace_file() -> Path:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    return TRACES_DIR / f"trace_{datetime.now().strftime('%Y-%m-%d')}.jsonl"


def _write(event: dict) -> None:
    event["ts"] = datetime.now(timezone.utc).isoformat()
    with open(_trace_file(), "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


@contextmanager
def operation(kind: str, meta: Optional[dict] = None):
    """Opens a traced operation, or -- if one is already active -- passes
    through transparently (nested calls share the parent's operation_id).
    Only the call that actually opened the operation writes operation_end,
    so a full request/response cycle across several agents lands as one
    contiguous trace."""
    existing = _current_operation.get()
    if existing is not None:
        yield existing
        return

    operation_id = uuid.uuid4().hex[:12]
    token = _current_operation.set(operation_id)
    start = time.monotonic()
    _write({"operation_id": operation_id, "event": "operation_start", "kind": kind, "meta": meta or {}})
    try:
        yield operation_id
    finally:
        _write({"operation_id": operation_id, "event": "operation_end", "kind": kind, "duration_sec": round(time.monotonic() - start, 3)})
        _current_operation.reset(token)


def _extract_usage(prompt: str, response) -> tuple:
    """Prefers Ollama's own token counts (exposed by langchain-ollama as
    `response.usage_metadata` on a plain AIMessage). Structured-output
    calls (llm.with_structured_output(Model).invoke(...), used throughout
    Session 5) return the parsed Pydantic object directly with no usage
    metadata attached -- for those we fall back to a chars/4 estimate,
    which is only meant to be accurate enough for relative comparison
    between operations, not billing-grade precision."""
    usage = getattr(response, "usage_metadata", None)
    if usage:
        return usage.get("input_tokens", 0), usage.get("output_tokens", 0), "ollama_usage"
    response_text = getattr(response, "content", None) or str(response)
    return len(prompt) // 4, len(response_text) // 4, "estimated_chars/4"


def traced_llm_call(llm, prompt: str, *, agent: str, purpose: str):
    """Drop-in replacement for `llm.invoke(prompt)` (or
    `structured_llm.invoke(prompt)`) that logs one llm_call event to the
    currently active operation and returns the exact same response the
    plain .invoke() call would have returned. A failed call (e.g. the
    local model producing unparseable structured output) is logged too,
    with tokens_in/out as null and an "error" field -- otherwise a crash
    would vanish from the trace instead of explaining the gap, which
    defeats the point of tracing a failure in the first place."""
    start = time.monotonic()
    try:
        response = llm.invoke(prompt)
    except Exception as exc:
        _write(
            {
                "operation_id": _current_operation.get(),
                "event": "llm_call",
                "agent": agent,
                "purpose": purpose,
                "prompt_preview": prompt[:200],
                "prompt_chars": len(prompt),
                "tokens_in": None,
                "tokens_out": None,
                "tokens_source": "n/a (call failed)",
                "duration_sec": round(time.monotonic() - start, 3),
                "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            }
        )
        raise

    duration = round(time.monotonic() - start, 3)
    tokens_in, tokens_out, tokens_source = _extract_usage(prompt, response)

    _write(
        {
            "operation_id": _current_operation.get(),
            "event": "llm_call",
            "agent": agent,
            "purpose": purpose,
            "prompt_preview": prompt[:200],
            "prompt_chars": len(prompt),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_source": tokens_source,
            "duration_sec": duration,
        }
    )
    return response


def log_retrieval(*, agent: str, query: str, k: int, sources: list, category_filter: Optional[str] = None) -> None:
    _write(
        {
            "operation_id": _current_operation.get(),
            "event": "retrieval",
            "agent": agent,
            "query": query,
            "k": k,
            "category_filter": category_filter,
            "sources": sources,
        }
    )


def log_decision(*, node: str, choice: str, extra: Optional[dict] = None) -> None:
    _write({"operation_id": _current_operation.get(), "event": "decision", "node": node, "choice": choice, "extra": extra or {}})


def log_subprocess(*, agent: str, target: str, duration_sec: float, return_code: int) -> None:
    """For steps Session 6 cannot see inside of, like Session 4's
    source-analysis agent (called as a separate OS process by
    agents/source_analyst.py) -- one honest black-box event instead of
    pretending we traced something we didn't."""
    _write(
        {
            "operation_id": _current_operation.get(),
            "event": "subprocess_call",
            "agent": agent,
            "target": target,
            "duration_sec": round(duration_sec, 3),
            "return_code": return_code,
        }
    )


def read_events(days: Optional[int] = None) -> list:
    """Reads all trace files (or just the most recent `days` of them),
    returned in file order. Shared by view_traces.py and cost_report.py so
    both tools parse the exact same JSONL format the same way."""
    if not TRACES_DIR.exists():
        return []
    files = sorted(TRACES_DIR.glob("trace_*.jsonl"))
    if days:
        files = files[-days:]
    events = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def group_by_operation(events: list) -> dict:
    """{operation_id: [events...]} preserving order, for view_traces.py's
    single-trace view and cost_report.py's per-operation aggregation."""
    grouped = {}
    for e in events:
        grouped.setdefault(e["operation_id"], []).append(e)
    return grouped


def operation_kind(op_events: list) -> str:
    """team.py's run_once() opens every request generically as "request"
    (the destination isn't known yet) -- for that case specifically, the
    supervisor's route() decision is the real, more specific kind. Any
    other opener (run_research()/run_consistency_check() standalone,
    evaluate.py's "golden_eval", judge.py's "evaluation") already knows
    exactly what it is and is kept as-is, even if a route() decision
    happens to occur inside it too -- e.g. evaluate.py's operations nest a
    route decision AND a judge call under one "golden_eval" operation,
    and must stay "golden_eval" so evaluation cost isn't silently
    double-counted as production "research" cost in cost_report.py."""
    start_kind = None
    for e in op_events:
        if e["event"] == "operation_start":
            start_kind = e["kind"]
            break
    if start_kind and start_kind != "request":
        return start_kind
    for e in op_events:
        if e["event"] == "decision" and e["node"] == "route":
            return e["choice"]
    return start_kind or "unknown"
