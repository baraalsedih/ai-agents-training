"""Central configuration for the session 3 knowledge base lab.

All tunable values live here so the other scripts (ingest.py, ask.py,
report.py) never hardcode a path or a model name. Values can be overridden
via a .env file (see .env.example) without touching any code — same pattern
as labs/lab1 and labs/lab2 in this course.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings

load_dotenv()

# Folder containing this file — every other path is relative to it, so the
# scripts work no matter which directory you run them from.
BASE_DIR = Path(__file__).resolve().parent

# Drop your real documents here: .pdf, .docx, .txt, .md
DOCUMENTS_DIR = BASE_DIR / "my_documents"

# Everything persisted by ingest.py lives under this folder: the Chroma
# vector store itself plus the manifest that tracks what's already indexed.
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
CHROMA_DIR = KNOWLEDGE_BASE_DIR / "chroma"
MANIFEST_PATH = KNOWLEDGE_BASE_DIR / "manifest.json"
CHROMA_COLLECTION_NAME = "knowledge_base"

# Chat model used for classification (ingest.py) and answer generation
# (ask.py). Pull it first: `ollama pull llama3.1:8b`
# Override in .env as CHAT_MODEL=... — e.g. qwen2.5:7b if your machine is
# slower or you don't want to download another ~5GB model. Trade-off worth
# knowing: qwen2.5:7b measurably leaks Chinese/Korean text into answers
# more often than llama3.1:8b in this pipeline (observed on broad/summary
# questions like "what's the company about?" — 2/5 clean vs 5/5 clean in
# side-by-side testing). ask.py retries and falls back to an honest
# failure message rather than showing garbled text, but if you hit that
# message often, switching back to llama3.1:8b is the real fix.
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.1:8b")

# Embedding model. This MUST stay identical for the entire life of a given
# knowledge base — switching it means every chunk has to be re-embedded
# from scratch, since different models place text in different, incompatible
# vector spaces. Pull it first: `ollama pull bge-m3`
# bge-m3 is genuinely multilingual (100+ languages, including Arabic) and
# needs no special query/document prefixes. Lighter alternative:
# nomic-embed-text (~274MB vs ~1.2GB) — English-optimized, and needs task
# prefixes to embed well, which get_embeddings() below adds automatically.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")

# Characters per chunk, and how many characters consecutive chunks share.
# Larger chunk_size = more context per match but less precise retrieval.
# Larger chunk_overlap = less risk of cutting an idea in half, but more
# redundant storage. 800-1200 / 100-200 is a reasonable starting point.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# How many chunks ask.py retrieves per question by default. Retrieval is
# approximate (nearest-neighbor by meaning, not exact keyword search), so a
# relevant chunk can rank just outside a too-tight k, especially as your
# archive grows. 8 is a reasonable default for a small/medium archive —
# raise it further if answers keep missing detail that you know is there.
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "8"))

# The four classification categories used by the tagging step in ingest.py.
CATEGORIES = ["idea", "decision", "evidence", "open_question"]

# Display labels shown to the user in print messages and reports.
CATEGORY_LABELS = {
    "idea": "Idea",
    "decision": "Decision",
    "evidence": "Evidence",
    "open_question": "Open Question",
    "unclassified": "Unclassified",
}

# File extensions ingest.py knows how to read.
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class _NomicPrefixedEmbeddings(OllamaEmbeddings):
    """nomic-embed-text needs task-specific prefixes to embed well — without
    them, retrieval quality drops significantly, especially across languages
    (e.g. an English question against Arabic documents). This adds the
    prefixes transparently: "search_document: " for stored chunks,
    "search_query: " for questions. See https://ollama.com/library/nomic-embed-text
    """

    def embed_documents(self, texts: list) -> list:
        return super().embed_documents([f"search_document: {t}" for t in texts])

    def embed_query(self, text: str) -> list:
        return super().embed_query(f"search_query: {text}")


def get_embeddings():
    """The single place every script builds its embeddings object, so
    storage (ingest.py) and retrieval (ask.py, report.py) always stay
    consistent with each other. Only nomic-* models get the prefix
    treatment above — a different EMBEDDING_MODEL falls back to plain
    OllamaEmbeddings, since other models don't use these task prefixes."""
    if EMBEDDING_MODEL.startswith("nomic-embed"):
        return _NomicPrefixedEmbeddings(model=EMBEDDING_MODEL)
    return OllamaEmbeddings(model=EMBEDDING_MODEL)


def check_knowledge_base_compatibility() -> str | None:
    """Returns a clear, actionable error message if the existing knowledge
    base was built with a different EMBEDDING_MODEL than the one currently
    configured — otherwise returns None. Every entry point (ingest.py,
    ask.py, report.py, webapp.py) calls this before touching the vector
    store, so a model swap in .env fails with a helpful message instead of
    a raw Chroma "dimension mismatch" error."""
    if not MANIFEST_PATH.exists():
        return None
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not manifest.get("files"):
        return None

    used_model = manifest.get("embedding_model")
    if used_model and used_model != EMBEDDING_MODEL:
        return (
            f"Your knowledge base was built with embedding model '{used_model}', "
            f"but EMBEDDING_MODEL is now set to '{EMBEDDING_MODEL}'. These produce "
            f"incompatible vectors. Either set EMBEDDING_MODEL back to "
            f"'{used_model}' in .env, or delete the knowledge_base/ folder and "
            f"run ingest.py again to rebuild it from scratch with '{EMBEDDING_MODEL}'."
        )
    return None
