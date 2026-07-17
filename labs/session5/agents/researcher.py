"""Research & report agent -- Session 5.

Turns one analytical question into a composed report: the question is
broken into a few focused sub-queries (query decomposition), each is
retrieved against the Session 3 knowledge base (with a category filter
when a sub-query is clearly scoped to one), and the results are woven into
a structured Markdown report where every claim cites its source chunk.

This is the "research and report on request" capability from the deeper
system requirements -- a step up from Session 3's ask.py, which answers a
single question with a single retrieval pass and no report file.

Usage:
    python3 researcher.py "What is the state of the funding plan?"

Everything runs locally through Ollama -- no external API calls.
"""

import argparse
import hashlib
import re
import sys
import warnings
from datetime import date
from pathlib import Path
from typing import Literal, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning)

SESSION3_DIR = Path(__file__).resolve().parent.parent.parent / "session3"
sys.path.insert(0, str(SESSION3_DIR))

import config as kb_config  # noqa: E402

from langchain_chroma import Chroma  # noqa: E402
from langchain_ollama import ChatOllama, OllamaEmbeddings  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

# session6: tracing added -- labs/session6/ is a sibling directory, not an
# installed package, same import convention this lab already uses for
# labs/session3/.
SESSION6_DIR = Path(__file__).resolve().parent.parent.parent / "session6"
sys.path.insert(0, str(SESSION6_DIR))
import tracing  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
RESEARCH_K = 4  # chunks retrieved per sub-query


class SubQuery(BaseModel):
    query: str = Field(description="A focused sub-question or search query derived from the founder's original question")
    category_filter: Optional[Literal["idea", "decision", "evidence", "open_question"]] = Field(
        default=None,
        description="Restrict retrieval to this category if the sub-question is clearly about one of them "
        "(e.g. specifically asking what was decided); otherwise null to search the whole archive",
    )


class QueryDecomposition(BaseModel):
    sub_queries: list[SubQuery] = Field(description="2 to 4 focused sub-queries that together cover the founder's original question")


DECOMPOSE_PROMPT = """A founder wants an analytical answer from their own strategic knowledge base archive. Break their question into 2-4 focused sub-questions/search queries that together would surface everything relevant to answering it well. If a sub-question is clearly about one specific category (idea, decision, evidence, or open_question) rather than the archive in general, set its category_filter to that category; otherwise leave it null.

Founder's question: {question}"""

COMPOSE_PROMPT = """You are writing an analytical research report for a founder, using ONLY the retrieved chunks below from their own knowledge base archive. Do not use outside knowledge.

Original question: {question}

Retrieved chunks (each tagged with its source file and category):
{context}

Write a Markdown report with exactly these sections, in this order:
## Summary
A 2-4 sentence direct answer to the original question.
## What We Know
The key points that answer the question, each ending with a citation like (Source: filename, category).
## Evidence
Concrete numbers, study results, or quotes from the archive relevant to the question, cited the same way. If none, say so.
## Related Decisions
Recorded decisions relevant to the question, cited the same way. If none, say so.
## Related Open Questions
Unresolved open questions from the archive that relate to this topic, cited the same way. If none, say so.
## Knowledge Limits
What the archive does NOT tell you about this question -- be specific about the gap, not just "more research is needed."

Every factual claim in every section except Knowledge Limits must end with a citation to its source chunk. If the retrieved chunks don't actually answer the question, say so plainly in the Summary instead of guessing."""


def build_resources():
    embeddings = OllamaEmbeddings(model=kb_config.EMBEDDING_MODEL)
    llm = ChatOllama(model=kb_config.CHAT_MODEL, temperature=0)
    vectorstore = Chroma(
        collection_name=kb_config.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(kb_config.CHROMA_DIR),
    )
    return embeddings, llm, vectorstore


def decompose(structured_llm, question: str) -> list:
    # session6: tracing added
    result = tracing.traced_llm_call(structured_llm, DECOMPOSE_PROMPT.format(question=question), agent="researcher", purpose="query_decomposition")
    return result.sub_queries


def retrieve(vectorstore, sub_queries: list, k: int = RESEARCH_K) -> list:
    """One retrieval pass per sub-query, pooled and de-duplicated (a chunk
    surfaced by two different sub-queries is only kept once)."""
    seen, pooled_docs = set(), []
    for sq in sub_queries:
        filter_dict = {"category": sq.category_filter} if sq.category_filter else None
        docs = vectorstore.similarity_search(sq.query, k=k, filter=filter_dict)
        # session6: tracing added
        tracing.log_retrieval(
            agent="researcher",
            query=sq.query,
            k=k,
            category_filter=sq.category_filter,
            sources=[{"source": d.metadata.get("source"), "category": d.metadata.get("category")} for d in docs],
        )
        for doc in docs:
            key = (doc.metadata.get("source"), doc.page_content[:60])
            if key not in seen:
                seen.add(key)
                pooled_docs.append(doc)
    return pooled_docs


def format_context(docs: list) -> str:
    blocks = []
    for i, d in enumerate(docs, 1):
        category = d.metadata.get("category", "unclassified")
        label = kb_config.CATEGORY_LABELS.get(category, "Unclassified")
        source = d.metadata.get("source", "?")
        blocks.append(f"[{i}] Source: {source} | Category: {label}\n{d.page_content}")
    return "\n\n".join(blocks)


def compose(llm, question: str, docs: list) -> str:
    prompt = COMPOSE_PROMPT.format(question=question, context=format_context(docs))
    # session6: tracing added
    response = tracing.traced_llm_call(llm, prompt, agent="researcher", purpose="compose_report")
    return response.content.strip()


def sources_list(docs: list) -> list:
    seen, result = set(), []
    for d in docs:
        source = d.metadata.get("source", "?")
        category = d.metadata.get("category", "unclassified")
        summary = d.metadata.get("summary", "")
        key = (source, summary)
        if key in seen:
            continue
        seen.add(key)
        result.append({"source": source, "category": category, "category_label": kb_config.CATEGORY_LABELS.get(category, "Unclassified"), "summary": summary})
    return result


def _slugify(question: str) -> str:
    latin = re.sub(r"[^a-zA-Z0-9]+", "_", question.strip().lower()).strip("_")
    short_hash = hashlib.sha1(question.encode("utf-8")).hexdigest()[:6]
    return f"{latin[:40]}_{short_hash}" if latin else f"q_{short_hash}"


def _save_report(question: str, report_body: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"research_{date.today().isoformat()}_{_slugify(question)}.md"
    header = f"# Research Report\n\nQuestion: {question}\nDate: {date.today().isoformat()}\n\n---\n\n"
    report_path.write_text(header + report_body + "\n", encoding="utf-8")
    return report_path


def run_research(question: str, feedback: Optional[str] = None) -> dict:
    """Top-level entry point, reused by both the CLI and supervisor.py.
    `feedback` carries the quality-review reviewer's notes when this is a
    one-shot revision pass (see supervisor.py's quality_review node)."""
    # session6: tracing added -- a no-op passthrough when called via
    # team.py (an operation is already open around supervisor.route()'s
    # app.invoke()); opens its own operation when this module runs
    # standalone (`python3 agents/researcher.py "question"`).
    with tracing.operation("research", {"question": question, "is_revision": bool(feedback)}):
        embeddings, llm, vectorstore = build_resources()
        structured_llm = llm.with_structured_output(QueryDecomposition)

        prompt_question = question
        if feedback:
            prompt_question = f"{question}\n\n(A previous draft of this report was reviewed and found lacking: {feedback} Address that in this revision.)"

        print("🧩 Decomposing the question into focused sub-queries...")
        sub_queries = decompose(structured_llm, prompt_question)
        for sq in sub_queries:
            scope = f" [category: {sq.category_filter}]" if sq.category_filter else ""
            print(f"   - {sq.query}{scope}")

        print(f"🔎 Retrieving relevant chunks for {len(sub_queries)} sub-quer{'y' if len(sub_queries) == 1 else 'ies'}...")
        docs = retrieve(vectorstore, sub_queries)
        print(f"   ✅ {len(docs)} unique chunk(s) retrieved")

        if not docs:
            report_body = "## Summary\nNo relevant chunks were found in the knowledge base for this question.\n"
        else:
            print("🤖 Composing the report...")
            report_body = compose(llm, question, docs)

        report_path = _save_report(question, report_body)
        print(f"✅ Report saved to: {report_path}")

        return {
            "report_path": report_path,
            "report_markdown": report_body,
            "sub_queries": [sq.query for sq in sub_queries],
            "sources": sources_list(docs),
        }


def main():
    parser = argparse.ArgumentParser(description="Session 5 research & report agent")
    parser.add_argument("question", nargs="?", help="The analytical question to research")
    args = parser.parse_args()

    if not kb_config.CHROMA_DIR.exists():
        print("❌ No knowledge base yet. Run labs/session3/ingest.py first.")
        sys.exit(1)

    question = args.question
    if not question:
        try:
            question = input("❓ Your research question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye 👋")
            sys.exit(0)

    if not question:
        print("No question given.")
        sys.exit(1)

    result = run_research(question)
    print()
    print(result["report_markdown"])


if __name__ == "__main__":
    main()
