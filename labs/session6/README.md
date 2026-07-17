# Lab — Session 6: Evaluation, Cost & Observability

This session doesn't build a new agent -- it adds the trust layer around the multi-agent team
built in Session 5 (supervisor + source analyst + consistency auditor + researcher, on top of
the Session 3 knowledge base): a lightweight JSONL tracer, an LLM-as-Judge quality evaluator
run against a hand-verified 15-question golden set, and a cost report that turns raw token/
time numbers into a placeholder cloud-dollar estimate. 100% local, no API keys, no data
leaving your machine.

For the full walkthrough with real report excerpts and the diagnosis worked example, see
chapter 8 of `handbooks/handbook_session6.pdf`. This file is the quick-start + reference.

## Prerequisite

This lab **measures** the Session 3-5 stack rather than replacing any of it -- all three must
already exist and be set up:

1. `labs/session3/ingest.py` must have been run at least once (see `labs/session3/README.md`).
2. `labs/session4/` must be set up with its own virtual environment (see `labs/session4/README.md`).
3. `labs/session5/` must be set up with its own virtual environment (see `labs/session5/README.md`)
   -- `evaluate.py` here imports and runs Session 5's real, unmodified graph directly.

## Setup

1. Make sure Ollama is running with the models Sessions 3-5 already need (`llama3.1:8b`,
   `nomic-embed-text`) -- nothing new to pull here.
2. Create and activate a virtual environment inside this folder:
   ```
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   Same pinned stack as `labs/session5/` (this lab imports and runs that team's real graph)
   plus PyYAML to read `golden_set.yaml`.

## Run order

### 1. Run the golden-set evaluation

```
python3 evaluate.py
```

Runs all 15 questions in `golden_set.yaml` through the real Session 5 team, judges every
answer on four dimensions (Correctness, Groundedness, Completeness, Honesty -- 1-5 each), and
writes a dated report to `eval_reports/eval_report_<date>.md`: a score table, per-dimension
averages, a comparison against `eval_reports/baseline.json` if one exists, and the three
weakest questions flagged for human review. Takes roughly 30-45 minutes on an 8B local model
(15 questions x several LLM calls each, including up to one quality-review revision per
question) -- this is expected, not a hang; watch the per-question progress lines.

The very first run has no baseline to compare against, so it saves its own results as
`baseline.json` automatically. Every later run compares against that same fixed baseline,
without overwriting it, unless you pass `--set-baseline`:

```
python3 evaluate.py --set-baseline   # intentionally reset the baseline to this run
```

Change something about the system (a prompt, `RESEARCH_K`, the chat model) and re-run
`evaluate.py` without `--set-baseline` to see the before/after delta -- that's the whole point
of a golden set (see chapter 1 of the handbook).

### 2. Run the cost report

```
python3 cost_report.py
```

Reads every trace file in `traces/` and writes `eval_reports/cost_report_<date>.md`: cost per
operation type (research / consistency_check / analyze_document), cost per agent + purpose
(which specific LLM call is actually the expensive one), evaluation's own cost kept in a
separate section, and a placeholder cloud-dollar estimate from `lab_config.py`.

### 3. Diagnose a weak answer

```
python3 view_traces.py              # list recent operations
python3 view_traces.py q07          # open one golden question's full trace tree
python3 view_traces.py a1b2c3d4e5f6 # or open by operation_id (prefix is enough)
```

Pick the worst-scoring question from `eval_report_<date>.md`'s "weakest 3" section and open
its trace: you'll see the exact routing decision, every retrieval (which chunks came back for
which sub-query), every LLM call (agent, purpose, tokens, duration), and the judge's own
verdict -- all in one operation, since evaluate.py traces the system run and the judge call
together. See chapter 6 of the handbook for a full worked diagnosis on this lab's own data.

## Adding your own questions

Copy the `TEMPLATE` block at the bottom of `golden_set.yaml`, fill it in from your own real
archive (see chapter 3 of the handbook for how to write a good question of each of the four
types: explicit, synthesis, category_filter, trap), and give it the next `q<N>` id. Every
mistake `evaluate.py` surfaces on your own archive is a candidate for a new golden question --
the set is meant to grow.

## Files

```
labs/session6/
├── tracing.py         -- lightweight JSONL tracer (used by labs/session5/ too, via sys.path)
├── golden_set.yaml     -- 15 questions on the Session 3 demo archive + a template section
├── judge.py             -- LLM-as-Judge: 4 dimensions, structured output, Arabic prompt/rationale
├── evaluate.py           -- runs golden_set.yaml through Session 5's team, judges, reports
├── cost_report.py         -- aggregates traces/ into a cost report
├── view_traces.py          -- list recent operations / open one operation's full trace tree
├── lab_config.py            -- paths, judge model, low-score threshold, placeholder cloud prices
├── traces/                   -- JSONL trace files land here (one per day)
├── eval_reports/               -- eval_report_*.md, cost_report_*.md, baseline.json
├── requirements.txt
└── README.md
```

`lab_config.py`, not `config.py`: Sessions 3-5 already import their own `config.py` by bare
module name via `sys.path` insertion -- a second top-level module also named `config` here
would silently collide with theirs in Python's module cache (`sys.modules`) instead of loading
side by side. See the comment at the top of `lab_config.py` for the full explanation.

## What changed in `labs/session5/`

A handful of call-site edits, each marked `# session6: tracing added`, wrap existing LLM
calls/retrievals with `tracing.traced_llm_call()` / `tracing.log_retrieval()` /
`tracing.log_decision()`, and wrap each top-level entry point
(`team.py`'s `run_once()`, `run_research()`, `run_consistency_check()`,
`source_analyst.run_source_analyst()`) in one `tracing.operation(...)` context so a whole
request traces as one contiguous tree, however many agents and revisions it takes. No node,
prompt, or piece of business logic was changed -- Session 5 runs exactly as it did before,
standalone, with or without `labs/session6/` present at import time... except it does need
`labs/session6/` present now, the same way it already needs `labs/session3/` and
`labs/session4/` present as sibling folders -- see `labs/session5/README.md`'s troubleshooting
section for the shape of that failure mode if one of these sibling folders ever goes missing.

## Troubleshooting

- **`evaluate.py` takes a long time (30-45 min)** -- expected. Watch the `[i/15] ... → الوجهة:
  ... | المتوسط: ...` progress line printed after each question; if it's still advancing, it's
  working. Consider running it in the background if you're driving it from a script.
- **The judge gives an unusually harsh or generous score on one question** -- expected
  sometimes, not a bug. A single local 8B model judging is a directional signal, not a ground
  truth -- see chapter 4 of the handbook for the judge's documented limits and the human-review
  protocol for low-scoring questions (`LOW_SCORE_THRESHOLD` in `lab_config.py`).
- **`cost_report.py` says "لا توجد أحداث مسجَّلة بعد"** -- run `evaluate.py` or any
  `labs/session5/team.py` request first; `cost_report.py` only reads what's already in
  `traces/`, it doesn't generate new usage itself.
- **`view_traces.py <id>` says no match** -- pass a longer prefix of the `operation_id` shown
  by the no-argument listing, or the golden question's own id (e.g. `q07`) if it came from
  `evaluate.py`.
- **`ModuleNotFoundError` for `team` or `agents`** -- make sure `labs/session5/` still exists
  next to this folder, unmoved; `evaluate.py` imports it by relative path, not as an installed
  package, same convention every lab since Session 4 uses.
- **`ConnectionError` / `could not connect to ollama`** -- Ollama isn't running. Open the
  Ollama app, or run `ollama serve` in a separate terminal, then try again.
- **"Ran out of memory" / machine froze** -- same fix as Sessions 3-5: switch `CHAT_MODEL` in
  `labs/session3/config.py` to a smaller model (e.g. `qwen2.5:7b`); every agent (and the judge,
  via `JUDGE_MODEL` in `lab_config.py`) can be pointed at a lighter model independently.
