"""Interactive Q&A over your knowledge base.

Retrieves the most relevant chunks for each question (optionally filtered
by category), then asks the local model to answer using ONLY those chunks.
A second, separate call then identifies which specific chunks the answer
actually draws from, so the sources shown are the ones the answer is
grounded in — not every chunk that was retrieved as a candidate. Splitting
generation and attribution into two focused calls is more reliable than
asking a small local model to do both in one shot (see comments below).

build_resources() and answer_question() are also imported directly by
webapp.py, so the CLI flow below and the web UI flow share the exact same
retrieval/answer logic.
"""

import re
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

import config

# This is the actual instruction sent to the local model for generation.
ANSWER_PROMPT = """Answer using ONLY the retrieved chunks below, from the user's own archive. Do not use any information from outside these chunks, or your general knowledge.

Rules:
- If you can't find a clear answer in the chunks, say exactly: "I don't know — I couldn't find an answer to this in your documents."
- Answer concisely and clearly, in the same language as the question.
- Write your entire answer in that one language only. Do not add a translation, a second version, or a "reference answer" in any other language.
- Do not add inline citations like "[Source: ...]" inside the answer — sources are tracked separately.

Retrieved chunks:
{context}

Question: {question}

Answer:"""

# A second, separate instruction that identifies which chunks an
# already-generated answer actually draws from. Kept as its own narrow
# call rather than folded into ANSWER_PROMPT above — a single call asking
# a small local model to compose prose AND track structured chunk numbers
# at the same time was unreliable in testing (the used_sources field came
# back empty for some questions no matter how many times it was retried).
# A focused, single-purpose call is the same pattern ingest.py's
# classify_chunk() already uses successfully.
ATTRIBUTION_PROMPT = """Below are numbered chunks and an answer that was generated from them. Identify which chunk number(s) the answer actually draws its information from.

Numbered chunks:
{context}

Answer:
{answer}

List only the chunk numbers the answer actually relies on. If the answer says it doesn't know / couldn't find the information, return an empty list."""

FILTER_COMMANDS = {"idea", "decision", "evidence", "open_question"}


class SourceAttribution(BaseModel):
    used_sources: list[int] = Field(
        description="Chunk numbers (the [N] labels above) that the answer actually draws its information "
        "from. Empty list if the answer says it doesn't know."
    )


# This archive and every expected answer are Arabic/English only, so any
# Chinese/Japanese/Korean characters in a response are leakage, never real
# content. Some local models (observed with qwen2.5) occasionally answer
# partly or entirely in CJK, inconsistently — a prompt rule alone doesn't
# fully prevent it (temperature=0 isn't perfectly deterministic with local
# quantized models), so answer_question() below retries generation a
# couple of times and falls back to stripping it out.
# Chinese/Japanese unified ideographs, hiragana/katakana, Hangul syllables.
_CJK_RANGES = "\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7a3"
_CJK_PUNCTUATION = "\u3000-\u303f\uff00-\uffef"  # CJK symbols + fullwidth forms block
_CJK_PATTERN = re.compile(f"[{_CJK_RANGES}]")

_NO_ANSWER_MARKERS = (
    "i don't know",
    "لا أعلم",
    "لا أعرف",
    "couldn't generate a clean answer",
    "تعذّر توليد إجابة واضحة",
)


def _has_cjk_leakage(text: str) -> bool:
    return bool(_CJK_PATTERN.search(text))


def _strip_cjk_leakage(text: str) -> str:
    """Last-resort cleanup if retries still produced CJK content: drop the
    CJK character runs (plus their punctuation) and tidy up the leftover
    whitespace."""
    cleaned = re.sub(f"[{_CJK_RANGES}{_CJK_PUNCTUATION}]+", "", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _looks_like_no_answer(text: str) -> bool:
    lowered = text.strip().lower()
    return any(marker in lowered or marker in text for marker in _NO_ANSWER_MARKERS)


# After stripping CJK leakage from a response that was mostly/entirely in
# the wrong script, what's left can be orphaned punctuation and digits
# rather than an actual sentence (e.g. a fully-Chinese answer reduces to
# something like '""152520'). Rather than show that, detect it and fall
# back to an honest "couldn't generate a clean answer" message.
_ALPHA_PATTERN = re.compile(r"[a-zA-Z\u0600-\u06ff]")
_MIN_ALPHA_CHARS = 15


def _looks_garbled(text: str) -> bool:
    return len(_ALPHA_PATTERN.findall(text)) < _MIN_ALPHA_CHARS


def _generation_failure_message(question: str) -> str:
    if re.search(r"[\u0600-\u06ff]", question):
        return "تعذّر توليد إجابة واضحة لهذا السؤال — جرّب إعادة صياغته أو اسأله مرة أخرى."
    return "Couldn't generate a clean answer to this question — try rephrasing it or asking again."


def build_resources():
    """Builds the (llm, vectorstore) tuple used by both the CLI flow and
    the web UI."""
    embeddings = config.get_embeddings()
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


def _generate_answer(llm, prompt: str, question: str) -> str:
    """Step 1: plain-text generation, with CJK-leakage retry.

    The first attempt reuses the caller's llm (temperature=0, the most
    reliable setting when it works). But some questions make a model
    answer entirely in the wrong script *deterministically* — observed
    with qwen2.5 answering fully in Chinese for certain phrasings, the
    exact same Chinese text on every attempt. Retrying at temperature=0
    would just reproduce the identical broken answer forever, so retries
    after the first use a higher temperature to actually get a different
    sample instead of repeating the same failure.

    If every attempt still comes back in the wrong script, stripping a
    mostly-CJK response leaves orphaned punctuation/digits, not a real
    answer — that gets detected and replaced with an honest failure
    message instead of showing the leftover garbage."""
    answer = None
    last_content = ""
    for attempt, temperature in enumerate((0, 0.4, 0.8)):
        model = llm if attempt == 0 else ChatOllama(model=llm.model, temperature=temperature)
        response = model.invoke(prompt)
        last_content = response.content.strip()
        if not _has_cjk_leakage(last_content):
            answer = last_content
            break
    if answer is None:
        cleaned = _strip_cjk_leakage(last_content)
        answer = _generation_failure_message(question) if _looks_garbled(cleaned) else cleaned
    return answer


def _attribute_sources(llm, docs, answer: str) -> list:
    """Step 2: a narrow, separate call that only identifies which chunks
    the already-generated answer draws from. Falls back to "all retrieved
    chunks" if this keeps failing, rather than showing nothing. Varies
    temperature across retries for the same reason _generate_answer()
    does — a bad result at temperature=0 repeats identically forever."""
    if _looks_like_no_answer(answer):
        return []

    prompt = ATTRIBUTION_PROMPT.format(context=format_context(docs), answer=answer)

    for attempt, temperature in enumerate((0, 0.4, 0.8)):
        model = llm if attempt == 0 else ChatOllama(model=llm.model, temperature=temperature)
        try:
            result = model.with_structured_output(SourceAttribution).invoke(prompt)
        except Exception:
            continue
        used = [docs[i - 1] for i in result.used_sources if 1 <= i <= len(docs)]
        if used:
            return used

    # Couldn't reliably identify specific sources — show everything that
    # was retrieved rather than showing no sources for a real answer.
    return docs


def answer_question(llm, vectorstore, question: str, category_filter: str = None) -> dict:
    """Runs one retrieval + generation + attribution cycle. Returns a dict
    with answer, sources (only the chunks the answer actually draws
    from — not every chunk retrieved as a candidate), and whether any
    chunks were found at all."""
    filter_dict = {"category": category_filter} if category_filter else None
    docs = vectorstore.similarity_search(question, k=config.RETRIEVAL_K, filter=filter_dict)

    if not docs:
        return {"answer": None, "sources": [], "found": False}

    prompt = ANSWER_PROMPT.format(context=format_context(docs), question=question)
    answer = _generate_answer(llm, prompt, question)
    used_docs = _attribute_sources(llm, docs, answer)

    return {"answer": answer, "sources": sources_list(used_docs), "found": True}


def main():
    if not config.CHROMA_DIR.exists():
        print("❌ No knowledge base yet. Run ingest.py first.")
        sys.exit(1)

    incompatible = config.check_knowledge_base_compatibility()
    if incompatible:
        print(f"❌ {incompatible}")
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
        if not result["sources"]:
            print("   (none used)")
        for s in result["sources"]:
            print(f"   - {s['source']} — {s['category_label']} — {s['summary']}")


if __name__ == "__main__":
    main()
