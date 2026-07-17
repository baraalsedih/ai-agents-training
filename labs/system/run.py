"""Unified entry point -- Session 7 (the capstone).

One menu, one command, one config -- for everything Sessions 3-6 already
built. This file contains NO new agent logic: every menu option below
calls the exact same, unmodified functions those sessions already ship,
imported as sibling modules (same convention Session 4 already used to
import Session 3, Session 5 to import Sessions 3-4, and Session 6 to
import Session 5). Nothing here is copied or re-implemented -- see the
Owner's Manual, chapter 1, for the full component map.

Usage:
    python3 run.py                 # Arabic interactive menu
    python3 run.py ingest          # process every new file in inbox/
    python3 run.py ask ["..."]     # quick Q&A over the archive
    python3 run.py research "..."  # a cited research report
    python3 run.py audit [--category ...]
    python3 run.py evaluate [--set-baseline]
    python3 run.py dashboard
    python3 run.py backup

Everything runs 100% locally through Ollama -- no API keys, no data
leaving this machine.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import system_config as config

# Sibling lab folders, added to sys.path so their real modules can be
# imported directly -- not an installed package, same convention every
# lab since Session 4 already uses for labs/session3/.
sys.path.insert(0, str(config.SESSION3_DIR))
sys.path.insert(0, str(config.SESSION5_DIR))
sys.path.insert(0, str(config.SESSION6_DIR))

import config as kb_config  # noqa: E402 -- Session 3's knowledge-base config (bare "config", see system_config.py's docstring)
import ask as kb_ask  # noqa: E402 -- Session 3
import report as kb_report  # noqa: E402 -- Session 3
from agents import consistency_auditor, researcher, source_analyst  # noqa: E402 -- Session 5

MAINTENANCE_NOTE = "   راجع دليل المالك (handbook_session7_owners_manual.pdf)، الفصل 5: دليل الصيانة والإصلاح."


# ------------------------------------------------------------------------
# 1. Ingest -- inbox/ -> source-analysis agent (Sessions 4-5) -> processed/
# ------------------------------------------------------------------------
def cmd_ingest() -> None:
    config.INBOX_DIR.mkdir(parents=True, exist_ok=True)
    config.INBOX_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p for p in config.INBOX_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in kb_config.SUPPORTED_EXTENSIONS
    )
    if not files:
        print("📭 لا توجد مستندات جديدة في inbox/.")
        print(f"   ضع ملفاتك (.pdf / .docx / .txt / .md) في: {config.INBOX_DIR}")
        return

    print(f"📥 {len(files)} مستند(ات) جديدة في inbox/. سيمر كل ملف عبر وكيل تحليل المصادر (الجلستان 4-5):")
    print("   استخراج → تقطيع → تصنيف → (أحيانًا) مراجعة بشرية → اقتراح روابط → موافقتك → إدخال.\n")

    for f in files:
        print(f"{'=' * 70}\n📄 {f.name}\n{'=' * 70}")
        try:
            source_analyst.run_source_analyst(str(f))
        except Exception as exc:
            print(f"\n❌ فشل تحليل {f.name}: {type(exc).__name__}: {exc}")
            print(MAINTENANCE_NOTE)
            continue

        dest = config.INBOX_PROCESSED_DIR / f.name
        shutil.move(str(f), str(dest))
        print(f"📦 نُقل {f.name} إلى inbox/processed/\n")


# ------------------------------------------------------------------------
# 2. Ask -- quick, single-pass Q&A over the archive (Session 3)
# ------------------------------------------------------------------------
def _print_ask_result(result: dict) -> None:
    if not result["found"]:
        print("⚠️  لم يُعثر على مقاطع ذات صلة.")
        return
    print("\n💬 الإجابة:")
    print(result["answer"])
    print("\n📚 المصادر:")
    for s in result["sources"]:
        print(f"   - {s['source']} — {s['category_label']} — {s['summary']}")


def cmd_ask(question: str = None) -> None:
    if not kb_config.CHROMA_DIR.exists():
        print("❌ لا توجد قاعدة معرفة بعد. أضف مستندات عبر الخيار 1 أولًا.")
        print(MAINTENANCE_NOTE)
        return

    llm, vectorstore = kb_ask.build_resources()

    if question:
        _print_ask_result(kb_ask.answer_question(llm, vectorstore, question))
        return

    print("🔎 اسأل أرشيفك مباشرة (سؤال وجواب سريع، بلا تقرير). اكتب 'exit' للخروج.")
    while True:
        try:
            q = input("\n❓ سؤالك: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nإلى اللقاء 👋")
            return
        if not q:
            continue
        if q.lower() in ("exit", "quit", "خروج"):
            return
        _print_ask_result(kb_ask.answer_question(llm, vectorstore, q))


# ------------------------------------------------------------------------
# 3. Research -- decomposed, cited research report (Session 5's researcher)
# ------------------------------------------------------------------------
def cmd_research(question: str = None) -> None:
    if not kb_config.CHROMA_DIR.exists():
        print("❌ لا توجد قاعدة معرفة بعد. أضف مستندات عبر الخيار 1 أولًا.")
        print(MAINTENANCE_NOTE)
        return

    if not question:
        try:
            question = input("❓ سؤال البحث: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nإلى اللقاء 👋")
            return
    if not question:
        print("لم يُدخَل سؤال.")
        return

    try:
        result = researcher.run_research(question)
    except Exception as exc:
        print(f"❌ فشل إعداد التقرير البحثي: {type(exc).__name__}: {exc}")
        print(MAINTENANCE_NOTE)
        return

    print("\n" + result["report_markdown"])


# ------------------------------------------------------------------------
# 4. Audit -- consistency check across the archive (Session 5's auditor)
# ------------------------------------------------------------------------
def cmd_audit(category: str = None) -> None:
    if not kb_config.CHROMA_DIR.exists():
        print("❌ لا توجد قاعدة معرفة بعد. أضف مستندات عبر الخيار 1 أولًا.")
        print(MAINTENANCE_NOTE)
        return

    try:
        result = consistency_auditor.run_consistency_check(category_filter=category, auto_confirm=False)
    except Exception as exc:
        print(f"❌ فشل فحص الاتساق: {type(exc).__name__}: {exc}")
        print(MAINTENANCE_NOTE)
        return

    if result["report_markdown"]:
        print("\n" + result["report_markdown"])


# ------------------------------------------------------------------------
# 5. Evaluate -- the golden-set run (Session 6). Heavy, so it runs as a
# subprocess in Session 6's own venv, exactly as its README documents.
# ------------------------------------------------------------------------
def cmd_evaluate(set_baseline: bool = False) -> None:
    print("⏳ التقييم الكامل يشغّل 15 سؤالًا عبر الفريق الكامل + القاضي الآلي — يستغرق عادة 30-45 دقيقة على نموذج محلي 8B.")
    try:
        answer = input("متابعة؟ (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nأُلغي.")
        return
    if answer not in ("y", "yes"):
        print("أُلغي.")
        return

    python_exe = str(config.SESSION6_VENV_PYTHON) if config.SESSION6_VENV_PYTHON.exists() else sys.executable
    cmd = [python_exe, "evaluate.py"]
    if set_baseline:
        cmd.append("--set-baseline")

    result = subprocess.run(cmd, cwd=str(config.SESSION6_DIR))
    if result.returncode != 0:
        print(f"❌ فشل التقييم (كود الخروج {result.returncode}).")
        print(MAINTENANCE_NOTE)


# ------------------------------------------------------------------------
# 6. Dashboard -- generated locally by dashboard.py (this folder)
# ------------------------------------------------------------------------
def cmd_dashboard() -> None:
    import dashboard

    try:
        dashboard.generate_dashboard(open_browser=True)
    except Exception as exc:
        print(f"❌ فشل توليد لوحة المتابعة: {type(exc).__name__}: {exc}")
        print(MAINTENANCE_NOTE)


# ------------------------------------------------------------------------
# 7. Backup -- create a dated archive (this folder's backup.py)
# ------------------------------------------------------------------------
def cmd_backup() -> None:
    import backup

    try:
        backup.create_backup()
    except Exception as exc:
        print(f"❌ فشلت النسخة الاحتياطية: {type(exc).__name__}: {exc}")
        print(MAINTENANCE_NOTE)


# ------------------------------------------------------------------------
# Interactive menu
# ------------------------------------------------------------------------
MENU_TEXT = """
============================================================
🧭 نظامك — نقطة الدخول الموحدة
============================================================
  1) أدخل مستندات جديدة        (inbox/ → تحليل → موافقة → إدخال)
  2) اسأل أرشيفك                (سؤال وجواب سريع)
  3) اطلب تقريرًا بحثيًا         (تقرير مركّب موثّق المصادر)
  4) افحص الاتساق               (تكرارات / تعارضات / فجوات / مصطلحات)
  5) شغّل التقييم               (مجموعة ذهبية + قاضٍ آلي، 30-45 دقيقة)
  6) افتح لوحة المتابعة
  7) نسخة احتياطية
  0) خروج
============================================================"""


def interactive_menu() -> None:
    while True:
        print(MENU_TEXT)
        try:
            choice = input("اختر رقمًا: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nإلى اللقاء 👋")
            return

        if choice == "1":
            cmd_ingest()
        elif choice == "2":
            cmd_ask()
        elif choice == "3":
            cmd_research()
        elif choice == "4":
            cmd_audit()
        elif choice == "5":
            cmd_evaluate()
        elif choice == "6":
            cmd_dashboard()
        elif choice == "7":
            cmd_backup()
        elif choice in ("0", "خروج", "exit", "quit"):
            print("إلى اللقاء 👋")
            return
        else:
            print("⚠️  اختيار غير معروف. اكتب رقمًا من 0 إلى 7.")


# ------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Session 7 -- unified system entry point")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("ingest", help="Process every new file waiting in inbox/")

    p_ask = sub.add_parser("ask", help="Quick Q&A over the archive")
    p_ask.add_argument("question", nargs="?", help="Ask one question and exit; omit for an interactive loop")

    p_research = sub.add_parser("research", help="A cited, composed research report")
    p_research.add_argument("question", nargs="?")

    p_audit = sub.add_parser("audit", help="Consistency audit of the archive")
    p_audit.add_argument("--category", choices=kb_config.CATEGORIES, help="Restrict the audit to one category")

    p_eval = sub.add_parser("evaluate", help="Run the golden-set evaluation")
    p_eval.add_argument("--set-baseline", action="store_true")

    sub.add_parser("dashboard", help="Generate and open the dashboard")
    sub.add_parser("backup", help="Create a dated backup archive")

    args = parser.parse_args()

    if args.command is None:
        interactive_menu()
        return

    if args.command == "ingest":
        cmd_ingest()
    elif args.command == "ask":
        cmd_ask(args.question)
    elif args.command == "research":
        cmd_research(args.question)
    elif args.command == "audit":
        cmd_audit(args.category)
    elif args.command == "evaluate":
        cmd_evaluate(args.set_baseline)
    elif args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "backup":
        cmd_backup()


if __name__ == "__main__":
    main()
