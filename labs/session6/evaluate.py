"""Golden-set evaluator -- Session 6.

Runs every question in golden_set.yaml through the real Session 5 team
(unmodified graph, imported directly -- not re-implemented), judges each
answer on the four quality dimensions (judge.py), and writes a dated
Markdown report: a score table, per-dimension averages, a comparison
against the saved baseline (if one exists), and the three weakest
questions flagged for human review.

The system's run and the judge's verdict for each golden question are
traced into the SAME operation (see run_question() below) -- so
view_traces.py on any one golden question's operation_id shows the full
picture: routing, retrieval, report composition, AND the judge's scores,
in one place. That's what makes the diagnosis workflow in chapter 6 of
the handbook possible.

Usage:
    python3 evaluate.py                  # run all golden questions, judge, report
    python3 evaluate.py --set-baseline   # also (re)establish baseline.json from this run

Everything runs locally through Ollama -- no external API calls.
"""

import argparse
import json
import sys
import warnings
from datetime import date
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore", category=DeprecationWarning)

import yaml

import judge
import lab_config as config
import tracing

# labs/session5/ is a sibling directory, not an installed package -- same
# import convention Session 5 itself already uses for labs/session3/.
SESSION5_DIR = Path(__file__).resolve().parent.parent / "session5"
sys.path.insert(0, str(SESSION5_DIR))
import team as session5_team  # noqa: E402 -- the real, unmodified Session 5 graph


def load_golden_set() -> list:
    data = yaml.safe_load(config.GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    return data["questions"]


def _judge_with_fallback(**kwargs) -> dict:
    """One retry, then a clearly-marked failure verdict instead of crashing
    the whole 15-question run over one bad generation. Observed for real
    during testing: the local judge model fell into a degenerate repetition
    loop writing one rationale (the same sentence pattern dozens of times)
    and produced unparseable output -- a genuine local-model failure mode,
    not a bug in judge.py's schema. See handbook chapter 4.3."""
    for attempt in (1, 2):
        try:
            verdict = judge.judge_answer(**kwargs)
            return judge.verdict_to_dict(verdict)
        except Exception as exc:  # noqa: BLE001 -- any parse/schema failure from the judge call, by design
            print(f"   ⚠️  فشل القاضي في المحاولة {attempt}: {type(exc).__name__} -- {str(exc)[:120]}")
    note = "⚠️ فشل القاضي الآلي في إنتاج حكم صالح لهذا السؤال بعد محاولتين (خطأ تحليل استجابة النموذج المحلي) -- يحتاج مراجعة يدوية كاملة، هذه ليست درجة قاضٍ حقيقية."
    return {dim: {"score": 1, "rationale": note} for dim in judge.DIMENSIONS}


def run_question(app, question: dict) -> dict:
    initial_state = {
        "user_request": question["question"],
        "destination": "",
        "args": {},
        "result": "",
        "research_sources": [],
        "revision_count": 0,
        "quality_feedback": "",
    }
    with tracing.operation("golden_eval", {"golden_id": question["id"], "golden_type": question["type"], "question": question["question"]}):
        final_state = app.invoke(initial_state)
        destination = final_state.get("destination", "?")
        cited_sources = [s["source"] for s in final_state.get("research_sources", [])] if destination == "research" else []

        verdict_dict = _judge_with_fallback(
            question=question["question"],
            reference_answer=question["reference_answer"],
            system_answer=final_state.get("result", ""),
            cited_sources=cited_sources,
            expected_sources=question.get("expected_sources") or [],
        )
        avg = judge.average_score(verdict_dict)
        tracing.log_decision(
            node="evaluate", choice=f"avg_score={avg:.2f}", extra={dim: verdict_dict[dim]["score"] for dim in judge.DIMENSIONS}
        )

    return {
        "id": question["id"],
        "type": question["type"],
        "question": question["question"],
        "destination": destination,
        "system_answer": final_state.get("result", ""),
        "cited_sources": cited_sources,
        "expected_sources": question.get("expected_sources") or [],
        "verdict": verdict_dict,
        "average": avg,
    }


def aggregate(results: list) -> dict:
    per_dimension = {dim: sum(r["verdict"][dim]["score"] for r in results) / len(results) for dim in judge.DIMENSIONS}
    overall = sum(r["average"] for r in results) / len(results)
    return {"per_dimension": per_dimension, "overall": overall}


def load_baseline() -> Optional[dict]:
    if config.BASELINE_PATH.exists():
        return json.loads(config.BASELINE_PATH.read_text(encoding="utf-8"))
    return None


def save_baseline(agg: dict) -> None:
    config.EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"date": date.today().isoformat(), **agg}
    config.BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _delta_arrow(delta: float) -> str:
    # +/-0.05 is noise-tolerance, not a meaningful change, on a 1-5 scale
    # judged by a single local model run -- avoids flagging every run as
    # "changed" from tiny judge variance alone.
    if delta > 0.05:
        return "🟢▲"
    if delta < -0.05:
        return "🔴▼"
    return "⚪"


def render_report(results: list, agg: dict, baseline: Optional[dict]) -> str:
    lines = [f"# تقرير تقييم الجودة — {date.today().isoformat()}", ""]
    lines.append(f"نموذج القاضي: `{config.JUDGE_MODEL}` (ثابت عبر كل التشغيلات لضمان قابلية المقارنة)  ")
    lines.append(f"عدد الأسئلة: {len(results)}")
    lines.append("")

    lines.append("## جدول الدرجات لكل سؤال")
    lines.append("")
    lines.append("| # | النوع | الوجهة | الصحة | الالتزام بالمصادر | الاكتمال | الصدق | المتوسط |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        v = r["verdict"]
        lines.append(
            f"| {r['id']} | {r['type']} | {r['destination']} | {v['correctness']['score']} | {v['groundedness']['score']} | "
            f"{v['completeness']['score']} | {v['honesty']['score']} | **{r['average']:.2f}** |"
        )
    lines.append("")

    lines.append("## المتوسطات لكل بُعد")
    lines.append("")
    for dim in judge.DIMENSIONS:
        lines.append(f"- **{judge.DIMENSION_LABELS_AR[dim]}**: {agg['per_dimension'][dim]:.2f} / 5")
    lines.append(f"- **المتوسط العام**: {agg['overall']:.2f} / 5")
    lines.append("")

    if baseline:
        lines.append("## مقارنة بخط الأساس السابق")
        lines.append("")
        lines.append(f"خط الأساس محفوظ بتاريخ: {baseline.get('date', '?')}")
        lines.append("")
        for dim in judge.DIMENSIONS:
            delta = agg["per_dimension"][dim] - baseline["per_dimension"][dim]
            lines.append(f"- {judge.DIMENSION_LABELS_AR[dim]}: {delta:+.2f} {_delta_arrow(delta)}")
        overall_delta = agg["overall"] - baseline["overall"]
        lines.append(f"- **المتوسط العام**: {overall_delta:+.2f} {_delta_arrow(overall_delta)}")
        lines.append("")
    else:
        lines.append("## خط الأساس")
        lines.append("")
        lines.append("لا يوجد خط أساس سابق — نتائج هذا التشغيل حُفظت كخط الأساس الأول (`baseline.json`). ")
        lines.append("التشغيلات القادمة ستُقارَن به تلقائيًا، ما لم تُستدعَ بـ `--set-baseline` لتحديثه.")
        lines.append("")

    worst = sorted(results, key=lambda r: r["average"])[:3]
    lines.append("## أضعف 3 أسئلة — مرشحة للمراجعة البشرية")
    lines.append("")
    for r in worst:
        flag = " ⚠️ تحت العتبة الدنيا" if r["average"] < config.LOW_SCORE_THRESHOLD else ""
        lines.append(f"### {r['id']} ({r['type']}) — متوسط {r['average']:.2f}/5{flag}")
        lines.append(f"**السؤال:** {r['question']}")
        lines.append("")
        lowest_dim = min(judge.DIMENSIONS, key=lambda d: r["verdict"][d]["score"])
        lines.append(
            f"أضعف بُعد: **{judge.DIMENSION_LABELS_AR[lowest_dim]}** ({r['verdict'][lowest_dim]['score']}/5) — "
            f"{r['verdict'][lowest_dim]['rationale']}"
        )
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Session 6 golden-set evaluator")
    parser.add_argument("--set-baseline", action="store_true", help="(Re)establish baseline.json from this run's results")
    args = parser.parse_args()

    print("📖 تحميل المجموعة الذهبية...")
    questions = load_golden_set()
    print(f"   {len(questions)} سؤالًا محمّلًا.\n")

    app = session5_team.build_graph()

    results = []
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] ({q['type']}) {q['question'][:60]}...")
        result = run_question(app, q)
        print(f"   → الوجهة: {result['destination']} | المتوسط: {result['average']:.2f}/5")
        results.append(result)

    agg = aggregate(results)
    old_baseline = load_baseline()
    report = render_report(results, agg, old_baseline)

    config.EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = config.EVAL_REPORTS_DIR / f"eval_report_{date.today().isoformat()}.md"
    report_path.write_text(report, encoding="utf-8")

    if args.set_baseline or old_baseline is None:
        save_baseline(agg)
        print("\n✅ تم حفظ/تحديث خط الأساس (baseline.json).")

    print(f"\n✅ تقرير الجودة محفوظ في: {report_path}")
    print(f"📊 المتوسط العام: {agg['overall']:.2f} / 5")


if __name__ == "__main__":
    main()
