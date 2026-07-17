"""Trace viewer -- Session 6.

Two modes:
    python3 view_traces.py                 -- lists recent operations, newest first
    python3 view_traces.py <operation_id>   -- prints one operation's full event
                                                tree (accepts a unique id prefix)

This is the tool for the diagnosis workflow in chapter 6 of the handbook:
find a weak question in an eval report, copy its operation_id (or just its
golden_id, e.g. "q01"), and open the full trace to see exactly which step
-- routing, retrieval, or composition -- produced the weak answer.

Usage:
    python3 view_traces.py
    python3 view_traces.py a1b2c3d4e5f6
    python3 view_traces.py q01              # matches by golden_id in meta

Everything runs locally -- no external API calls, no dependency on Ollama
even being up (this only reads already-recorded trace files).
"""

import sys

import tracing

EVENT_LABELS_AR = {
    "operation_start": "بداية العملية",
    "operation_end": "نهاية العملية",
    "llm_call": "استدعاء LLM",
    "retrieval": "استرجاع",
    "decision": "قرار",
    "subprocess_call": "استدعاء عملية فرعية",
}


def list_operations(events: list, limit: int = 20) -> None:
    grouped = tracing.group_by_operation(events)
    rows = []
    for op_id, op_events in grouped.items():
        start = next((e for e in op_events if e["event"] == "operation_start"), None)
        end = next((e for e in op_events if e["event"] == "operation_end"), None)
        kind = tracing.operation_kind(op_events)
        llm_call_count = sum(1 for e in op_events if e["event"] == "llm_call")
        meta = start.get("meta", {}) if start else {}
        label = meta.get("question") or meta.get("user_request") or meta.get("file_path") or meta.get("category_filter") or ""
        rows.append(
            {
                "operation_id": op_id,
                "ts": start["ts"] if start else "?",
                "kind": kind,
                "llm_call_count": llm_call_count,
                "duration_sec": end["duration_sec"] if end else None,
                "label": str(label)[:50],
            }
        )
    rows.sort(key=lambda r: r["ts"], reverse=True)

    if not rows:
        print("⚠️  لا توجد عمليات مسجَّلة بعد.")
        return

    print(f"📋 آخر {min(limit, len(rows))} عملية (من إجمالي {len(rows)}):\n")
    print(f"{'المعرّف':<14}{'النوع':<18}{'استدعاءات':<12}{'الزمن (ث)':<12}{'الوصف'}")
    print("-" * 100)
    for r in rows[:limit]:
        duration = f"{r['duration_sec']:.1f}" if r["duration_sec"] is not None else "?"
        print(f"{r['operation_id']:<14}{r['kind']:<18}{r['llm_call_count']:<12}{duration:<12}{r['label']}")
    print("\nلعرض شجرة عملية كاملة: python3 view_traces.py <المعرّف أو جزء منه>")


def _find_operation(events: list, query: str):
    grouped = tracing.group_by_operation(events)
    # exact/prefix match on operation_id first
    matches = {op_id: ev for op_id, ev in grouped.items() if op_id.startswith(query)}
    if matches:
        return matches
    # fall back to matching a golden_id (e.g. "q01") inside operation_start meta
    matches = {}
    for op_id, ev in grouped.items():
        start = next((e for e in ev if e["event"] == "operation_start"), None)
        if start and start.get("meta", {}).get("golden_id") == query:
            matches[op_id] = ev
    return matches


def show_operation(events: list, query: str) -> None:
    matches = _find_operation(events, query)
    if not matches:
        print(f"⚠️  لم يُعثر على عملية تطابق: {query}")
        return
    if len(matches) > 1:
        print(f"⚠️  عدة عمليات تطابق '{query}': {', '.join(matches.keys())}")
        print("   حدّد معرّفًا أدق.")
        return

    op_id, op_events = next(iter(matches.items()))
    kind = tracing.operation_kind(op_events)
    print(f"🔎 العملية: {op_id}  (النوع: {kind})\n")
    print("=" * 100)
    for e in op_events:
        label = EVENT_LABELS_AR.get(e["event"], e["event"])
        ts = e.get("ts", "")
        if e["event"] == "operation_start":
            print(f"[{ts}] ▶️  {label} -- meta: {e.get('meta', {})}")
        elif e["event"] == "operation_end":
            print(f"[{ts}] ⏹️  {label} -- المدة الكلية: {e.get('duration_sec')} ثانية")
        elif e["event"] == "llm_call":
            print(
                f"[{ts}]   🤖 {label} -- الوكيل: {e['agent']} | الغرض: {e['purpose']} | "
                f"توكنز: {e['tokens_in']} دخل / {e['tokens_out']} خرج ({e['tokens_source']}) | الزمن: {e['duration_sec']} ث"
            )
            if e.get("error"):
                print(f"             ❌ فشل الاستدعاء: {e['error']}")
            print(f"             معاينة الطلب: {e['prompt_preview'][:120]}...")
        elif e["event"] == "retrieval":
            sources = ", ".join(s.get("source", "?") for s in e.get("sources", []))
            print(f"[{ts}]   📚 {label} -- الوكيل: {e['agent']} | الاستعلام: \"{e['query']}\" | k={e['k']} | المصادر: {sources or '(لا شيء)'}")
        elif e["event"] == "decision":
            print(f"[{ts}]   🧭 {label} -- العقدة: {e['node']} | الاختيار: {e['choice']}" + (f" | {e['extra']}" if e.get("extra") else ""))
        elif e["event"] == "subprocess_call":
            print(f"[{ts}]   📦 {label} -- الوكيل: {e['agent']} | الهدف: {e['target']} | الزمن: {e['duration_sec']} ث | كود الخروج: {e['return_code']}")
        else:
            print(f"[{ts}]   {label} -- {e}")
    print("=" * 100)


def main():
    events = tracing.read_events()
    if len(sys.argv) > 1:
        show_operation(events, sys.argv[1])
    else:
        list_operations(events)


if __name__ == "__main__":
    main()
