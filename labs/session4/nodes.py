"""Node functions for the source-analysis agent (Session 4).

Each function is a plain Python function: it takes the shared AnalysisState
and returns a dict with ONLY the keys it updates -- LangGraph merges that
dict into the state before the next node runs. This is the same one-node,
one-responsibility rule from the Session 1 "Modularity" principle.

Session 3 already built a working knowledge-base pipeline (loading,
chunking, classification, Chroma storage, the manifest). This agent feeds
that SAME knowledge base rather than duplicating any of that logic, so the
loader, the classification prompt/model, and the manifest helpers are all
imported directly from labs/session3/.
"""

import json
import shutil
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import TypedDict

warnings.filterwarnings("ignore", category=DeprecationWarning)

# labs/session3/ is a sibling folder, not an installed package, so it has to
# be added to sys.path before its modules can be imported.
SESSION3_DIR = Path(__file__).resolve().parent.parent / "session3"
sys.path.insert(0, str(SESSION3_DIR))

import config as kb_config  # noqa: E402 -- Session 3's knowledge-base config
from ingest import (  # noqa: E402 -- reused, not re-implemented
    ChunkClassification,
    classify_chunk,
    file_hash,
    load_file,
    load_manifest,
    save_manifest,
)

from langchain_chroma import Chroma  # noqa: E402
from langchain_ollama import ChatOllama, OllamaEmbeddings  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402
from langgraph.types import interrupt  # noqa: E402


# ============================================================
# State -- the shared bag every node reads from and adds to.
# LangGraph inspects each node's real type hints at graph-build time (to
# infer input/output schemas), so this has to be a real importable class,
# not just a type-checking-only forward reference.
# ============================================================
class AnalysisState(TypedDict):
    file_path: str  # document being processed
    raw_text: str  # extracted text
    chunks: list  # split chunks: [{"index", "text"}, ...]
    classified: list  # chunks with category/confidence/summary tags
    low_confidence: list  # indices of chunks needing human review
    suggested_links: list  # proposed relations to existing knowledge
    approved: bool  # human approval status
    report: str  # final summary


# ------------------------------------------------------------------------
# Tunable thresholds for this agent specifically (Session 3's config.py is
# reused as-is above for models/paths; these two values only make sense
# here, so they live next to the code that uses them).
# ------------------------------------------------------------------------

# A classified chunk with confidence strictly below this goes to human_review
# instead of straight to suggest_links. Local 7-8B models classify with high
# confidence (0.9-1.0) even on fairly ordinary text; 0.85 catches the rarer
# cases where the model itself hedged below its usual range (e.g. text that
# mixes decision and idea language in the same passage).
LOW_CONFIDENCE_THRESHOLD = 0.85

# suggest_links proposes at most this many existing chunks per new chunk...
LINK_TOP_K = 2
# ...and only if their Chroma distance is below this cutoff (lower = more
# similar). This is a heuristic, not a certainty -- see the handbook.
LINK_MAX_DISTANCE = 0.42


def _label(category: str) -> str:
    return kb_config.CATEGORY_LABELS.get(category, category)


# ------------------------------------------------------------------------
# 1. extract_text
# ------------------------------------------------------------------------
def extract_text(state: AnalysisState) -> dict:
    path = Path(state["file_path"])
    print(f"\n🔎 extract_text node: reading {path.name}...")

    docs = load_file(path)
    raw_text = "\n\n".join(d.page_content for d in docs)

    print(f"   ✅ Read {len(raw_text):,} characters from {path.name}")
    return {"raw_text": raw_text}


# ------------------------------------------------------------------------
# 2. chunk
# ------------------------------------------------------------------------
def chunk(state: AnalysisState) -> dict:
    print("✂️  chunk node: splitting the text into chunks...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=kb_config.CHUNK_SIZE, chunk_overlap=kb_config.CHUNK_OVERLAP
    )
    texts = splitter.split_text(state["raw_text"])
    chunks = [{"index": i, "text": text} for i, text in enumerate(texts)]

    print(f"   ✅ {len(chunks)} chunk(s) (same settings as Session 3: {kb_config.CHUNK_SIZE}/{kb_config.CHUNK_OVERLAP})")
    return {"chunks": chunks}


# ------------------------------------------------------------------------
# 3. classify
# ------------------------------------------------------------------------
def classify(state: AnalysisState) -> dict:
    chunks = state["chunks"]
    print(f"🏷️  classify node: classifying {len(chunks)} chunk(s) locally...")

    llm = ChatOllama(model=kb_config.CHAT_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(ChunkClassification)

    classified = []
    low_confidence = []
    for c in chunks:
        result = classify_chunk(structured_llm, c["text"])
        entry = {
            "index": c["index"],
            "text": c["text"],
            "category": result["category"],
            "confidence": result["confidence"],
            "summary": result["one_line_summary"],
            "reviewed": False,
            "original_category": None,
        }
        classified.append(entry)
        flag = " ⚠️ low confidence" if result["confidence"] < LOW_CONFIDENCE_THRESHOLD else ""
        print(f"   Chunk {c['index']}: {_label(result['category'])} (confidence {result['confidence']:.2f}){flag}")
        if result["confidence"] < LOW_CONFIDENCE_THRESHOLD:
            low_confidence.append(c["index"])

    print(f"   ✅ Classification complete -- {len(low_confidence)} chunk(s) need human review")
    return {"classified": classified, "low_confidence": low_confidence}


def route_after_classify(state: AnalysisState) -> str:
    if state["low_confidence"]:
        return "human_review"
    return "suggest_links"


# ------------------------------------------------------------------------
# 4. human_review
# ------------------------------------------------------------------------
def human_review(state: AnalysisState) -> dict:
    classified = state["classified"]
    low_confidence = state["low_confidence"]
    print(f"\n🧑‍⚖️  human_review node: {len(low_confidence)} low-confidence chunk(s) need a quick look from you.")
    print("   Press Enter to accept the suggested category, or type the correct one (Idea/Decision/Evidence/Open Question).")

    label_to_category = {v.lower(): k for k, v in kb_config.CATEGORY_LABELS.items()}
    by_index = {c["index"]: c for c in classified}

    for idx in low_confidence:
        entry = by_index[idx]
        print(f"\n   --- Chunk {idx} (suggested: {_label(entry['category'])}, confidence {entry['confidence']:.2f}) ---")
        print(f"   {entry['text'][:220]}{'...' if len(entry['text']) > 220 else ''}")
        try:
            answer = input("   Your category (Enter to accept): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n⏸️  Stopped during review. Re-run the same command to restart from this stage.")
            raise SystemExit(0)
        if answer:
            category = label_to_category.get(answer.lower())
            if category:
                entry["original_category"] = entry["category"]
                entry["category"] = category
                print(f"   ✅ Category changed to: {_label(category)}")
            else:
                print("   ⚠️  Unknown category -- ignoring the edit and keeping the suggested classification.")
        entry["reviewed"] = True

    return {"classified": classified}


# ------------------------------------------------------------------------
# 5. suggest_links
# ------------------------------------------------------------------------
def suggest_links(state: AnalysisState) -> dict:
    print("\n🔗 suggest_links node: searching the current knowledge base for connections...")

    embeddings = OllamaEmbeddings(model=kb_config.EMBEDDING_MODEL)
    vectorstore = Chroma(
        collection_name=kb_config.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(kb_config.CHROMA_DIR),
    )

    suggested_links = []
    for entry in state["classified"]:
        results = vectorstore.similarity_search_with_score(entry["text"], k=LINK_TOP_K)
        for doc, score in results:
            if score > LINK_MAX_DISTANCE:
                continue
            suggested_links.append(
                {
                    "new_chunk_index": entry["index"],
                    "new_chunk_summary": entry["summary"],
                    "existing_source": doc.metadata.get("source", "?"),
                    "existing_category": doc.metadata.get("category", "unclassified"),
                    "existing_summary": doc.metadata.get("summary", ""),
                    "score": round(score, 4),
                }
            )

    print(f"   ✅ {len(suggested_links)} suggested link(s) with your current archive")
    return {"suggested_links": suggested_links}


# ------------------------------------------------------------------------
# 6. human_approval (the interrupt point)
# ------------------------------------------------------------------------
def _build_approval_payload(state: AnalysisState) -> dict:
    counts = {}
    for entry in state["classified"]:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1

    return {
        "file_name": Path(state["file_path"]).name,
        "chunk_count": len(state["classified"]),
        "counts": counts,
        "reviewed_count": sum(1 for e in state["classified"] if e["reviewed"]),
        "samples": [
            {"index": e["index"], "category": e["category"], "summary": e["summary"]}
            for e in state["classified"]
        ],
        "links": state["suggested_links"],
    }


def format_approval_summary(payload: dict) -> str:
    """Shared by the node (first run) and agent.py (resume after a restart)
    so the exact same summary is shown either way."""
    lines = []
    lines.append(f"\n📋 Analysis Summary — {payload['file_name']}")
    lines.append(f"   Total chunks: {payload['chunk_count']} ({payload['reviewed_count']} manually reviewed)")
    lines.append("   Breakdown by category:")
    for category, n in payload["counts"].items():
        lines.append(f"      {_label(category)}: {n}")

    lines.append("\n   Sample of classified chunks:")
    for s in payload["samples"][:5]:
        lines.append(f"      [{s['index']}] {_label(s['category'])} — {s['summary']}")

    lines.append(f"\n   🔗 Suggested links with your archive ({len(payload['links'])}):")
    if not payload["links"]:
        lines.append("      No suggested links above the similarity threshold.")
    for link in payload["links"][:8]:
        lines.append(
            f"      Chunk {link['new_chunk_index']} ↔ {link['existing_source']} "
            f"({_label(link['existing_category'])}, similarity {1 - link['score']:.2f}): {link['existing_summary']}"
        )
    return "\n".join(lines)


def human_approval(state: AnalysisState) -> dict:
    payload = _build_approval_payload(state)
    decision = interrupt(payload)
    approved = str(decision).strip().lower() in ("y", "yes")
    return {"approved": approved}


def route_after_approval(state: AnalysisState) -> str:
    if state["approved"]:
        return "ingest_to_kb"
    return "write_report"


# ------------------------------------------------------------------------
# 7. ingest_to_kb
# ------------------------------------------------------------------------
def ingest_to_kb(state: AnalysisState) -> dict:
    print("\n💾 ingest_to_kb node: ingesting into the Session 3 knowledge base...")

    source_path = Path(state["file_path"])
    # The file "graduates" into Session 3's my_documents/ so it becomes a
    # permanent, ordinary member of that folder -- if ingest.py runs again
    # later, it will see the file already indexed instead of "deleted".
    dest_path = kb_config.DOCUMENTS_DIR / source_path.name
    kb_config.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)
    rel = dest_path.name

    embeddings = OllamaEmbeddings(model=kb_config.EMBEDDING_MODEL)
    vectorstore = Chroma(
        collection_name=kb_config.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(kb_config.CHROMA_DIR),
    )

    texts, metadatas, ids = [], [], []
    for entry in state["classified"]:
        chunk_id = f"{rel}::{entry['index']}"
        texts.append(entry["text"])
        metadatas.append(
            {
                "source": rel,
                "category": entry["category"],
                "confidence": entry["confidence"],
                "summary": entry["summary"],
                "indexed_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        ids.append(chunk_id)

    vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    manifest = load_manifest()
    manifest["files"][rel] = {
        "hash": file_hash(dest_path),
        "chunk_count": len(ids),
        "chunk_ids": ids,
        "last_ingested": datetime.now().isoformat(timespec="seconds"),
    }
    save_manifest(manifest)

    links_path = Path(__file__).resolve().parent / "links.json"
    existing_links = []
    if links_path.exists():
        existing_links = json.loads(links_path.read_text(encoding="utf-8"))
    existing_links.append({"source_file": rel, "links": state["suggested_links"]})
    links_path.write_text(json.dumps(existing_links, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"   ✅ Ingested {len(ids)} chunk(s) into {kb_config.CHROMA_DIR}")
    print("   ✅ Updated manifest.json and links.json")
    return {}


# ------------------------------------------------------------------------
# 8. write_report
# ------------------------------------------------------------------------
def write_report(state: AnalysisState) -> dict:
    print("📝 write_report node: writing the final report...")

    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    file_name = Path(state["file_path"]).name
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [f"# Source Analysis Report — {file_name}", f"Date: {today}", ""]

    if not state["approved"]:
        lines.append("## ❌ Decision: Rejected")
        lines.append("No chunks from this document were added to the knowledge base.")
    else:
        lines.append("## ✅ Decision: Approved and Ingested")
        counts = {}
        for entry in state["classified"]:
            counts[entry["category"]] = counts.get(entry["category"], 0) + 1
        lines.append("\n### Breakdown by category")
        for category, n in counts.items():
            lines.append(f"- {_label(category)}: {n}")

        lines.append("\n### Suggested links with the current archive")
        if not state["suggested_links"]:
            lines.append("No suggested links.")
        for link in state["suggested_links"]:
            lines.append(
                f"- Chunk {link['new_chunk_index']} ↔ {link['existing_source']} "
                f"({_label(link['existing_category'])}): {link['existing_summary']}"
            )

    reviewed = [e for e in state["classified"] if e["reviewed"]]
    lines.append("\n### Human review decisions")
    if not reviewed:
        lines.append("No human review was needed -- every chunk was classified with sufficient confidence.")
    for entry in reviewed:
        if entry["original_category"]:
            lines.append(
                f"- Chunk {entry['index']}: changed from {_label(entry['original_category'])} "
                f"to {_label(entry['category'])}"
            )
        else:
            lines.append(f"- Chunk {entry['index']}: reviewed and the suggested classification was accepted ({_label(entry['category'])})")

    report_text = "\n".join(lines) + "\n"
    report_path = reports_dir / f"report_{today}_{Path(file_name).stem}.md"
    report_path.write_text(report_text, encoding="utf-8")

    print(f"   ✅ Report saved to: {report_path}")
    return {"report": report_text}
