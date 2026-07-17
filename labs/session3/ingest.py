"""Reads every supported file in my_documents/, splits it into chunks,
classifies each chunk into one of four categories using a local LLM, and
indexes everything into a local Chroma vector store.

Incremental by design: manifest.json tracks a hash per source file, so
re-running this script only re-processes files that are new or changed.
Everything runs locally through Ollama — no external API calls.

The core functions here (scan_documents, build_resources, run_ingestion)
are also imported directly by webapp.py, so the CLI flow below and the
web UI flow both share the exact same ingestion logic.
"""

import hashlib
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Literal

warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_chroma import Chroma
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

import config

# This is the actual instruction sent to the local model — see handbook
# chapter 3 for the full explanation. English instructions work fine on
# non-English (e.g. Arabic) source text.
CLASSIFICATION_PROMPT = """You are an assistant specialized in classifying chunks from a founder's strategic archive.
Read the chunk below and classify it into exactly one of these four categories:

- idea: a proposal or vision that hasn't been decided yet. Example: "We might want to target the Gulf market first."
- decision: something that has actually been adopted, a final call was made. Example: "We decided to delay launch to Q2."
- evidence: a number, study, quote, or concrete result. Example: "The survey showed 62% of the sample are willing to pay monthly."
- open_question: an unresolved point that still needs an answer. Example: "Do we need a separate business license in every country?"

Chunk:
\"\"\"
{text}
\"\"\"

Pick the single best category, estimate your confidence from 0 to 1, and write a one-sentence summary of the chunk."""


class ChunkClassification(BaseModel):
    category: Literal["idea", "decision", "evidence", "open_question"] = Field(
        description="The single category that best fits this chunk"
    )
    confidence: float = Field(description="Confidence from 0.0 to 1.0")
    one_line_summary: str = Field(description="One short sentence summarizing the chunk")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest() -> dict:
    if config.MANIFEST_PATH.exists():
        return json.loads(config.MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"files": {}}


def save_manifest(manifest: dict) -> None:
    manifest["embedding_model"] = config.EMBEDDING_MODEL
    config.MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_file(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(path))
    elif suffix == ".docx":
        loader = Docx2txtLoader(str(path))
    else:
        loader = TextLoader(str(path), encoding="utf-8")
    return loader.load()


def classify_chunk(structured_llm, text: str) -> dict:
    try:
        result = structured_llm.invoke(CLASSIFICATION_PROMPT.format(text=text))
        return {
            "category": result.category,
            "confidence": result.confidence,
            "one_line_summary": result.one_line_summary,
        }
    except Exception as e:
        return {"category": "unclassified", "confidence": 0.0, "one_line_summary": "", "error": str(e)}


def scan_documents() -> dict:
    """Looks at my_documents/ vs. the manifest and figures out what changed.

    Returns a dict with: files, manifest, known, to_process, removed_rel_paths.
    Raises FileNotFoundError if the documents folder itself is missing.
    """
    if not config.DOCUMENTS_DIR.exists():
        raise FileNotFoundError(str(config.DOCUMENTS_DIR))

    files = sorted(
        p
        for p in config.DOCUMENTS_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in config.SUPPORTED_EXTENSIONS
    )

    manifest = load_manifest()
    known = manifest["files"]

    to_process = []
    current_rel_paths = set()
    for path in files:
        rel = str(path.relative_to(config.DOCUMENTS_DIR))
        current_rel_paths.add(rel)
        h = file_hash(path)
        if rel not in known or known[rel]["hash"] != h:
            to_process.append((path, rel, h))

    removed_rel_paths = [rel for rel in known if rel not in current_rel_paths]

    return {
        "files": files,
        "manifest": manifest,
        "known": known,
        "to_process": to_process,
        "removed_rel_paths": removed_rel_paths,
    }


def build_resources():
    """Builds the (embeddings, llm, structured_llm, vectorstore) tuple used
    by both the CLI flow and the web UI."""
    embeddings = config.get_embeddings()
    llm = ChatOllama(model=config.CHAT_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(ChunkClassification)
    vectorstore = Chroma(
        collection_name=config.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(config.CHROMA_DIR),
    )
    return embeddings, llm, structured_llm, vectorstore


def count_pending_chunks(to_process: list) -> int:
    """Splits every pending file just to count chunks, for a time estimate."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )
    total = 0
    for path, rel, h in to_process:
        docs = load_file(path)
        total += len(splitter.split_documents(docs))
    return total


def run_ingestion(scan: dict, vectorstore, structured_llm, on_progress=None) -> dict:
    """Performs the actual chunking, classification, and storage.

    on_progress(message: str), if given, is called for each log-worthy step
    (used by the CLI to print, and by webapp.py to collect a log list).
    Returns the classification counts dict. Mutates and saves the manifest.
    """
    def log(msg):
        if on_progress:
            on_progress(msg)

    manifest = scan["manifest"]
    known = scan["known"]
    to_process = scan["to_process"]
    removed_rel_paths = scan["removed_rel_paths"]

    for rel in removed_rel_paths:
        old_ids = known[rel].get("chunk_ids", [])
        if old_ids:
            vectorstore.delete(ids=old_ids)
        del known[rel]
        log(f"Removed chunks for deleted file: {rel}")

    # Clean up the OLD chunks of any changed file before re-adding new ones,
    # so an edited document never leaves stale chunks behind.
    for path, rel, h in to_process:
        if rel in known:
            old_ids = known[rel].get("chunk_ids", [])
            if old_ids:
                vectorstore.delete(ids=old_ids)

    counts = {c: 0 for c in config.CATEGORIES}
    counts["unclassified"] = 0

    if to_process:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
        )

        all_chunks = []  # (rel_path, file_hash, chunk_index, chunk_document)
        for path, rel, h in to_process:
            log(f"Reading {path.name}...")
            docs = load_file(path)
            chunks = splitter.split_documents(docs)
            log(f"  {len(chunks)} chunk(s)")
            for i, chunk in enumerate(chunks):
                all_chunks.append((rel, h, i, chunk))

        total = len(all_chunks)
        texts, metadatas, ids = [], [], []
        files_chunk_ids: dict = {}

        for idx, (rel, h, i, chunk) in enumerate(all_chunks, 1):
            log(f"Classifying {idx}/{total}: {rel} (chunk {i})...")
            result = classify_chunk(structured_llm, chunk.page_content)
            if result.get("error"):
                log(f"  Failed to classify this chunk — marking it 'unclassified' ({result['error']})")
            counts[result["category"]] += 1

            chunk_id = f"{rel}::{i}"
            texts.append(chunk.page_content)
            metadatas.append(
                {
                    "source": rel,
                    "category": result["category"],
                    "confidence": result["confidence"],
                    "summary": result["one_line_summary"],
                    "indexed_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            ids.append(chunk_id)
            files_chunk_ids.setdefault(rel, []).append(chunk_id)

        log("Saving chunks to the knowledge base...")
        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        for path, rel, h in to_process:
            known[rel] = {
                "hash": h,
                "chunk_count": len(files_chunk_ids.get(rel, [])),
                "chunk_ids": files_chunk_ids.get(rel, []),
                "last_ingested": datetime.now().isoformat(timespec="seconds"),
            }

    save_manifest(manifest)
    return counts


def main():
    print("📚 Knowledge Base Builder — Session 3")
    print(f"📁 Documents folder: {config.DOCUMENTS_DIR}\n")

    incompatible = config.check_knowledge_base_compatibility()
    if incompatible:
        print(f"❌ {incompatible}")
        sys.exit(1)

    try:
        scan = scan_documents()
    except FileNotFoundError:
        print("❌ my_documents/ does not exist. Create it and add your documents, then try again.")
        sys.exit(1)

    if not scan["files"]:
        print("⚠️  The folder is empty — add .pdf/.docx/.txt/.md files to it, then run this again.")
        sys.exit(0)

    print(f"🔎 Scanning {len(scan['files'])} file(s) for new or changed content...")
    to_process = scan["to_process"]
    removed_rel_paths = scan["removed_rel_paths"]

    if not to_process and not removed_rel_paths:
        print("✅ Nothing new — every file is already indexed and up to date.")
        return

    print(f"📄 New/changed files: {len(to_process)}")
    print(f"🗑️  Files removed since last run: {len(removed_rel_paths)}\n")

    if to_process:
        print("✂️  Splitting pending files into chunks to estimate the work...")
        total = count_pending_chunks(to_process)
        est_seconds = total * 7
        print(
            f"\n💡 Classification will call the local model {total} time(s) (once per chunk) — "
            f"rough estimate: {est_seconds // 60} min {est_seconds % 60} sec, "
            f"depending on your machine's speed."
        )
        answer = input("Continue? (y/n): ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled — nothing was saved.")
            return

    print("\n🧠 Connecting to local models via Ollama...")
    _, _, structured_llm, vectorstore = build_resources()

    print()
    counts = run_ingestion(scan, vectorstore, structured_llm, on_progress=print)

    if to_process:
        print("\n📊 Classification summary for this run:")
        for cat in config.CATEGORIES + ["unclassified"]:
            label = config.CATEGORY_LABELS[cat]
            print(f"   {label}: {counts[cat]}")

    print(f"\n✅ Ingestion complete. Knowledge base saved at: {config.CHROMA_DIR}")
    print("   Run ask.py to query your archive, or report.py for the full inventory report.")


if __name__ == "__main__":
    main()
