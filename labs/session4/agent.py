"""Source-analysis agent -- Session 4.

Reads one new document, walks it through extraction, chunking,
classification, an optional human review of low-confidence chunks, a
link-suggestion step against the Session 3 knowledge base, a human
approval checkpoint, and finally ingestion into that same knowledge base.

Usage:
    python3 agent.py incoming/<file>          # run (or resume) the agent
    python3 agent.py incoming/<file> --draw   # also save the graph diagram

Everything runs locally through Ollama -- no external API calls.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

import nodes
from nodes import AnalysisState  # the shared state bag -- defined once, next to the nodes that fill it

CHECKPOINT_DB = Path(__file__).resolve().parent / "checkpoints.sqlite"


# ============================================================
# Graph wiring -- exactly the layout designed on paper first:
# START -> extract_text -> chunk -> classify -> (branch) ->
#   human_review or suggest_links -> suggest_links (if reviewed) ->
#   human_approval [pause] -> (branch) -> ingest_to_kb or (skip) ->
#   write_report -> END
# ============================================================
def build_graph():
    graph = StateGraph(AnalysisState)

    graph.add_node("extract_text", nodes.extract_text)
    graph.add_node("chunk", nodes.chunk)
    graph.add_node("classify", nodes.classify)
    graph.add_node("human_review", nodes.human_review)
    graph.add_node("suggest_links", nodes.suggest_links)
    graph.add_node("human_approval", nodes.human_approval)
    graph.add_node("ingest_to_kb", nodes.ingest_to_kb)
    graph.add_node("write_report", nodes.write_report)

    graph.add_edge(START, "extract_text")
    graph.add_edge("extract_text", "chunk")
    graph.add_edge("chunk", "classify")

    graph.add_conditional_edges(
        "classify",
        nodes.route_after_classify,
        {"human_review": "human_review", "suggest_links": "suggest_links"},
    )
    graph.add_edge("human_review", "suggest_links")
    graph.add_edge("suggest_links", "human_approval")

    graph.add_conditional_edges(
        "human_approval",
        nodes.route_after_approval,
        {"ingest_to_kb": "ingest_to_kb", "write_report": "write_report"},
    )
    graph.add_edge("ingest_to_kb", "write_report")
    graph.add_edge("write_report", END)

    # SqliteSaver (not the in-memory saver) so a paused run at human_approval
    # survives closing the terminal entirely -- re-running the same command
    # later picks the run back up exactly where it stopped.
    conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return graph.compile(checkpointer=checkpointer)


def thread_id_for(file_path: Path) -> str:
    # One thread per document name -- re-running the agent on the same
    # incoming file resumes that document's run instead of starting a new one.
    return f"analyze::{file_path.stem}"


def ask_approval_decision() -> str:
    try:
        return input("\n✅ Do you approve ingesting this document into the knowledge base? (y/n): ").strip()
    except (EOFError, KeyboardInterrupt):
        # The run is already saved at the interrupt point (that's the whole
        # point of using interrupt() + a persistent checkpointer) -- closing
        # here loses nothing. Re-running the same command later resumes it.
        print("\n\n⏸️  Stopped while waiting for your decision. The analysis is saved -- run the same command again to resume it.")
        sys.exit(0)


def run(app, file_path: Path) -> None:
    config = {"configurable": {"thread_id": thread_id_for(file_path)}}
    snapshot = app.get_state(config)

    if snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
        # A previous run stopped right at human_approval -- possibly in a
        # process that has since closed. Rebuild the same summary from the
        # saved interrupt payload instead of re-running the graph blind.
        print(f"🔁 Found a previous analysis of {file_path.name} paused and waiting for your approval -- resuming from there.")
        payload = snapshot.tasks[0].interrupts[0].value
        print(nodes.format_approval_summary(payload))
        decision = ask_approval_decision()
        result = app.invoke(Command(resume=decision), config)
    elif snapshot.next:
        # The graph has pending work but never reached the interrupt (e.g.
        # the process was killed mid-node) -- simply retry that node.
        print(f"🔁 Found a previous run of {file_path.name} paused mid-way -- resuming from where it stopped.")
        result = app.invoke(None, config)
    elif snapshot.values:
        # This thread already ran to completion (approved or rejected).
        print(f"✅ {file_path.name} was already fully analyzed. Check its report inside reports/.")
        return
    else:
        initial_state: AnalysisState = {
            "file_path": str(file_path),
            "raw_text": "",
            "chunks": [],
            "classified": [],
            "low_confidence": [],
            "suggested_links": [],
            "approved": False,
            "report": "",
        }
        result = app.invoke(initial_state, config)

    if isinstance(result, dict) and "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print(nodes.format_approval_summary(payload))
        decision = ask_approval_decision()
        result = app.invoke(Command(resume=decision), config)

    if result.get("approved"):
        print("\n🎉 Analysis and ingestion completed successfully.")
    else:
        print("\n🛑 Ingestion rejected -- nothing was added to the knowledge base.")


def save_graph_diagram(app) -> None:
    # Mermaid text export only -- draw_mermaid_png() calls a public API by
    # default, which would break the "100% local, no external calls" rule
    # this whole lab follows. The .mmd text is viewable in any Mermaid
    # renderer (e.g. VS Code's built-in Markdown preview) with no network.
    mermaid_text = app.get_graph().draw_mermaid()
    out_path = Path(__file__).resolve().parent / "agent_graph.mmd"
    out_path.write_text(mermaid_text, encoding="utf-8")
    print(f"🖼️  Graph diagram saved to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Session 4 source-analysis agent")
    parser.add_argument("file", nargs="?", help="Path to the document to analyze (e.g. incoming/doc.md)")
    parser.add_argument("--draw", action="store_true", help="Save the graph diagram (Mermaid text) and exit")
    args = parser.parse_args()

    app = build_graph()

    if args.draw:
        save_graph_diagram(app)
        return

    if not args.file:
        parser.error("the following argument is required: file")

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    run(app, file_path)


if __name__ == "__main__":
    main()
