"""
Lab 4 (Bonus) — A small but complete RAG pipeline: Chunking -> Embeddings -> Chroma -> Retrieval -> LLM
=============================================
This is the hands-on example for the "Stretch: RAG" section of the
slides. We take a local text file (data/sample_doc.md) about a
fictional company, split it into chunks, turn each chunk into a
vector (embedding) with an open-source model, store them in Chroma
(a local vector database), and then, for a user question, retrieve
the semantically closest chunks and pass them to the model as
context so it can ground its answer in them.

To prove the answer comes from the document and not from the model's
prior knowledge, we ask about two facts that only exist inside
sample_doc.md (see its last section).

Usage:
    python 04_rag_demo.py
"""

import os
import shutil

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_text_splitters import MarkdownTextSplitter

load_dotenv()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "sample_doc.md")
PERSIST_DIR = os.path.join(os.path.dirname(__file__), ".chroma_rag_demo")

RAG_PROMPT_TEMPLATE = """Answer the question using ONLY the context below.
If the answer is not contained in the context, say "I don't know based on the given context."

Context:
{context}

Question: {question}

Answer:"""


def build_vectorstore() -> Chroma:
    print("1) Loading the document and splitting it into chunks...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_text = f.read()

    splitter = MarkdownTextSplitter(chunk_size=400, chunk_overlap=60)
    chunks = splitter.create_documents([raw_text])
    print(f"   Number of chunks: {len(chunks)}")

    print("2) Generating embeddings with an open-source model (sentence-transformers)...")
    # A small, fast model (~90MB) that runs entirely locally, no external API.
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    print("3) Storing the vectors in Chroma (local vector database)...")
    # Wipe any previous store so every run of the lab starts clean.
    if os.path.exists(PERSIST_DIR):
        shutil.rmtree(PERSIST_DIR)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name="nebula_handbook",
    )
    return vectorstore


def ask(vectorstore: Chroma, llm: ChatOllama, question: str, k: int = 3):
    print(f"\n{'=' * 60}\nQuestion: {question}\n{'=' * 60}")

    print("4) Retrieval — fetching the semantically closest chunks for the question...")
    retrieved_docs = vectorstore.similarity_search(question, k=k)
    for i, doc in enumerate(retrieved_docs, 1):
        preview = doc.page_content.strip().replace("\n", " ")[:90]
        print(f"   [{i}] {preview}...")

    context = "\n\n".join(d.page_content for d in retrieved_docs)
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)

    print("5) Sending the question + retrieved context to the model...")
    response = llm.invoke([HumanMessage(content=prompt)])
    print(f"\nAnswer: {response.content.strip()}")
    return response.content


def main():
    vectorstore = build_vectorstore()
    llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)

    # Two questions that prove the answer came from the document: these
    # two facts don't exist in any general training data for the model.
    ask(vectorstore, llm, "What is Nebula's support ticket system internally called?")
    ask(vectorstore, llm, "What was the codename of Nebula's 2024 infrastructure migration project?")

    # A third, ordinary question to show RAG also works for "natural"
    # questions about the document.
    ask(vectorstore, llm, "How many data centers does Nebula operate and where?")

    # =========================================================
    # 🧪 Try it yourself:
    # 1. Ask a question completely outside the document's scope (e.g.
    #    "What is the capital of France?") — watch the model refuse to
    #    answer because the context doesn't contain that information
    #    (thanks to the prompt above).
    # 2. Change k in ask() from 3 to 1 and see if answer quality changes.
    # 3. Add a new paragraph to data/sample_doc.md, rerun, and ask about
    #    it directly.
    # =========================================================


if __name__ == "__main__":
    main()
