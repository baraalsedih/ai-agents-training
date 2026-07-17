"""Cost report -- Session 6.

Reads every trace in traces/ and turns it into two Markdown tables:
one macro view (cost per user-facing operation type -- research,
consistency_check, analyze_document, direct_answer) and one micro view
(cost per agent + purpose -- which specific LLM call is actually the
expensive one). Both report real, measured local numbers (call counts,
tokens, seconds) plus a placeholder cloud-dollar estimate from
lab_config.py, in decision language a non-programmer founder can act on.

Evaluation cost (golden_eval / evaluation operation kinds -- i.e. what
evaluate.py and judge.py themselves cost to run) is reported in its own
section, separate from production usage, so it's never silently mixed
into "what does asking a real question cost" numbers.

Usage:
    python3 cost_report.py

Everything runs locally -- no external API calls, no dependency on
Ollama even being up (this only reads already-recorded trace files).
"""

from collections import defaultdict
from datetime import date
from pathlib import Path

import lab_config as config
import tracing

PRODUCTION_KINDS = {"research", "consistency_check", "analyze_document", "direct_answer"}
EVALUATION_KINDS = {"golden_eval", "evaluation"}


def _cloud_cost_usd(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1000) * config.CLOUD_PRICE_PER_1K_INPUT_TOKENS_USD + (tokens_out / 1000) * config.CLOUD_PRICE_PER_1K_OUTPUT_TOKENS_USD


def summarize_operations(events: list) -> dict:
    """{kind: [operation_summary, ...]}"""
    grouped = tracing.group_by_operation(events)
    by_kind = defaultdict(list)
    for op_events in grouped.values():
        kind = tracing.operation_kind(op_events)
        llm_calls = [e for e in op_events if e["event"] == "llm_call"]
        subprocess_calls = [e for e in op_events if e["event"] == "subprocess_call"]
        end = next((e for e in op_events if e["event"] == "operation_end"), None)
        by_kind[kind].append(
            {
                "llm_call_count": len(llm_calls),
                # tokens_in/out are null on a failed call (tracing.py logs the
                # failure itself but has no response to count tokens from) --
                # `or 0` keeps a crashed call counted in llm_call_count without
                # breaking the sum.
                "tokens_in": sum(e["tokens_in"] or 0 for e in llm_calls),
                "tokens_out": sum(e["tokens_out"] or 0 for e in llm_calls),
                "duration_sec": end["duration_sec"] if end else sum(e["duration_sec"] for e in llm_calls),
                "subprocess_count": len(subprocess_calls),
            }
        )
    return by_kind


def summarize_by_agent(events: list) -> dict:
    """{(agent, purpose): [llm_call event, ...]} across ALL operations,
    regardless of kind -- the micro view."""
    by_agent = defaultdict(list)
    for e in events:
        if e["event"] == "llm_call":
            by_agent[(e["agent"], e["purpose"])].append(e)
    return by_agent


def _avg(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def render_kind_table(by_kind: dict, kinds: set, title: str, notes: str = "") -> list:
    lines = [f"## {title}", ""]
    if notes:
        lines.append(notes)
        lines.append("")
    relevant = {k: v for k, v in by_kind.items() if k in kinds}
    if not relevant:
        lines.append("لا توجد عمليات مسجَّلة من هذا النوع بعد.")
        lines.append("")
        return lines

    lines.append("| نوع العملية | عدد العمليات | متوسط استدعاءات LLM | متوسط توكنز (دخل/خرج) | متوسط الزمن (ثانية) | تكلفة سحابية افتراضية/عملية |")
    lines.append("|---|---|---|---|---|---|")
    for kind, ops in sorted(relevant.items(), key=lambda kv: -len(kv[1])):
        n = len(ops)
        avg_calls = _avg([o["llm_call_count"] for o in ops])
        avg_in = _avg([o["tokens_in"] for o in ops])
        avg_out = _avg([o["tokens_out"] for o in ops])
        avg_duration = _avg([o["duration_sec"] for o in ops])
        avg_cost = _cloud_cost_usd(avg_in, avg_out)
        has_subprocess = any(o["subprocess_count"] > 0 for o in ops)
        cost_cell = "غير قابل للتقدير (عملية فرعية Session 4 -- انظر الفصل 6)" if has_subprocess and avg_in == 0 else f"≈ ${avg_cost:.4f}"
        lines.append(f"| {kind} | {n} | {avg_calls:.1f} | {avg_in:.0f} / {avg_out:.0f} | {avg_duration:.1f} | {cost_cell} |")
    lines.append("")
    return lines


def render_agent_table(by_agent: dict) -> list:
    lines = ["## التكلفة حسب الوكيل والغرض (أين تذهب التكلفة فعليًا؟)", ""]
    if not by_agent:
        lines.append("لا توجد استدعاءات LLM مسجَّلة بعد.")
        lines.append("")
        return lines

    lines.append("| الوكيل | الغرض | عدد الاستدعاءات | متوسط توكنز دخل | متوسط توكنز خرج | متوسط الزمن (ثانية) | إجمالي التكلفة الافتراضية |")
    lines.append("|---|---|---|---|---|---|---|")
    for (agent, purpose), calls in sorted(by_agent.items(), key=lambda kv: -len(kv[1])):
        n = len(calls)
        avg_in = _avg([c["tokens_in"] or 0 for c in calls])
        avg_out = _avg([c["tokens_out"] or 0 for c in calls])
        avg_duration = _avg([c["duration_sec"] for c in calls])
        total_in = sum(c["tokens_in"] or 0 for c in calls)
        total_out = sum(c["tokens_out"] or 0 for c in calls)
        total_cost = _cloud_cost_usd(total_in, total_out)
        lines.append(f"| {agent} | {purpose} | {n} | {avg_in:.0f} | {avg_out:.0f} | {avg_duration:.1f} | ${total_cost:.4f} |")
    lines.append("")
    return lines


def render_report(events: list) -> str:
    by_kind = summarize_operations(events)
    by_agent = summarize_by_agent(events)

    llm_calls = [e for e in events if e["event"] == "llm_call"]
    total_operations = len(tracing.group_by_operation(events))
    total_tokens_in = sum(e["tokens_in"] for e in llm_calls)
    total_tokens_out = sum(e["tokens_out"] for e in llm_calls)
    estimated_source = "estimated_chars/4" in {e["tokens_source"] for e in llm_calls} if llm_calls else False

    lines = [f"# تقرير التكلفة — {date.today().isoformat()}", ""]
    lines.append(f"إجمالي العمليات المسجَّلة: {total_operations}  ")
    lines.append(f"إجمالي استدعاءات LLM: {len(llm_calls)}  ")
    lines.append(f"إجمالي التوكنز: {total_tokens_in} دخل + {total_tokens_out} خرج")
    lines.append("")
    lines.append(
        "⚠️ الأسعار السحابية أدناه أرقام افتراضية قابلة للتعديل في `lab_config.py` "
        "(`CLOUD_PRICE_PER_1K_INPUT_TOKENS_USD` / `CLOUD_PRICE_PER_1K_OUTPUT_TOKENS_USD`) -- "
        "ليست أسعارًا فعلية حالية لأي مزود، وتتغير مع الوقت. لا تُستخدم إلا لتقدير نسبي: "
        "\"هذه العملية تستهلك تقريبًا ضعف تلك\"، لا فاتورة حقيقية."
    )
    if estimated_source:
        lines.append(
            "\nملاحظة: بعض استدعاءات structured output (القاضي، والتصنيف/التحقق داخل مدقق الاتساق) "
            "لا تعرض عدد توكنز Ollama الحقيقي، فاستُخدم تقدير تقريبي (chars/4) لها بدلًا من ذلك -- "
            "كافٍ للمقارنة النسبية بين العمليات، لا لدقة الفوترة."
        )
    lines.append("")

    lines += render_kind_table(
        by_kind,
        PRODUCTION_KINDS,
        "التكلفة حسب نوع العملية (استخدام إنتاجي فعلي)",
        "هذا الجدول يجيب: \"لو سألت النظام سؤالًا من هذا النوع، كم يكلف تقريبًا؟\"",
    )
    lines += render_agent_table(by_agent)
    lines += render_kind_table(
        by_kind,
        EVALUATION_KINDS,
        "تكلفة التقييم نفسه (evaluate.py / judge.py)",
        "التقييم ليس مجانيًا -- كل تشغيل لـ `evaluate.py` يستدعي النظام الحقيقي **و** القاضي معًا لكل سؤال. "
        "هذا القسم منفصل عمدًا عن الجدول أعلاه حتى لا تختلط تكلفة قياس الجودة بتكلفة الاستخدام الفعلي.",
    )

    lines.append("## أسئلة ضبط شائعة (التفاصيل والأثر المتوقع في الفصل 5 من الكتيّب)")
    lines.append("")
    lines.append("- هل استدعاءات `route_classification` كثيرة ورخيصة نسبيًا؟ مرشّح جيد لنموذج أصغر.")
    lines.append("- هل `quality_review` يُطلق مراجعة (`revise`) في أغلب الأسئلة؟ قد تحتاج تحسين prompt التركيب `compose_report` بدل رفع MAX_REVISIONS.")
    lines.append("- هل `consistency_check` يستهلك استدعاءات أكثر بكثير من `research`؟ فعّل الحلقة عند الطلب فقط، لا تلقائيًا على كل تغيير صغير.")
    lines.append("- هل `retrieve` يعيد مقاطع كثيرة غير مستخدَمة فعليًا في التقرير النهائي؟ قلّل `RESEARCH_K` في agents/researcher.py.")
    lines.append("")

    return "\n".join(lines)


def main():
    print("📖 قراءة كل ملفات traces/...")
    events = tracing.read_events()
    if not events:
        print("⚠️  لا توجد أحداث مسجَّلة بعد. شغّل evaluate.py أو استخدم labs/session5/team.py أولًا.")
        return
    print(f"   {len(events)} حدثًا محمّلًا عبر {len(tracing.group_by_operation(events))} عملية.\n")

    report = render_report(events)
    config.EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = config.EVAL_REPORTS_DIR / f"cost_report_{date.today().isoformat()}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"✅ تقرير التكلفة محفوظ في: {report_path}")


if __name__ == "__main__":
    main()
