"""Supervisor -- Session 5.

The routing and quality-loop logic for the multi-agent team: classifies
each founder request into a destination agent, extracts the arguments that
agent needs, calls it, and -- for the researcher specifically -- reviews
its output once before handing it back, requesting exactly one revision if
something is missing.

TeamState is the shared bag that flows through every node in team.py's
graph, following the same one-node-one-responsibility pattern as Session
4's AnalysisState.
"""

import sys
import warnings
from pathlib import Path
from typing import Literal, Optional, TypedDict

warnings.filterwarnings("ignore", category=DeprecationWarning)

SESSION3_DIR = Path(__file__).resolve().parent.parent / "session3"
sys.path.insert(0, str(SESSION3_DIR))
import config as kb_config  # noqa: E402

from langchain_ollama import ChatOllama  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents import consistency_auditor, researcher, source_analyst  # noqa: E402

# session6: tracing added -- labs/session6/ is a sibling directory, not an
# installed package, same import convention this lab already uses for
# labs/session3/.
SESSION6_DIR = Path(__file__).resolve().parent.parent / "session6"
sys.path.insert(0, str(SESSION6_DIR))
import tracing  # noqa: E402

MAX_REVISIONS = 1  # quality loop runs at most once, to bound cost/latency


class TeamState(TypedDict):
    user_request: str
    destination: str  # "analyze_document" | "consistency_check" | "research" | "direct_answer"
    args: dict
    result: str
    research_sources: list
    revision_count: int
    quality_feedback: str


# ------------------------------------------------------------------------
# route
# ------------------------------------------------------------------------
class RouteDecision(BaseModel):
    destination: Literal["analyze_document", "consistency_check", "research", "direct_answer"] = Field(
        description="analyze_document: ingest a new document into the knowledge base. "
        "consistency_check: audit the archive itself for duplicates/contradictions/gaps/terminology. "
        "research: answer an analytical question by researching across the archive. "
        "direct_answer: the request is not about this knowledge-base system at all."
    )
    file_path: Optional[str] = Field(default=None, description="For analyze_document: the file path or filename mentioned in the request")
    question: Optional[str] = Field(default=None, description="For research: the founder's question, restated clearly")
    category_filter: Optional[Literal["idea", "decision", "evidence", "open_question"]] = Field(
        default=None, description="For consistency_check: restrict the audit to this category if one is explicitly named"
    )


ROUTE_PROMPT = """You are the supervisor of a multi-agent system that manages ONE specific founder's strategic knowledge base (their own business archive: ideas, decisions, evidence, open questions about their own startup). Classify the founder's request into exactly one destination:

- analyze_document: the founder wants to add/ingest a new document into the knowledge base (a file path or filename is mentioned)
- consistency_check: the founder wants the archive itself checked for duplicate content, contradictions, unresolved gaps, or inconsistent terminology
- research: the founder is asking an analytical question that should be answered by researching THEIR OWN ARCHIVE specifically (e.g. "what is the status of our X", "summarize our Y", "do we have conflicting decisions about Z") -- it must plausibly be answerable from a business archive about their own startup
- direct_answer: anything that is NOT a request to research this specific founder's own business archive -- general knowledge trivia (e.g. "what is the capital of France"), small talk, requests about unrelated topics, coding help, or anything this narrow system cannot do

When in doubt between research and direct_answer, ask: could the answer possibly live inside a small startup's internal notes/decisions/evidence archive? If clearly not (general world facts, unrelated domains), choose direct_answer.

Examples:
- "What is the status of our funding plan?" -> research
- "Do we have any conflicting pricing decisions?" -> research
- "What is the capital of France?" -> direct_answer (general knowledge, not in any business archive)
- "Write me a poem about spring" -> direct_answer (unrelated task)
- "What's the weather like today?" -> direct_answer (general knowledge, not in any business archive)

Founder's request: {user_request}

Extract any relevant arguments: a file path for analyze_document, a clearly restated question for research, or a category filter for consistency_check if one is explicitly named."""


def route(state: TeamState) -> dict:
    llm = ChatOllama(model=kb_config.CHAT_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(RouteDecision)
    # session6: tracing added
    decision = tracing.traced_llm_call(
        structured_llm, ROUTE_PROMPT.format(user_request=state["user_request"]), agent="supervisor", purpose="route_classification"
    )

    print(f"🎯 Supervisor: classified this as '{decision.destination}'.", flush=True)
    tracing.log_decision(node="route", choice=decision.destination)  # session6: tracing added

    args = {}
    if decision.file_path:
        args["file_path"] = decision.file_path
    if decision.question:
        args["question"] = decision.question
    if decision.category_filter:
        args["category_filter"] = decision.category_filter

    return {"destination": decision.destination, "args": args, "revision_count": 0, "quality_feedback": ""}


def route_destination(state: TeamState) -> str:
    return state["destination"]


# ------------------------------------------------------------------------
# call_source_analyst
# ------------------------------------------------------------------------
def call_source_analyst(state: TeamState) -> dict:
    file_path = state["args"].get("file_path") or state["user_request"]
    result = source_analyst.run_source_analyst(file_path)
    return {"result": result["message"]}


# ------------------------------------------------------------------------
# call_consistency_auditor
# ------------------------------------------------------------------------
def call_consistency_auditor(state: TeamState) -> dict:
    category_filter = state["args"].get("category_filter")
    # auto_confirm=True: the founder already expressed clear intent through
    # the routed request, so the supervisor doesn't re-prompt for the y/n
    # confirmation consistency_auditor.py's own standalone CLI would show.
    result = consistency_auditor.run_consistency_check(category_filter=category_filter, auto_confirm=True)
    counts = result["counts"]
    summary = (
        f"Consistency audit complete ({result['report_path']}):\n"
        f"- {counts.get('duplicates', 0)} duplicate(s)\n"
        f"- {counts.get('contradictions', 0)} contradiction(s)\n"
        f"- {counts.get('gaps', 0)} gap(s) (open questions with no resolving decision/evidence nearby)\n"
        f"- {counts.get('glossary', 0)} terminology cluster(s) proposed in glossary.json\n\n"
        f"{result['report_markdown']}"
    )
    return {"result": summary}


# ------------------------------------------------------------------------
# call_researcher
# ------------------------------------------------------------------------
def call_researcher(state: TeamState) -> dict:
    question = state["args"].get("question") or state["user_request"]
    feedback = state.get("quality_feedback") or None
    result = researcher.run_research(question, feedback=feedback)
    return {
        "result": result["report_markdown"],
        "research_sources": result["sources"],
        "args": {**state["args"], "question": question},
    }


# ------------------------------------------------------------------------
# quality_review -- the supervisor wears the reviewer hat for one pass
# ------------------------------------------------------------------------
class QualityJudgment(BaseModel):
    answers_question: bool = Field(description="True if the report's Summary section directly answers the founder's original question")
    all_claims_sourced: bool = Field(description="True if every factual claim in the report is backed by a citation to a source chunk")
    feedback: str = Field(description="If either check fails, one or two concrete, actionable sentences for the researcher to address; otherwise an empty string")


QUALITY_PROMPT = """You are reviewing a research report before it is delivered to a founder.

Original question: {question}

Report:
{report}

Number of distinct sources cited: {source_count}

Check: (1) does the Summary section directly answer the original question? (2) is every factual claim backed by a source citation? Give one or two concrete, actionable sentences of feedback only if either check fails; otherwise leave feedback empty."""


def quality_review(state: TeamState) -> dict:
    llm = ChatOllama(model=kb_config.CHAT_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(QualityJudgment)
    # session6: tracing added
    judgment = tracing.traced_llm_call(
        structured_llm,
        QUALITY_PROMPT.format(
            question=state["args"].get("question", state["user_request"]),
            report=state["result"],
            source_count=len(state.get("research_sources") or []),
        ),
        agent="supervisor",
        purpose="quality_review",
    )
    passed = judgment.answers_question and judgment.all_claims_sourced

    if passed:
        print("🔍 Supervisor (quality review): passed.")
        tracing.log_decision(node="quality_review", choice="passed")  # session6: tracing added
        return {"quality_feedback": ""}

    # A failed review must always carry non-empty feedback -- route_after_
    # quality_review uses truthiness of quality_feedback to decide whether
    # to loop back, so an empty string here would silently be treated as
    # "passed" and the revision would never actually happen (observed
    # during testing: the local model sometimes fails both checks but still
    # returns feedback="").
    reasons = []
    if not judgment.answers_question:
        reasons.append("the Summary does not directly answer the original question")
    if not judgment.all_claims_sourced:
        reasons.append("not every factual claim is backed by a source citation")
    feedback = judgment.feedback.strip() or f"Needs improvement: {'; '.join(reasons)}."

    if state["revision_count"] >= MAX_REVISIONS:
        print(f"🔍 Supervisor (quality review): still incomplete after {MAX_REVISIONS} revision(s) -- delivering with a caveat.")
        tracing.log_decision(node="quality_review", choice="delivered_with_caveat", extra={"feedback": feedback})  # session6: tracing added
        note = f"\n\n---\n⚠️ Quality review note: this report may still be incomplete -- {feedback}"
        return {"result": state["result"] + note, "quality_feedback": ""}

    print(f"🔍 Supervisor (quality review): needs revision -- {feedback}")
    tracing.log_decision(node="quality_review", choice="revise", extra={"feedback": feedback})  # session6: tracing added
    return {"revision_count": state["revision_count"] + 1, "quality_feedback": feedback}


def route_after_quality_review(state: TeamState) -> str:
    return "revise" if state["quality_feedback"] else "done"


# ------------------------------------------------------------------------
# direct_answer -- polite decline for anything outside the KB system's scope
# ------------------------------------------------------------------------
DIRECT_ANSWER_MESSAGE = (
    "This system manages a founder's strategic knowledge base -- it can ingest a new document, "
    "audit the archive for consistency, or research a question across it. That request doesn't fit "
    "any of those, so there's nothing for the team to do here."
)


def direct_answer(state: TeamState) -> dict:
    print("🎯 Supervisor: this request is outside the knowledge-base system's scope.")
    return {"result": DIRECT_ANSWER_MESSAGE}
