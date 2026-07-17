"""Backup / restore -- Session 7 capstone.

Archives everything that is genuinely irreplaceable if this machine is
lost: the knowledge base itself (Session 3), the auditor's reports and
glossary (Session 5), and the observability data + golden set (Session 6)
-- plus the tunable config files, so a restored copy remembers exactly
which models/thresholds/prices produced that data. Code is not included:
it already lives in this same git repository.

Usage:
    python3 backup.py                          # create a dated archive
    python3 backup.py restore --file <path> --to <dir>

Everything here is a plain file copy -- no network calls, no Ollama
required (a restore can be verified even offline).
"""

import argparse
import json
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import system_config as config

# What actually gets backed up: (path on disk, arcname prefix inside the zip).
# Missing paths are skipped with a note -- a fresh system that hasn't run
# every command yet shouldn't make backup.py fail.
BACKUP_SOURCES = [
    (config.SESSION3_DIR / "knowledge_base", "session3/knowledge_base"),
    (config.SESSION5_DIR / "reports", "session5/reports"),
    (config.SESSION5_DIR / "glossary.json", "session5/glossary.json"),
    (config.SESSION6_DIR / "traces", "session6/traces"),
    (config.SESSION6_DIR / "eval_reports", "session6/eval_reports"),
    (config.SESSION6_DIR / "golden_set.yaml", "session6/golden_set.yaml"),
    (config.SESSION3_DIR / "config.py", "configs/session3_config.py"),
    (config.SESSION6_DIR / "lab_config.py", "configs/session6_lab_config.py"),
    (config.BASE_DIR / "system_config.py", "configs/system_config.py"),
]


def _add_to_zip(zf: zipfile.ZipFile, source: Path, arcname: str) -> int:
    """Adds a file or a whole directory tree to the zip. Returns how many
    files were actually written (0 if the source doesn't exist)."""
    if not source.exists():
        return 0
    if source.is_file():
        zf.write(source, arcname)
        return 1
    count = 0
    for path in source.rglob("*"):
        if path.is_file():
            rel = path.relative_to(source)
            zf.write(path, f"{arcname}/{rel}")
            count += 1
    return count


def create_backup() -> Path:
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    archive_path = config.BACKUP_DIR / f"backup_{stamp}.zip"

    print("📦 إنشاء نسخة احتياطية...")
    total_files = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for source, arcname in BACKUP_SOURCES:
            n = _add_to_zip(zf, source, arcname)
            status = f"{n} ملف" if n else "غير موجود بعد — تُخُطّي"
            print(f"   {'✅' if n else '⚪'} {arcname} ({status})")
            total_files += n

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ النسخة الاحتياطية جاهزة: {archive_path}")
    print(f"   {total_files} ملفًا إجمالًا — الحجم: {size_mb:.2f} م.ب.")
    return archive_path


# ------------------------------------------------------------------------
# Restore + a basic offline integrity check (no Ollama needed)
# ------------------------------------------------------------------------
def _verify_restored(target_dir: Path) -> list:
    """Returns a list of (label, ok: bool, detail: str) checks. Deliberately
    offline/lightweight: file existence + size, and JSON files actually
    parse -- enough to confirm the archive extracted correctly without
    needing Ollama or re-running the pipeline."""
    checks = []

    sqlite_path = target_dir / "session3" / "knowledge_base" / "chroma" / "chroma.sqlite3"
    if sqlite_path.exists():
        size_kb = sqlite_path.stat().st_size / 1024
        checks.append(("قاعدة المعرفة (Chroma)", size_kb > 0, f"{size_kb:.0f} ك.ب."))
    else:
        checks.append(("قاعدة المعرفة (Chroma)", False, "لم تُستعاد — لم تكن موجودة في هذه النسخة الاحتياطية"))

    manifest_path = target_dir / "session3" / "knowledge_base" / "manifest.json"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            checks.append(("manifest.json", True, f"{len(data.get('files', {}))} ملف مفهرَس"))
        except json.JSONDecodeError as exc:
            checks.append(("manifest.json", False, f"ملف تالف: {exc}"))
    else:
        checks.append(("manifest.json", False, "غير موجود في هذه النسخة"))

    baseline_path = target_dir / "session6" / "eval_reports" / "baseline.json"
    if baseline_path.exists():
        try:
            json.loads(baseline_path.read_text(encoding="utf-8"))
            checks.append(("baseline.json (التقييم)", True, "صالح"))
        except json.JSONDecodeError as exc:
            checks.append(("baseline.json (التقييم)", False, f"ملف تالف: {exc}"))

    configs_dir = target_dir / "configs"
    if configs_dir.exists():
        n = sum(1 for _ in configs_dir.glob("*.py"))
        checks.append(("ملفات الإعدادات", n > 0, f"{n} ملف"))

    return checks


def restore_backup(archive_file: Path, target_dir: Path) -> None:
    if not archive_file.exists():
        print(f"❌ الملف غير موجود: {archive_file}")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"📂 استخراج {archive_file.name} إلى {target_dir}...")
    with zipfile.ZipFile(archive_file, "r") as zf:
        zf.extractall(target_dir)

    print("\n🔍 فحص سلامة الاسترجاع (بلا اتصال، بلا Ollama):")
    checks = _verify_restored(target_dir)
    all_ok = True
    for label, ok, detail in checks:
        print(f"   {'✅' if ok else '❌'} {label} — {detail}")
        all_ok = all_ok and ok

    print(f"\n{'✅ الاسترجاع سليم.' if all_ok else '⚠️  راجع العناصر أعلاه المعلّمة بـ ❌.'}")
    print(f"   الملفات مستعادة في: {target_dir}")
    print("   لتشغيل النظام فعليًا من هذه النسخة، انسخ محتوى session3/knowledge_base/ فوق labs/session3/knowledge_base/")
    print("   (أو عدّل system_config.py ليشير إلى هذا المسار) ثم شغّل run.py من جديد.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Session 7 backup / restore")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("backup", help="Create a dated backup archive (default if no command given)")

    p_restore = sub.add_parser("restore", help="Extract a backup archive and verify it")
    p_restore.add_argument("--file", required=True, help="Path to the .zip archive")
    p_restore.add_argument("--to", required=True, help="Target directory to extract into")

    args = parser.parse_args()

    if args.command == "restore":
        restore_backup(Path(args.file), Path(args.to))
    else:
        create_backup()


if __name__ == "__main__":
    main()
