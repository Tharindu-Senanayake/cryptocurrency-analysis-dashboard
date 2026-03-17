# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Crypto Currency Analysis

Daily data collection pipeline for the top 20 cryptocurrencies (AUD). Fetches raw snapshots from CoinMarketCap and appends 20 rows per day to `output/raw/crypto_daily_snapshots.csv`. A second script builds a star-schema from the raw data into `output/tables/`. Data is stored as-is — no cleaning or transformation in the collection script. User handles analysis in notebooks separately.

---

# Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools). AI handles reasoning; deterministic Python scripts handle execution. That separation is what keeps this system reliable.

## The WAT Architecture

**Layer 1: Workflows** — Markdown SOPs in `workflows/`. Each defines the objective, inputs, which tool to call, expected output, and how to handle edge cases.

**Layer 2: Agent (You)** — Read the relevant workflow, call tools in the right sequence, handle failures, ask before re-running anything that costs API credits.

**Layer 3: Tools** — Python scripts in `tools/`. Stateless, re-runnable, and fast. They do the actual work.

---

## Environment

- **OS:** Windows 11
- **Language:** Python 3.x — all tools must be written in Python, no exceptions
- **Command:** Always use `python` (not `python3`) — this is Windows
- **Output format:** CSV files saved to `output/`
- **Scheduling target:** Windows Task Scheduler (scripts must run headlessly)
- **Secrets:** All API keys go in `.env` only

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run a tool
python tools/<script_name>.py

# Tail the run log
tail -f logs/run.log
```

---

## How to Operate

1. **Check `tools/` before building anything new.** Only create a new script if nothing exists for the task.
2. **When things fail:** Read the full error, fix the script, retest. If the fix requires a paid API call, ask before running. Document findings in the relevant workflow.
3. **Keep workflows current.** Update them when you find better methods or hit recurring issues. Don't create or overwrite workflow files without asking unless explicitly told to.

---

## File Structure

```
notebooks/           # Jupyter notebooks for interactive analysis
output/
  raw/               # Rolling raw snapshot CSV (append-only)
  tables/            # Star-schema CSVs for Power BI (rebuilt daily)
reports/             # Power BI reports (.pbix)
logs/                # run.log — one line per execution
tools/               # Python scripts for deterministic execution
workflows/           # Markdown SOPs
.env                 # API keys (gitignored)
.tmp/                # Temporary/intermediate files — disposable
requirements.txt     # Python dependencies
```

---

## CSV Output Rules

- Raw data saves to `output/raw/`, star-schema tables save to `output/tables/`
- Filename: `{data_type}_{YYYY-MM-DD}.csv` (e.g. `crypto_daily_snapshots.csv`)
- Always include a `timestamp` column (UTC)
- Include a unique key column per row for safe deduplication
- Encoding: `utf-8-sig` (BOM) so Excel opens without issues
- Never overwrite an existing file — use a new timestamped filename

---

## Scheduling Rules

Scripts must be safe to run unattended via Windows Task Scheduler:

- No `input()` calls or interactive prompts
- Exit `0` on success, non-zero on failure
- Write a log entry to `logs/run.log` on every execution (timestamp, rows fetched, status)
- If the API is unreachable or returns an error, log it and exit cleanly
