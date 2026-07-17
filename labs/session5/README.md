# Lab — Session 5: Multi-Agent Team (Supervisor + Specialists)

A [LangGraph](https://langchain-ai.github.io/langgraph/) supervisor that routes a founder's
request to one of three specialized agents working on the *same* knowledge base built in
Session 3: the source-analysis agent from Session 4 (ingests a new document), a new
consistency-auditor agent (audits the archive itself for duplicates, contradictions, gaps,
and inconsistent terminology), and a new researcher agent (answers an analytical question
with a cited, composed report) — with one quality-review cycle on the researcher's output
before it's delivered. 100% local, no API keys, no data leaving your machine.

For the full walkthrough with sample outputs and the graph diagram, see chapter 5 of
`handbooks/handbook_session5.pdf`. This file is the quick-start + reference.

## Prerequisite

This team **feeds and queries** the Session 3 knowledge base, and hands off document
analysis to Session 4's agent unchanged — both must already exist:

1. `labs/session3/ingest.py` must have been run at least once (see `labs/session3/README.md`).
2. `labs/session4/` must be set up with its own virtual environment (see
   `labs/session4/README.md`) — the supervisor calls Session 4's `agent.py` as a subprocess,
   in its own venv, without copying or modifying any of its code.

## Setup

1. Make sure Ollama is running with the models Sessions 3–4 already need
   (`llama3.1:8b`, `nomic-embed-text`) — nothing new to pull here.
2. Create and activate a virtual environment inside this folder:
   ```
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   This installs the same pinned stack as Sessions 3–4 (this team's agents query and extend
   that same knowledge base) plus `numpy`, used by the consistency auditor to cluster
   candidate terminology by embedding similarity.

## Run order

### 1. Ingest a new document (routes to the source-analysis agent)

```
python3 team.py --request "Please analyze and ingest the file incoming/<file-name>"
```

The supervisor classifies this as `analyze_document`, extracts the file path, and hands off
to Session 4's real `agent.py` as a subprocess — its extraction/chunking/classification/
link-suggestion/human-approval flow runs exactly as it does standalone, printing to the same
terminal. Answer the approval prompt `y`/`n` exactly as you would running Session 4 directly.

### 2. Check the archive's consistency (routes to the consistency auditor)

```
python3 team.py --request "Check the knowledge base archive for consistency issues"
```

Prints a running estimate of local-model calls, then a report with four sections — duplicates,
contradictions, gaps (open questions with no resolving decision/evidence nearby), and a
proposed terminology glossary — saved under `reports/`. The sample knowledge base ships with a
deliberately planted contradiction (a later "expand to large restaurant chains" decision that
reverses an earlier "small restaurants only, no ERP integration" decision) and a near-duplicate
evidence restatement, so the auditor has something real to find on a fresh run — see chapter 3
of the handbook for the real distances and confirmed findings from testing this exact archive.

You can also scope the audit to one category (faster on a larger archive later):

```
python3 team.py --request "Check only the decisions for consistency"
```

### 3. Ask an analytical question (routes to the researcher, with a quality-review pass)

```
python3 team.py --request "<your analytical question about the archive>"
```

The researcher decomposes the question into a few focused sub-queries, retrieves for each, and
composes a cited Markdown report (Summary / What We Know / Evidence / Related Decisions /
Related Open Questions / Knowledge Limits) saved under `reports/`. The supervisor then reviews
it once: if the Summary doesn't answer the question or a claim is missing its citation, the
researcher gets one revision pass with concrete feedback; after that the report ships either
way, with an explicit caveat appended if it's still incomplete. `MAX_REVISIONS = 1` in
`supervisor.py` bounds this to exactly one cycle, to keep cost and latency predictable — see
chapter 4 of the handbook for a real transcript of both an immediate pass and a full revision
cycle triggered by a deliberately vague question.

### Interactive mode

Run `python3 team.py` with no arguments for a REPL: type a request, see the routing decision
and the result, repeat; type `exit` to quit.

## Seeing the graph itself

```
python3 team.py --draw
```

Saves `team_graph.mmd` — the actual compiled graph as Mermaid text. Open it in any
Mermaid-aware viewer (e.g. VS Code's Markdown preview) — no network call is made.

## Files

```
labs/session5/
├── agents/
│   ├── source_analyst.py      -- subprocess wrapper around Session 4's real agent.py
│   ├── consistency_auditor.py -- the new auditor agent (duplicates/contradictions/gaps/terms)
│   └── researcher.py          -- the new research & report agent (decompose/retrieve/compose)
├── supervisor.py               -- routing (route) + the quality loop (quality_review)
├── team.py                     -- top-level graph wiring + CLI entry point
├── reports/                    -- generated audit/research reports land here (created on first run)
├── glossary.json               -- the auditor's proposed canonical-term list (created on first run)
├── requirements.txt
└── README.md
```

- `agents/source_analyst.py` calls Session 4's `agent.py` as a subprocess rather than
  importing its graph as a true LangGraph subgraph — see the module's docstring for exactly
  why (Session 4's `interrupt()` + its own `SqliteSaver` checkpointer would otherwise need to
  be shared across two graphs' persistence layers for no real benefit in a single-process CLI
  lab). Session 4 itself is completely unmodified and still runs standalone.
- `agents/consistency_auditor.py` and `agents/researcher.py` are also runnable directly
  (`python3 agents/consistency_auditor.py`, `python3 agents/researcher.py "question"`) for
  quicker iteration without going through the full team graph.

## Troubleshooting

- **The supervisor routes a document-analysis request to the wrong destination, or vice
  versa** — rephrase to be explicit: mention the word "file" or a filename for
  `analyze_document`, or "archive"/"consistency"/"duplicates"/"contradictions" for
  `consistency_check`. The router is a local 8B model doing structured-output classification,
  not a lookup table — it occasionally needs an unambiguous phrasing, same as any
  classifier node in Sessions 3–4.
- **The consistency check is slow on a large archive** — scope it to one category:
  `python3 team.py --request "Check only the decisions for consistency"`. Duplicate/
  contradiction candidate generation is already restricted to each chunk's nearest
  neighbors (not every possible pair — see the module docstring), but the LLM confirmation
  calls still scale with the number of candidates found.
- **The quality-review loop "rejected it twice"** — it can't; `MAX_REVISIONS = 1` in
  `supervisor.py` means at most one revision cycle runs. If a report still ships with a
  caveat after that, the archive likely doesn't contain enough to fully answer the question
  — check the report's own "Knowledge Limits" section, which says so explicitly.
- **`ConnectionError` / `could not connect to ollama`** — Ollama isn't running. Open the
  Ollama app, or run `ollama serve` in a separate terminal, then try again.
- **`ModuleNotFoundError` for `config` or `ingest`** — make sure `labs/session3/` still
  exists next to `labs/session4/` and `labs/session5/`, unmoved; all three import from it by
  relative path, not as an installed package.
- **`analyze_document` requests hang or the subprocess seems to do nothing** — Session 4's
  agent needs `labs/session4/venv/` set up with its own dependencies installed (see
  `labs/session4/README.md`); `source_analyst.py` looks for that venv's Python interpreter
  specifically and falls back to the current interpreter only if it's missing.
- **"Ran out of memory" / machine froze during an audit or research pass** — same fix as
  Sessions 3–4: switch `CHAT_MODEL` in `labs/session3/config.py` to a smaller model (e.g.
  `qwen2.5:7b`); every agent here reuses that same shared config.
