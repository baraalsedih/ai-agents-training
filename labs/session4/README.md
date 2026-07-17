# Lab — Session 4: Source-Analysis Agent (LangGraph)

A single specialized agent, built with [LangGraph](https://langchain-ai.github.io/langgraph/),
that reads one new document, walks it through extraction, chunking,
classification, an optional human review of low-confidence chunks, a
link-suggestion step against your existing archive, a human approval
checkpoint, and finally ingestion — feeding the exact same knowledge base
`labs/session3/` built. 100% local, no API keys, no data leaving your
machine.

For the full walkthrough with sample outputs and the graph diagram, see
chapter 4 of `handbooks/handbook_session4.pdf`. This file is the
quick-start + reference.

## Prerequisite

This lab **feeds** the Session 3 knowledge base rather than building its
own — run `labs/session3/ingest.py` at least once first (see
`labs/session3/README.md`) so there is an existing archive to link against
and ingest into.

## Setup

1. Make sure Ollama is running with the two models Session 3 already
   needs (`llama3.1:8b`, `nomic-embed-text`) — nothing new to pull here.
2. Create and activate a virtual environment inside this folder:
   ```
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   This installs the same pinned stack as `labs/session3/` plus LangGraph
   (this lab imports Session 3's loader, classifier, and manifest helpers
   directly instead of duplicating them).

## Run order

1. Two sample documents already sit in `incoming/` — realistic follow-ups
   to the fictional startup from Session 3's `my_documents/`, so the
   link-suggestion step finds real connections. Drop your own new
   document there too (`.pdf`/`.docx`/`.txt`/`.md`).
2. Run the agent on one file:
   ```
   python3 agent.py "incoming/<file-name>"
   ```
   Watch each node print what it did as the graph runs: extraction,
   chunking, classification, (sometimes) a quick human review of
   low-confidence chunks, link suggestions against Session 3's archive,
   then a full summary before it pauses and asks for your approval.
3. At the approval prompt, answer `y` to ingest, or `n` to reject (nothing
   is written to the knowledge base, but a "rejected" report is still
   saved so the analysis isn't lost).
4. Once approved, confirm the new document is really in the knowledge
   base by asking about it from `labs/session3/`:
   ```
   cd ../session3 && python3 ask.py
   ```

## Resuming a paused run

The approval step is a real LangGraph `interrupt()`, checkpointed to a
local SQLite file (`checkpoints.sqlite`) — not just an in-memory pause.
If you close the terminal (or it crashes) while the agent is waiting for
your `y`/`n`, nothing is lost: run the exact same command again later and
it detects the pending run, reprints the same summary, and asks for your
decision again from where it left off. Running the command a third time
on an already-approved-or-rejected file just tells you it was already
processed — it won't double-ingest.

## Seeing the graph itself

```
python3 agent.py --draw
```
Saves `agent_graph.mmd` — the actual compiled graph as Mermaid text
(generated from the real code, not redrawn by hand). Open it in any
Mermaid-aware viewer (e.g. VS Code's Markdown preview) — no network call
is made to render it, keeping this lab's "100% local" rule intact.

## Files

- `nodes.py` — one function per graph node. Reuses `labs/session3/`'s
  document loader, classification prompt/model, and manifest helpers
  directly rather than re-implementing them.
- `agent.py` — the `AnalysisState` definition, the graph wiring
  (including the conditional branches and the approval checkpoint), and
  the command-line run loop.
- `incoming/` — documents waiting to be analyzed.
- `reports/` — one dated Markdown report per analyzed document (created
  on first run).
- `links.json` — every suggested link ever accepted via ingestion, kept
  as a simple running log (a first step toward drawing relations across
  the archive later).

## Troubleshooting

- **`ConnectionError` / `could not connect to ollama`** — Ollama isn't
  running. Open the Ollama app, or run `ollama serve` in a separate
  terminal, then try again.
- **`NameError` about a missing module when running `agent.py`** — make
  sure `labs/session3/` still exists next to this folder with its
  `config.py`/`ingest.py` intact; `nodes.py` imports from it directly by
  path, not as an installed package.
- **The agent says a file was "already processed" but you wanted to
  re-run it from scratch** — delete `checkpoints.sqlite` (this resets
  *every* file's progress, not just one, since it's a single shared
  database) and run again.
- **Every chunk sails through with no human review at all** — expected
  most of the time. The local classifier reports high confidence
  (0.9–1.0) even on fairly ordinary text; `human_review` only triggers
  below `LOW_CONFIDENCE_THRESHOLD` in `nodes.py` (0.85 by default), which
  is the less common case, not the default path. See chapter 3 of the
  Session 3 handbook for the same observation about this classifier.
- **`suggest_links` finds nothing** — either the knowledge base is nearly
  empty (run `labs/session3/ingest.py` first) or the new document is
  genuinely unrelated to what's already indexed. Nothing is wrong; an
  empty link list is a valid, expected result.
- **Answering `y`/`n` at approval does nothing / raises `EOFError`** —
  you're running the script with no attached terminal (e.g. piped from an
  empty source). Run it interactively, or see "Resuming a paused run"
  above if you did this on purpose to test the resume behavior.
- **Ran out of memory / machine froze during classification** — same fix
  as Session 3: switch `CHAT_MODEL` in `labs/session3/config.py` to a
  smaller model (e.g. `qwen2.5:7b`).
