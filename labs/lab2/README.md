# Lab — Session 3: LCEL + Natural Language to SQL

Two scripts, run in order:

1. **`seed_database.py`** — builds `store.db`, a small fictional e-commerce
   SQLite database (customers, products, orders, order_items) with
   realistic, randomized data.
2. **`sql_agent.py`** — connects a LangChain SQL Agent to `store.db` and
   answers natural-language questions (Arabic and English) by exploring
   the schema, writing SQL, running it, and explaining the result.

## Setup

Same environment style as the Session 2 lab — Python 3.11-3.13 (avoid
3.14 for now, see Troubleshooting), a local virtual environment, and
either Ollama (default, free, local) or the HuggingFace Inference API.

```bash
# From inside labs/lab2/
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env            # defaults are already correct for Ollama
```

If you don't already have Ollama + a tool-calling model pulled from the
Session 2 lab:

```bash
ollama pull qwen2.5:7b
```

## Run order

```bash
python seed_database.py   # creates store.db (safe to re-run — it recreates the file each time)
python sql_agent.py       # explores the schema, runs 5 demo questions, then offers a conversational mode
```

`sql_agent.py` will:

1. Print the tables and one table's schema — what the agent "sees"
   before it ever runs.
2. Build the agent (`SQLDatabaseToolkit` + `create_sql_agent`,
   `verbose=True`, so you see every tool call it makes).
3. Run 5 example questions, increasing in difficulty, mixing Arabic and
   English.
4. Ask if you want to enter conversational mode (`y`/`n`) — a REPL where
   follow-up questions carry context from previous turns.

## Troubleshooting

- **`store.db not found`** — run `seed_database.py` first.
- **The agent responds with a filler sentence and never queries the
  database** (e.g. "Let me check that.") — this is a known rough edge of
  Ollama's tool-calling template with small local models on certain
  phrasings. `sql_agent.py` already retries automatically with a nudge
  (see `invoke_reliably()`); if it still happens on a question you write
  yourself, try rephrasing it or asking more specifically (name the
  table/column you're interested in).
- **The model generates wrong or invalid SQL** — try a larger model
  (`llama3.1:8b` or a bigger Qwen model), or rephrase the question to be
  more specific about which table/columns/timeframe you mean. Small
  local models are noticeably less reliable on multi-table joins and
  date-range logic than hosted frontier models — this is expected and is
  exactly the "model compatibility" caveat from the slides.
- **`TypeError: 'function' object is not subscriptable` / pydantic
  errors on import** — you're likely on Python 3.14+. This repo's pinned
  LangChain/pydantic versions don't yet resolve cleanly on the newest
  Python. Use Python 3.12 (`brew install python@3.12` on Mac) to create
  the virtual environment instead.
- **Ollama connection refused** — make sure the Ollama app/service is
  running (`ollama serve`, or open the desktop app), and that
  `OLLAMA_MODEL` in `.env` matches a model you've actually pulled
  (`ollama list`).
