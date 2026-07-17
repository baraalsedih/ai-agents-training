"""Inventory report over the knowledge base: how many chunks per category,
the full list of open questions, and the full list of decisions — the two
most operationally useful lists for a founder reviewing their own archive.

Usage:
    python3 report.py            # print to screen
    python3 report.py --save     # also save as a dated Markdown file

compute_report_data() is also imported directly by webapp.py, so the CLI
flow below and the web UI flow share the exact same report logic.
"""

import argparse
import sys
import warnings
from collections import defaultdict
from datetime import date

warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_chroma import Chroma

import config


def collect_data():
    embeddings = config.get_embeddings()
    vectorstore = Chroma(
        collection_name=config.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(config.CHROMA_DIR),
    )
    raw = vectorstore.get(include=["metadatas", "documents"])
    return raw["metadatas"]


def compute_report_data(metadatas: list) -> dict:
    """Structured report data — used to render both the CLI text report
    and the web UI's JSON response."""
    total = len(metadatas)
    counts = defaultdict(int)
    by_source = defaultdict(int)
    open_questions = defaultdict(list)
    decisions = defaultdict(list)

    for meta in metadatas:
        category = meta.get("category", "unclassified")
        source = meta.get("source", "?")
        counts[category] += 1
        by_source[source] += 1
        if category == "open_question":
            open_questions[source].append(meta.get("summary", ""))
        elif category == "decision":
            decisions[source].append(meta.get("summary", ""))

    return {
        "total": total,
        "counts": dict(counts),
        "by_source": dict(sorted(by_source.items())),
        "open_questions": dict(sorted(open_questions.items())),
        "decisions": dict(sorted(decisions.items())),
    }


def render_text_report(data: dict) -> list:
    """Turns compute_report_data()'s dict into plain-text lines (also valid
    enough as simple Markdown, since every heading line is prefixed with '#')."""
    lines = []
    lines.append("# Knowledge Base Inventory Report")
    lines.append(f"Total indexed chunks: **{data['total']}**")
    lines.append("")

    lines.append("## Breakdown by category")
    for category in config.CATEGORIES + ["unclassified"]:
        label = config.CATEGORY_LABELS[category]
        lines.append(f"- {label}: {data['counts'].get(category, 0)}")
    lines.append("")

    lines.append("## Breakdown by source file")
    for source, n in data["by_source"].items():
        lines.append(f"- {source}: {n} chunk(s)")
    lines.append("")

    lines.append("## Open questions in your archive")
    if not data["open_questions"]:
        lines.append("No open questions classified yet.")
    else:
        for source, summaries in data["open_questions"].items():
            lines.append(f"### {source}")
            for summary in summaries:
                lines.append(f"- {summary}")
    lines.append("")

    lines.append("## Decisions recorded in your archive")
    if not data["decisions"]:
        lines.append("No decisions classified yet.")
    else:
        for source, summaries in data["decisions"].items():
            lines.append(f"### {source}")
            for summary in summaries:
                lines.append(f"- {summary}")

    return lines


def main():
    parser = argparse.ArgumentParser(description="Knowledge base inventory report")
    parser.add_argument("--save", action="store_true", help="Also save the report as a Markdown file")
    args = parser.parse_args()

    if not config.CHROMA_DIR.exists():
        print("❌ No knowledge base yet. Run ingest.py first.")
        sys.exit(1)

    incompatible = config.check_knowledge_base_compatibility()
    if incompatible:
        print(f"❌ {incompatible}")
        sys.exit(1)

    print("📊 Reading the knowledge base...")
    metadatas = collect_data()

    if not metadatas:
        print("⚠️  The knowledge base is empty — no chunks indexed yet.")
        return

    data = compute_report_data(metadatas)
    lines = render_text_report(data)
    print()
    for line in lines:
        print(line)

    if args.save:
        report_path = config.KNOWLEDGE_BASE_DIR / f"report_{date.today().isoformat()}.md"
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n💾 Report saved to: {report_path}")


if __name__ == "__main__":
    main()
