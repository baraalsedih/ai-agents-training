"""
Lab 1 — Hello World with an open-source model
=============================================
Goal: your first successful call to a local language model via
LangChain, with a fallback path to the HuggingFace Inference API if
your machine can't comfortably run a model locally.

Before running: make sure 00_check_setup.py shows at least ✅ for
"Ollama service running" and "tool-calling-capable model pulled".

Usage:
    python 01_hello_world.py
"""

import os

from dotenv import load_dotenv

load_dotenv()  # reads HUGGINGFACEHUB_API_TOKEN from .env if present

# USE_HUGGINGFACE=1 in .env switches from local Ollama to the
# HuggingFace Inference API — useful if your machine is underpowered
# for running a local model.
USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "0") == "1"

# Local Ollama model name (change this if you pulled a different one)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def get_llm():
    """Builds and returns the LLM object for the selected path."""
    if USE_HUGGINGFACE:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        # HuggingFaceEndpoint calls the Inference API over the network —
        # requires a valid HUGGINGFACEHUB_API_TOKEN in .env
        endpoint = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            task="text-generation",
            max_new_tokens=256,
            temperature=0.1,
        )
        return ChatHuggingFace(llm=endpoint)

    # Default path: a local model via Ollama — no internet required
    # after the model is pulled, and no API cost.
    from langchain_ollama import ChatOllama

    return ChatOllama(model=OLLAMA_MODEL, temperature=0.1)


def main():
    print(f"Loading model ({'HuggingFace API' if USE_HUGGINGFACE else 'Ollama: ' + OLLAMA_MODEL})...")
    llm = get_llm()

    # First call (invoke) — send a simple text message and receive the
    # model's reply. This is a plain call (no tools) — classic "text
    # generation".
    response = llm.invoke("Hello! Introduce yourself in one short sentence.")

    print("\n--- Model response ---")
    print(response.content)
    print("\n--- Metadata ---")
    print(f"message type: {type(response).__name__}")
    print(f"model: {response.response_metadata.get('model', 'N/A')}")

    # Second example: a question that needs a precise fact — without
    # tools, the model will guess (this is exactly the Hallucination
    # we fix in Lab 2 with a Calculator tool)
    math_response = llm.invoke("What is 345 multiplied by 123? Answer with just the number.")
    print("\n--- Math question without tools (expect it to be wrong or approximate) ---")
    print(f"Model's answer: {math_response.content.strip()}")
    print(f"Correct answer: {345 * 123}")


if __name__ == "__main__":
    main()
