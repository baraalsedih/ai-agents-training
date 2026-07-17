"""Team -- Session 5. Single entry point for the whole multi-agent system.

Wires the supervisor's routing and quality-loop nodes together with the
three specialized agents into one LangGraph graph:

    START -> route -> (conditional) -> one of:
        call_source_analyst -> END
        call_consistency_auditor -> END
        call_researcher -> quality_review -> (conditional) -> call_researcher (once) or END
        direct_answer -> END

No checkpointer is needed for this graph itself: the only real pause-and-
resume point in the whole system (Session 4's human_approval interrupt())
lives inside the source-analysis agent's own subprocess and its own
checkpointer -- see agents/source_analyst.py's docstring for why it's
called as a subprocess rather than nested as a subgraph here.

Usage:
    python3 team.py                          # interactive loop
    python3 team.py --request "..."          # one request, non-interactive
    python3 team.py --draw                   # save the graph diagram and exit

Everything runs locally through Ollama -- no external API calls.
"""

import argparse
import sys
from pathlib import Path

from langgraph.graph import END, START, StateGraph

import supervisor
from supervisor import TeamState

# session6: tracing added -- labs/session6/ is a sibling directory, not an
# installed package, same import convention this lab already uses for
# labs/session3/ and labs/session4/.
SESSION6_DIR = Path(__file__).resolve().parent.parent / "session6"
sys.path.insert(0, str(SESSION6_DIR))
import tracing  # noqa: E402


def build_graph():
    graph = StateGraph(TeamState)

    graph.add_node("route", supervisor.route)
    graph.add_node("call_source_analyst", supervisor.call_source_analyst)
    graph.add_node("call_consistency_auditor", supervisor.call_consistency_auditor)
    graph.add_node("call_researcher", supervisor.call_researcher)
    graph.add_node("quality_review", supervisor.quality_review)
    graph.add_node("direct_answer", supervisor.direct_answer)

    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        supervisor.route_destination,
        {
            "analyze_document": "call_source_analyst",
            "consistency_check": "call_consistency_auditor",
            "research": "call_researcher",
            "direct_answer": "direct_answer",
        },
    )
    graph.add_edge("call_source_analyst", END)
    graph.add_edge("call_consistency_auditor", END)
    graph.add_edge("call_researcher", "quality_review")
    graph.add_conditional_edges(
        "quality_review",
        supervisor.route_after_quality_review,
        {"revise": "call_researcher", "done": END},
    )
    graph.add_edge("direct_answer", END)

    return graph.compile()


def run_once(app, user_request: str) -> None:
    initial_state: TeamState = {
        "user_request": user_request,
        "destination": "",
        "args": {},
        "result": "",
        "research_sources": [],
        "revision_count": 0,
        "quality_feedback": "",
    }
    # session6: tracing added -- opens the one operation that spans this
    # entire request, however many nodes/agents/revisions it takes; every
    # traced call underneath (route, the agents, quality_review) nests
    # into it automatically via tracing.py's contextvar.
    with tracing.operation("request", {"user_request": user_request}):
        final_state = app.invoke(initial_state)
    print("\n" + "=" * 70)
    print(final_state["result"])
    print("=" * 70)


def save_graph_diagram(app) -> None:
    # Mermaid text export only -- keeps this lab's "100% local" rule intact,
    # same reasoning as Session 4's agent.py --draw.
    out_path = Path(__file__).resolve().parent / "team_graph.mmd"
    out_path.write_text(app.get_graph().draw_mermaid(), encoding="utf-8")
    print(f"🖼️  Graph diagram saved to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Session 5 multi-agent team -- top-level entry point")
    parser.add_argument("--request", help="Run a single request non-interactively")
    parser.add_argument("--draw", action="store_true", help="Save the graph diagram (Mermaid text) and exit")
    args = parser.parse_args()

    app = build_graph()

    if args.draw:
        save_graph_diagram(app)
        return

    if args.request:
        run_once(app, args.request)
        return

    print("🧭 Session 5 team -- examples: 'analyze incoming/doc.md', 'check the archive for consistency', 'what is the status of the funding plan?'")
    print("   Type 'exit' to quit.")
    while True:
        try:
            user_request = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye 👋")
            break
        if not user_request:
            continue
        if user_request.lower() in ("exit", "quit"):
            print("Goodbye 👋")
            break
        run_once(app, user_request)


if __name__ == "__main__":
    main()
