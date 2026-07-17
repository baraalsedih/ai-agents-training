# Lab — Session 7: Assembly, Dashboard & Handover

One unified entry point for the whole system built across Sessions 3-6: a knowledge
base, a source-analysis agent, a multi-agent team, and a trust layer. This lab adds no
new agent logic — `run.py` imports Sessions 3-6's real, unmodified functions directly,
plus two new pieces: a local static dashboard (`dashboard.py`) and dated backup/restore
(`backup.py`). 100% local, no API keys, no data leaving your machine.

For the full walkthrough — every menu option with real pasted output, a card-by-card
dashboard reading guide, the three operating playbooks, and a full maintenance/
troubleshooting chapter — see `handbooks/handbook_session7_owners_manual.pdf`. This file
is the quick-start + reference.

## Prerequisite

This lab **assembles** Sessions 3-6 rather than replacing any of them — all four must
already exist and be set up, unmoved, as sibling folders:

1. `labs/session3/ingest.py` must have been run at least once.
2. `labs/session4/` must be set up with its own virtual environment.
3. `labs/session5/` must be set up with its own virtual environment.
4. `labs/session6/` must be set up with its own virtual environment.

## Setup

1. Make sure Ollama is running with the models Sessions 3-6 already need
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
   Same pinned stack as `labs/session6/` (this lab imports Session 3's, Session 5's,
   and Session 6's real modules directly). Session 4 is intentionally not listed here —
   it's only ever reached through Session 5's `agents/source_analyst.py`, which calls it
   as a separate OS process in its own venv.

## Run order

```
python3 run.py
```

Shows an Arabic interactive menu: ingest new documents, ask your archive, request a
research report, audit consistency, run evaluation, open the dashboard, or take a
backup. Prefer direct commands?

```
python3 run.py ingest|ask|research|audit|evaluate|dashboard|backup
```

1. Drop new documents (`.pdf`/`.docx`/`.txt`/`.md`) into `inbox/`, then run `ingest` —
   each file goes through Session 4's source-analysis agent (extraction, chunking,
   classification, link suggestions, your approval), then moves to `inbox/processed/`.
2. `ask` for a quick question, `research` for a deeper cited report, `audit` to check
   the archive for duplicates/contradictions/gaps/terminology.
3. `evaluate` runs the full 15-question golden set (30-45 minutes) — confirms before
   starting since it's heavy.
4. `dashboard` generates `dashboard.html` from whatever Sessions 3-6 have already
   produced on disk, and opens it in your browser.
5. `backup` creates a dated `.zip` under `backups/`. Restore is a separate, deliberate
   command (see below) — not part of the daily menu.

## Restoring a backup

```
python3 backup.py restore --file backups/backup_<date>.zip --to <some-folder>
```

Extracts the archive and runs an offline integrity check (file existence/size, JSON
validity) — no Ollama needed to verify a restore.

## Files

```
labs/system/
├── run.py              -- menu + subcommands, the single entry point
├── system_config.py    -- paths only; never named config.py (see its own docstring)
├── dashboard.py         -- generates dashboard.html from live data across Sessions 3-6
├── backup.py             -- backup / restore
├── inbox/                 -- drop new documents here; processed/ once handled
├── backups/                -- dated backup archives land here
├── dashboard.html            -- generated output -- open in any browser
├── requirements.txt
└── README.md
```

## Troubleshooting

See `handbook_session7_owners_manual.pdf`, chapter 5 (Maintenance & Troubleshooting) for
the full guide, including a first-aid table merging every session's own troubleshooting
table. Quick pointers:

- **`ConnectionError` / `could not connect to ollama`** — Ollama isn't running. Open the
  Ollama app, or run `ollama serve` in a separate terminal, then try again.
- **`ModuleNotFoundError` for `config`, `team`, or `agents`** — make sure `labs/session3/`
  through `labs/session6/` still exist next to this folder, unmoved; every module here
  imports them by sibling path, not as installed packages.
- **The dashboard shows "لا بيانات بعد" (no data yet) on every card** — expected on a
  brand-new system. Run options 1-5 at least once, then regenerate the dashboard.
- **`inbox/` doesn't seem to do anything** — check the file extension is supported
  (`.pdf`/`.docx`/`.txt`/`.md`) and it isn't already sitting in `inbox/processed/`.
- **`evaluate` takes 30-45 minutes** — expected, not a hang; it runs 15 questions through
  the real team plus the judge. Consider running it in the background.
- **"Ran out of memory" / machine froze** — same fix as every earlier session: switch
  `CHAT_MODEL` in `labs/session3/config.py` to a smaller model (e.g. `qwen2.5:7b`).
