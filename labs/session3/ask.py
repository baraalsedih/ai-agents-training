"""Interactive Q&A over your knowledge base.

Retrieves the most relevant chunks for each question (optionally filtered
by category), then asks the local model to answer using ONLY those chunks,
citing its sources. Everything runs locally through Ollama.

build_resources() and answer_question() are also imported directly by
webapp.py, so the CLI flow below and the web UI flow share the exact same
retrieval/answer logic.
"""

import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

import config

# This is the actual instruction sent to the local model.
ANSWER_PROMPT = """Answer using ONLY the retrieved chunks below, from the user's own archive. Do not use any information from outside these chunks, or your general knowledge.

Rules:
- If you can't find a clear answer in the chunks, say exactly: "I don't know — I couldn't find an answer to this in your documents."
- Cite the source file for every key fact you use in your answer.
- Answer concisely and clearly, in the same language as the question.

Retrieved chunks:
{context}

Question: {question}

Answer:"""

FILTER_COMMANDS = {"idea", "decision", "evidence", "open_question"}


def build_resources():
    """Builds the (llm, vectorstore) tuple used by both the CLI flow and
    the web UI."""
    embeddings = OllamaEmbeddings(model=config.EMBEDDING_MODEL)
    llm = ChatOllama(model=config.CHAT_MODEL, temperature=0)
    vectorstore = Chroma(
        collection_name=config.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(config.CHROMA_DIR),
    )
    return llm, vectorstore


def format_context(docs) -> str:
    blocks = []
    for i, d in enumerate(docs, 1):
        category = d.metadata.get("category", "unclassified")
        label = config.CATEGORY_LABELS.get(category, "Unclassified")
        source = d.metadata.get("source", "?")
        blocks.append(f"[{i}] Source: {source} | Category: {label}\n{d.page_content}")
    return "\n\n".join(blocks)


def sources_list(docs) -> list:
    """De-duplicated source list for display. Returns the raw category key
    (e.g. "decision") plus its English label, so callers can render either
    the CLI's English label or translate the raw key themselves (the web
    UI shows these to the user in Arabic — see web/script.js)."""
    seen = set()
    result = []
    for d in docs:
        source = d.metadata.get("source", "?")
        category = d.metadata.get("category", "unclassified")
        label = config.CATEGORY_LABELS.get(category, "Unclassified")
        summary = d.metadata.get("summary", "")
        key = (source, summary)
        if key in seen:
            continue
        seen.add(key)
        result.append({"source": source, "category": category, "category_label": label, "summary": summary})
    return result


def answer_question(llm, vectorstore, question: str, category_filter: str = None) -> dict:
    """Runs one retrieval + generation cycle. Returns a dict with
    answer, sources, and whether any chunks were found at all."""
    filter_dict = {"category": category_filter} if category_filter else None
    docs = vectorstore.similarity_search(question, k=config.RETRIEVAL_K, filter=filter_dict)

    if not docs:
        return {"answer": None, "sources": [], "found": False}

    prompt = ANSWER_PROMPT.format(context=format_context(docs), question=question)
    response = llm.invoke(prompt)

    return {"answer": response.content.strip(), "sources": sources_list(docs), "found": True}


def main():
    if not config.CHROMA_DIR.exists():
        print("❌ No knowledge base yet. Run ingest.py first.")
        sys.exit(1)

    print("🔎 Knowledge Base Query Tool — Session 3")
    print("Type a question directly, or use one of these commands:")
    print("   filter: decision   /   filter: idea   /   filter: evidence   /   filter: open_question")
    print("   clear filter                                                — remove the active filter")
    print("   exit                                                        — quit")

    llm, vectorstore = build_resources()
    active_filter = None

    while True:
        try:
            query = input("\n❓ Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye 👋")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            print("Goodbye 👋")
            break

        if query.lower().startswith("filter:"):
            category = query.split(":", 1)[1].strip().lower().replace(" ", "_")
            if category in FILTER_COMMANDS:
                active_filter = category
                label = config.CATEGORY_LABELS[category]
                print(f"✅ Filter set to: {label} — search is now restricted to this category only.")
            else:
                available = ", ".join(config.CATEGORY_LABELS[c] for c in config.CATEGORIES)
                print(f"⚠️  Unknown category. Available categories: {available}")
            continue

        if query.lower() == "clear filter":
            active_filter = None
            print("✅ Filter cleared — searching the whole archive again.")
            continue

        print("🔎 Searching your archive...")
        result = answer_question(llm, vectorstore, query, active_filter)

        if not result["found"]:
            scope = f" within category '{config.CATEGORY_LABELS[active_filter]}'" if active_filter else ""
            print(f"⚠️  No relevant chunks found{scope}.")
            continue

        print("\n💬 Answer:")
        print(result["answer"])

        print("\n📚 Sources:")
        for s in result["sources"]:
            print(f"   - {s['source']} — {s['category_label']} — {s['summary']}")


if __name__ == "__main__":
    main()
