"""Dashboard generator -- Session 7 capstone.

Reads whatever Sessions 3-6 have already produced on disk (no live model
calls, no re-running anything) and renders one static HTML file: knowledge-
base health, decision-support lists (open questions + the auditor's latest
gaps/contradictions), recent activity (from Session 6's traces), and
quality/cost (from Session 6's eval reports and cost data). Every card
that has no data yet says so plainly instead of failing.

Usage:
    python3 dashboard.py

Why a static HTML file instead of a running web app: zero maintenance,
zero moving parts, opens in any browser, never goes stale silently (the
generation timestamp is printed on the page itself) -- see the Owner's
Manual, chapter 3, for the full reasoning.
"""

import html
import json
import re
import sys
import webbrowser
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import system_config as config

# Sibling lab folders -- same sys.path convention run.py uses.
sys.path.insert(0, str(config.SESSION3_DIR))
sys.path.insert(0, str(config.SESSION5_DIR))
sys.path.insert(0, str(config.SESSION6_DIR))

import config as kb_config  # noqa: E402 -- Session 3
import report as kb_report  # noqa: E402 -- Session 3
import judge  # noqa: E402 -- Session 6 (DIMENSIONS, DIMENSION_LABELS_AR)
import lab_config as eval_config  # noqa: E402 -- Session 6
import tracing  # noqa: E402 -- Session 6

CONSISTENCY_REPORTS_DIR = config.SESSION5_DIR / "reports"
PRODUCTION_KINDS = {"research", "consistency_check", "analyze_document", "direct_answer"}
KIND_LABELS_AR = {
    "research": "تقرير بحثي",
    "consistency_check": "فحص اتساق",
    "analyze_document": "تحليل مستند",
    "direct_answer": "إجابة مباشرة",
    "golden_eval": "سؤال تقييم (مجموعة ذهبية)",
    "evaluation": "تقييم",
    "request": "طلب",
}


def _cloud_cost_usd(tokens_in: float, tokens_out: float) -> float:
    """Same placeholder-price formula as labs/session6/cost_report.py's
    own helper -- kept local so this module doesn't reach into another
    module's underscored (private-by-convention) function."""
    return (tokens_in / 1000) * eval_config.CLOUD_PRICE_PER_1K_INPUT_TOKENS_USD + (tokens_out / 1000) * eval_config.CLOUD_PRICE_PER_1K_OUTPUT_TOKENS_USD


# ------------------------------------------------------------------------
# Card 1: knowledge-base health (Session 3)
# ------------------------------------------------------------------------
def get_kb_health():
    if not kb_config.CHROMA_DIR.exists():
        return None
    metadatas = kb_report.collect_data()
    if not metadatas:
        return {"empty": True}

    data = kb_report.compute_report_data(metadatas)
    manifest = {"files": {}}
    if kb_config.MANIFEST_PATH.exists():
        manifest = json.loads(kb_config.MANIFEST_PATH.read_text(encoding="utf-8"))

    last_ingested = None
    for info in manifest["files"].values():
        ts = info.get("last_ingested")
        if ts and (last_ingested is None or ts > last_ingested):
            last_ingested = ts

    return {
        "empty": False,
        "total_chunks": data["total"],
        "counts": data["counts"],
        "open_questions": data["open_questions"],
        "doc_count": len(manifest["files"]),
        "last_ingested": last_ingested,
    }


# ------------------------------------------------------------------------
# Card 2: decision support -- open questions (Session 3) + latest
# gaps/contradictions from the consistency auditor (Session 5)
# ------------------------------------------------------------------------
def _flatten_open_questions(open_questions: dict) -> list:
    items = []
    for source, summaries in open_questions.items():
        for summary in summaries:
            items.append({"source": source, "summary": summary})
    return items


def get_latest_consistency_report():
    if not CONSISTENCY_REPORTS_DIR.exists():
        return None
    files = sorted(CONSISTENCY_REPORTS_DIR.glob("consistency_report_*.md"))
    if not files:
        return None

    path = files[-1]
    text = path.read_text(encoding="utf-8")

    def _count(pattern):
        m = re.search(pattern, text)
        return int(m.group(1)) if m else 0

    counts = {
        "duplicates": _count(r"## 1\. Duplicates \((\d+) confirmed"),
        "contradictions": _count(r"## 2\. Contradictions \((\d+) confirmed"),
        "gaps": _count(r"## 3\. Gaps[^\n]*\((\d+)\)"),
        "glossary": _count(r"## 4\. Terminology unification \((\d+) cluster"),
    }

    def _section(start_marker, end_marker):
        start = text.find(start_marker)
        if start == -1:
            return ""
        end = text.find(end_marker, start)
        return text[start:end] if end != -1 else text[start:]

    gaps_section = _section("## 3. Gaps", "## 4. Terminology")
    gap_lines = [ln[2:].strip() for ln in gaps_section.splitlines() if ln.startswith("- `")][:5]

    contradictions_section = _section("## 2. Contradictions", "## 3. Gaps")
    contradiction_lines = [ln[2:].strip() for ln in contradictions_section.splitlines() if ln.startswith("- **")][:5]

    date_match = re.search(r"Date: (\d{4}-\d{2}-\d{2})", text)
    return {
        "date": date_match.group(1) if date_match else None,
        "path": str(path),
        "counts": counts,
        "gap_lines": gap_lines,
        "contradiction_lines": contradiction_lines,
    }


# ------------------------------------------------------------------------
# Card 3: recent activity (Session 6 traces)
# ------------------------------------------------------------------------
def get_recent_activity(limit: int = 10) -> list:
    events = tracing.read_events()
    if not events:
        return []

    grouped = tracing.group_by_operation(events)
    rows = []
    for op_id, op_events in grouped.items():
        start = next((e for e in op_events if e["event"] == "operation_start"), None)
        end = next((e for e in op_events if e["event"] == "operation_end"), None)
        kind = tracing.operation_kind(op_events)
        meta = start.get("meta", {}) if start else {}
        label = (
            meta.get("question")
            or meta.get("user_request")
            or meta.get("file_path")
            or meta.get("category_filter")
            or meta.get("golden_id")
            or ""
        )
        rows.append(
            {
                "operation_id": op_id,
                "ts": start["ts"] if start else "",
                "kind": kind,
                "kind_label": KIND_LABELS_AR.get(kind, kind),
                "duration_sec": end["duration_sec"] if end else None,
                "label": str(label)[:70],
            }
        )
    rows.sort(key=lambda r: r["ts"], reverse=True)
    return rows[:limit]


# ------------------------------------------------------------------------
# Card 4: quality (Session 6 eval reports) + cost (Session 6 traces)
# ------------------------------------------------------------------------
def get_eval_summary():
    eval_dir = eval_config.EVAL_REPORTS_DIR
    if not eval_dir.exists():
        return None
    files = sorted(eval_dir.glob("eval_report_*.md"))
    if not files:
        return None

    text = files[-1].read_text(encoding="utf-8")

    per_dimension = {}
    for dim in judge.DIMENSIONS:
        label = judge.DIMENSION_LABELS_AR[dim]
        m = re.search(rf"\*\*{re.escape(label)}\*\*: ([\d.]+) / 5", text)
        if m:
            per_dimension[dim] = float(m.group(1))

    overall_m = re.search(r"\*\*المتوسط العام\*\*: ([\d.]+) / 5", text)
    overall = float(overall_m.group(1)) if overall_m else None

    baseline = None
    if eval_config.BASELINE_PATH.exists():
        baseline = json.loads(eval_config.BASELINE_PATH.read_text(encoding="utf-8"))

    date_m = re.search(r"— (\d{4}-\d{2}-\d{2})", text)
    return {
        "date": date_m.group(1) if date_m else None,
        "per_dimension": per_dimension,
        "overall": overall,
        "baseline": baseline,
    }


def get_cost_summary():
    events = tracing.read_events()
    if not events:
        return None

    by_kind = defaultdict(list)
    for op_events in tracing.group_by_operation(events).values():
        kind = tracing.operation_kind(op_events)
        if kind not in PRODUCTION_KINDS:
            continue
        llm_calls = [e for e in op_events if e["event"] == "llm_call"]
        end = next((e for e in op_events if e["event"] == "operation_end"), None)
        by_kind[kind].append(
            {
                "tokens_in": sum(e["tokens_in"] or 0 for e in llm_calls),
                "tokens_out": sum(e["tokens_out"] or 0 for e in llm_calls),
                "duration_sec": end["duration_sec"] if end else 0,
            }
        )

    if not by_kind:
        return None

    rows = []
    for kind, ops in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
        n = len(ops)
        avg_in = sum(o["tokens_in"] for o in ops) / n
        avg_out = sum(o["tokens_out"] for o in ops) / n
        avg_duration = sum(o["duration_sec"] for o in ops) / n
        rows.append(
            {
                "kind": kind,
                "kind_label": KIND_LABELS_AR.get(kind, kind),
                "count": n,
                "avg_cost_usd": _cloud_cost_usd(avg_in, avg_out),
                "avg_duration": avg_duration,
            }
        )
    return rows


# ------------------------------------------------------------------------
# HTML rendering -- one self-contained file, RTL, light theme matching the
# slide deck's identity (same CSS variables as session*/styles.css).
# ------------------------------------------------------------------------
def _empty_card(message: str) -> str:
    return f'<p class="empty-note">⚪ {html.escape(message)}</p>'


def _render_kb_health_card(kb) -> str:
    if kb is None:
        return _empty_card("لا توجد قاعدة معرفة بعد — شغّل الخيار 1 (أدخل مستندات جديدة) أولًا.")
    if kb.get("empty"):
        return _empty_card("قاعدة المعرفة موجودة لكنها فارغة — أضف مستندات عبر الخيار 1.")

    labels = kb_config.CATEGORY_LABELS
    counts = kb["counts"]
    max_count = max(counts.values()) if counts else 1
    bars = []
    for cat in kb_config.CATEGORIES + ["unclassified"]:
        n = counts.get(cat, 0)
        pct = round((n / max_count) * 100) if max_count else 0
        bars.append(
            f'<div class="bar-row">'
            f'<span class="bar-label">{html.escape(labels.get(cat, cat))}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{pct}%"></span></span>'
            f'<span class="bar-count">{n}</span>'
            f"</div>"
        )

    last = kb["last_ingested"] or "—"
    return f"""
    <div class="stat-row">
      <div class="stat-tile"><span class="stat-num">{kb['total_chunks']}</span><span class="stat-label">مقطع مفهرَس</span></div>
      <div class="stat-tile"><span class="stat-num">{kb['doc_count']}</span><span class="stat-label">مستند</span></div>
    </div>
    <div class="bar-chart">{''.join(bars)}</div>
    <p class="fine-print">آخر إدخال: {html.escape(last)}</p>
    """


def _render_decision_support_card(kb, consistency) -> str:
    parts = []

    open_qs = _flatten_open_questions(kb["open_questions"]) if kb and not kb.get("empty") else []
    if not open_qs:
        parts.append('<h4 class="subhead">الأسئلة المفتوحة في أرشيفك</h4>')
        parts.append(_empty_card("لا أسئلة مفتوحة مسجَّلة بعد."))
    else:
        rows = "".join(
            f'<li><strong>{html.escape(q["source"])}</strong> — {html.escape(q["summary"])}</li>' for q in open_qs[:8]
        )
        more = f'<li class="fine-print">+ {len(open_qs) - 8} سؤال إضافي — التقرير الكامل: <span class="en">report.py</span></li>' if len(open_qs) > 8 else ""
        parts.append(f'<h4 class="subhead">الأسئلة المفتوحة في أرشيفك ({len(open_qs)})</h4>')
        parts.append(f'<ul class="decision-list">{rows}{more}</ul>')

    parts.append('<h4 class="subhead">آخر فحص اتساق (المدقق)</h4>')
    if consistency is None:
        parts.append(_empty_card("لا يوجد فحص اتساق بعد — شغّل الخيار 4."))
    else:
        c = consistency["counts"]
        parts.append(
            f'<div class="chip-row">'
            f'<span class="chip">🔁 تكرارات: {c["duplicates"]}</span>'
            f'<span class="chip chip-warn">⚠️ تعارضات: {c["contradictions"]}</span>'
            f'<span class="chip">🕳️ فجوات: {c["gaps"]}</span>'
            f'<span class="chip">🏷️ مصطلحات: {c["glossary"]}</span>'
            f"</div>"
        )
        if consistency["contradiction_lines"]:
            rows = "".join(f"<li>{html.escape(ln)}</li>" for ln in consistency["contradiction_lines"])
            parts.append(f'<ul class="decision-list">{rows}</ul>')
        if consistency["gap_lines"]:
            rows = "".join(f"<li>{html.escape(ln)}</li>" for ln in consistency["gap_lines"])
            parts.append(f'<ul class="decision-list">{rows}</ul>')
        parts.append(f'<p class="fine-print">تاريخ الفحص: {html.escape(consistency["date"] or "—")}</p>')

    return "".join(parts)


def _render_activity_card(rows: list) -> str:
    if not rows:
        return _empty_card("لا نشاط مسجَّل بعد — أي عملية إدخال/بحث/فحص تُسجَّل تلقائيًا هنا.")

    items = []
    for r in rows:
        ts_display = r["ts"].replace("T", " ")[:16] if r["ts"] else "—"
        duration = f"{r['duration_sec']:.1f} ث" if r["duration_sec"] is not None else "؟"
        label = f" — {html.escape(r['label'])}" if r["label"] else ""
        items.append(
            f'<li><span class="activity-kind">{html.escape(r["kind_label"])}</span>'
            f'<span class="activity-meta">{ts_display} · {duration}</span>{label}</li>'
        )
    return f'<ul class="activity-list">{"".join(items)}</ul>'


def _delta_badge(delta: float) -> str:
    if delta > 0.05:
        return f'<span class="badge badge-good">+{delta:.2f} ▲</span>'
    if delta < -0.05:
        return f'<span class="badge badge-bad">{delta:.2f} ▼</span>'
    return f'<span class="badge badge-neutral">{delta:+.2f} ⚪</span>'


def _render_quality_cost_card(eval_summary, cost_rows) -> str:
    parts = ['<h4 class="subhead">آخر تقييم للجودة</h4>']
    if eval_summary is None or eval_summary["overall"] is None:
        parts.append(_empty_card("لا يوجد تقييم بعد — شغّل الخيار 5 (قد يستغرق 30-45 دقيقة)."))
    else:
        overall = eval_summary["overall"]
        baseline = eval_summary["baseline"]
        delta_html = ""
        if baseline and baseline.get("overall") is not None:
            delta_html = _delta_badge(overall - baseline["overall"])
        parts.append(
            f'<div class="stat-row"><div class="stat-tile"><span class="stat-num">{overall:.2f}/5</span>'
            f'<span class="stat-label">المتوسط العام {delta_html}</span></div></div>'
        )
        dim_rows = "".join(
            f'<li>{html.escape(judge.DIMENSION_LABELS_AR[d])}: <strong>{eval_summary["per_dimension"].get(d, 0):.2f}</strong>/5</li>'
            for d in judge.DIMENSIONS
            if d in eval_summary["per_dimension"]
        )
        parts.append(f'<ul class="decision-list">{dim_rows}</ul>')
        parts.append(f'<p class="fine-print">تاريخ التقييم: {html.escape(eval_summary["date"] or "—")}</p>')

    parts.append('<h4 class="subhead">متوسط التكلفة حسب نوع العملية</h4>')
    if not cost_rows:
        parts.append(_empty_card("لا توجد عمليات مسجَّلة بعد لحساب التكلفة."))
    else:
        rows = "".join(
            f'<li><strong>{html.escape(r["kind_label"])}</strong> '
            f'({r["count"]} عملية) — ≈ ${r["avg_cost_usd"]:.4f} / عملية، {r["avg_duration"]:.1f} ث</li>'
            for r in cost_rows
        )
        parts.append(f'<ul class="decision-list">{rows}</ul>')
        parts.append('<p class="fine-print">تكلفة سحابية افتراضية للمقارنة النسبية فقط — راجع دليل المالك، الفصل 3.</p>')

    return "".join(parts)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>لوحة المتابعة — نظامك</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #f4f6fb; --surface: #ffffff; --surface-alt: #f1f3fa;
    --border: #e3e7f2; --text: #1c2333; --text-muted: #5c6478;
    --primary: #4b4ee0; --primary-dark: #383bb8; --accent: #14b8a6;
    --warn: #f59e0b; --warn-light: #fef3e0; --danger: #ef4444;
    --success: #22c55e; --shadow: 0 10px 30px rgba(28,35,51,.08);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 32px 24px 60px; background: var(--bg); color: var(--text);
    font-family: 'Tajawal', sans-serif; direction: rtl;
  }}
  h1, h2, h3, h4 {{ font-family: 'Cairo', sans-serif; margin: 0; }}
  .en {{ direction: ltr; unicode-bidi: isolate; font-family: 'Cairo', sans-serif; font-weight: 600; color: var(--primary-dark); }}
  header.page-header {{ max-width: 1100px; margin: 0 auto 24px; }}
  header.page-header h1 {{ font-size: 26px; font-weight: 900; }}
  header.page-header p {{ color: var(--text-muted); font-size: 13.5px; margin-top: 6px; }}
  .grid {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 860px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 18px;
    box-shadow: var(--shadow); padding: 22px 24px;
  }}
  .card-title {{ font-size: 17px; font-weight: 800; display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }}
  .subhead {{ font-size: 13.5px; font-weight: 700; color: var(--text-muted); margin: 16px 0 8px; }}
  .subhead:first-child {{ margin-top: 0; }}
  .stat-row {{ display: flex; gap: 14px; margin-bottom: 10px; }}
  .stat-tile {{ background: var(--surface-alt); border-radius: 12px; padding: 10px 16px; display: flex; flex-direction: column; gap: 2px; }}
  .stat-num {{ font-size: 22px; font-weight: 900; color: var(--primary-dark); }}
  .stat-label {{ font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }}
  .bar-chart {{ display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }}
  .bar-row {{ display: flex; align-items: center; gap: 8px; font-size: 12.5px; }}
  .bar-label {{ width: 84px; flex: 0 0 auto; color: var(--text-muted); }}
  .bar-track {{ flex: 1; background: var(--surface-alt); border-radius: 6px; height: 10px; overflow: hidden; }}
  .bar-fill {{ display: block; height: 100%; background: var(--primary); border-radius: 6px; }}
  .bar-count {{ width: 28px; flex: 0 0 auto; text-align: left; font-weight: 700; }}
  .decision-list {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; font-size: 12.8px; color: var(--text); }}
  .decision-list li {{ border-right: 3px solid var(--primary); padding-right: 10px; }}
  .chip-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }}
  .chip {{ background: var(--surface-alt); border-radius: 999px; padding: 4px 12px; font-size: 12px; font-weight: 700; }}
  .chip-warn {{ background: var(--warn-light); color: #92400e; }}
  .activity-list {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; font-size: 12.8px; }}
  .activity-list li {{ border-bottom: 1px dashed var(--border); padding-bottom: 8px; }}
  .activity-kind {{ font-weight: 800; color: var(--primary-dark); }}
  .activity-meta {{ color: var(--text-muted); font-size: 11.5px; margin-right: 6px; }}
  .badge {{ font-size: 11px; border-radius: 999px; padding: 2px 8px; font-weight: 700; }}
  .badge-good {{ background: #e7f9ee; color: #166534; }}
  .badge-bad {{ background: #fdecec; color: #991b1b; }}
  .badge-neutral {{ background: var(--surface-alt); color: var(--text-muted); }}
  .empty-note {{ color: var(--text-muted); font-size: 13px; background: var(--surface-alt); border-radius: 10px; padding: 10px 14px; }}
  .fine-print {{ color: var(--text-muted); font-size: 11.3px; margin-top: 10px; }}
  footer.page-footer {{ max-width: 1100px; margin: 30px auto 0; color: var(--text-muted); font-size: 11.5px; text-align: center; }}
</style>
</head>
<body>
<header class="page-header">
  <h1>🧭 لوحة المتابعة</h1>
  <p>تُولَّد عند الطلب من بيانات النظام الفعلية — وُلِّدت في: {generated_at}</p>
</header>
<div class="grid">
  <section class="card">
    <div class="card-title">📚 صحة قاعدة المعرفة</div>
    {kb_health_html}
  </section>
  <section class="card">
    <div class="card-title">🧭 دعم القرار</div>
    {decision_support_html}
  </section>
  <section class="card">
    <div class="card-title">🕓 النشاط الأخير</div>
    {activity_html}
  </section>
  <section class="card">
    <div class="card-title">📈 الجودة والتكلفة</div>
    {quality_cost_html}
  </section>
</div>
<footer class="page-footer">نظامك — الجلسة السابعة · ملف ثابت لا يعتمد على خادم قائم · أعِد التوليد من الخيار 6 في <span class="en">run.py</span></footer>
</body>
</html>"""


def generate_dashboard(open_browser: bool = False) -> Path:
    kb = get_kb_health()
    consistency = get_latest_consistency_report()
    activity_rows = get_recent_activity()
    eval_summary = get_eval_summary()
    cost_rows = get_cost_summary()

    html_out = PAGE_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        kb_health_html=_render_kb_health_card(kb),
        decision_support_html=_render_decision_support_card(kb, consistency),
        activity_html=_render_activity_card(activity_rows),
        quality_cost_html=_render_quality_cost_card(eval_summary, cost_rows),
    )

    config.DASHBOARD_PATH.write_text(html_out, encoding="utf-8")
    print(f"✅ لوحة المتابعة محدَّثة: {config.DASHBOARD_PATH}")

    if open_browser:
        webbrowser.open(f"file://{config.DASHBOARD_PATH}")

    return config.DASHBOARD_PATH


if __name__ == "__main__":
    generate_dashboard(open_browser=True)
