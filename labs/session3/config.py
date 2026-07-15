"""Central configuration for the session 3 knowledge base lab.

All tunable values live here so the other scripts (ingest.py, ask.py,
report.py) never hardcode a path or a model name.
"""

from pathlib import Path

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
CHAT_MODEL = "llama3.1:8b"
# Lighter/already-installed alternative if your machine is slower or you
# don't want to download another ~5GB model:
# CHAT_MODEL = "qwen2.5:7b"

# Embedding model. This MUST stay identical for the entire life of this
# knowledge base — switching it means every chunk has to be re-embedded
# from scratch, since different models place text in different, incompatible
# vector spaces. Pull it first: `ollama pull nomic-embed-text`
EMBEDDING_MODEL = "nomic-embed-text"

# Characters per chunk, and how many characters consecutive chunks share.
# Larger chunk_size = more context per match but less precise retrieval.
# Larger chunk_overlap = less risk of cutting an idea in half, but more
# redundant storage. 800-1200 / 100-200 is a reasonable starting point.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# How many chunks ask.py retrieves per question by default.
RETRIEVAL_K = 5

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
