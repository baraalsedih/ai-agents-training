# Lab — Session 3: Living Knowledge Base (RAG)

Turns a folder of real documents into a searchable, self-updating knowledge
base — 100% local. No API keys, no cloud calls, no data leaving your
machine. Everything runs through [Ollama](https://ollama.com).

For the full walkthrough with sample outputs, see chapter 4 of
`handbooks/handbook_session3.pdf`. This file is the quick-start + reference.

## Setup

1. Make sure Ollama is installed and running (see the session 2 handbook,
   chapter 1, if you haven't set it up yet).
2. Pull the two models this lab needs:
   ```
   ollama pull llama3.1:8b
   ollama pull bge-m3
   ```
3. Create and activate a virtual environment inside this folder:
   ```
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. (Optional) Copy `.env.example` to `.env` if you want to override any
   default — model names, chunk size, retrieval k — without editing code:
   ```
   cp .env.example .env
   ```

## Run order

1. Put your real documents (`.pdf`, `.docx`, `.txt`, `.md`) inside
   `my_documents/`. Four sample documents about a fictional startup are
   already there — safe to delete once you add your own.
2. Build the knowledge base:
   ```
   python3 ingest.py
   ```
   Reads every file, splits it into chunks, classifies each chunk
   (idea / decision / evidence / open_question) with the local model, and
   indexes everything into a local Chroma store under `knowledge_base/`.
   Re-running it later only processes files that are new or changed — a
   `manifest.json` tracks a hash per file.
3. Ask questions:
   ```
   python3 ask.py
   ```
   Type a question in Arabic or English. Special commands:
   - `filter: decision` / `filter: idea` / `filter: evidence` / `filter: open_question` —
     restrict retrieval to one category
   - `clear filter` — clear the active filter
   - `exit` — quit
4. Get an inventory report:
   ```
   python3 report.py            # print to screen
   python3 report.py --save     # also save as a dated Markdown file
   ```
   Shows chunk counts per category, per source file, and the full list of
   open questions and decisions across your entire archive.

## Web UI (recommended for Arabic content)

Most terminals don't shape/reorder Arabic (RTL) text correctly, so Arabic
filenames, questions, answers, and summaries can look backwards or jumbled
when printed directly in a terminal — even though the underlying text is
correct. A browser renders this correctly, so there's a small local web UI
that wraps the exact same `ingest`/`ask`/`report` logic:

```
python3 webapp.py
```

Then open `http://localhost:5050`. Three tabs: **Ask** (ask questions with
an optional category filter, see cited sources), **Ingest** (check for
changed files, then build/update the knowledge base with a live log), and
**Report** (the same inventory report, rendered as HTML). Nothing here
changes what the scripts do — it's the same functions, just with a UI that
displays Arabic correctly.

## Config

All tunable values (model names, chunk size/overlap, retrieval k, folder
paths) live in `config.py`. Model names and the chunking/retrieval numbers
can be overridden via a `.env` file (see `.env.example`) — same pattern as
`labs/lab1` and `labs/lab2` — so switching models (e.g. to try `qwen2.5:7b`
instead of `llama3.1:8b`) never requires editing code. Anything without a
`.env` variable (folder paths, category names) is set directly in
`config.py`.

To use a different chat model, set `CHAT_MODEL` in `.env` after pulling it
with Ollama. To use a different embedding model, set `EMBEDDING_MODEL` —
but see the warning above: this requires deleting `knowledge_base/` and
running `ingest.py` again from scratch, since chunks embedded by one model
aren't compatible with another.

## Troubleshooting

- **`ConnectionError` / `could not connect to ollama`** — Ollama isn't
  running. Open the Ollama app, or run `ollama serve` in a separate
  terminal, then try again.
- **`model "llama3.1:8b" not found` (or `bge-m3`)** — you haven't
  pulled it yet. Run the two `ollama pull` commands from Setup above.
- **Ingest is much slower than the printed estimate** — classification
  calls the local model once per chunk; a slower machine or a bigger model
  (`CHAT_MODEL`) both increase this. Set `CHAT_MODEL=qwen2.5:7b` in `.env`
  if you need something faster and it's already on your machine.
- **A `.pdf` file fails to load / produces empty text** — it's likely a
  scanned image PDF rather than real text. This lab does not do OCR; either
  re-export the file as text-based PDF or skip it for now.
- **`my_documents/` is empty and ingest.py exits immediately** — add at
  least one `.pdf`/`.docx`/`.txt`/`.md` file to that folder first.
- **A chunk keeps coming back `unclassified`** — the local model failed to
  return a valid structured response for that one chunk (rare, but small
  models occasionally do this). It's stored with category `unclassified`
  instead of crashing the whole run; you can re-run `ingest.py` after
  editing that source file slightly to retry it, or classify it manually by
  reviewing `report.py`'s output.
- **Answers in `ask.py` say "I don't know" even though the info exists in
  your documents** — two different causes, in order of likelihood:
  (1) the relevant chunk didn't make it into the top `RETRIEVAL_K` results —
  try raising `RETRIEVAL_K` in `.env`, rephrasing the question closer to the
  document's own wording, or narrowing/removing an active category filter;
  (2) the chunk *was* retrieved but got buried among several less-relevant
  ones and the local model played it safe rather than risk a wrong answer —
  this is expected, conservative behavior from a small local model (the
  alternative is a model that guesses and hallucinates, which is worse).
  Asking a more specific question, or filtering to the right category first,
  usually helps.
- **Arabic text looks reversed or jumbled in the terminal** — this is a
  terminal rendering limitation (most terminals don't reorder RTL text
  correctly), not a bug in the data. Use `python3 webapp.py` instead — see
  the Web UI section above.
- **Ran out of memory / machine froze during ingest or ask** — set
  `CHAT_MODEL=qwen2.5:7b` (or another smaller model) in `.env` and close
  other memory-heavy applications.
