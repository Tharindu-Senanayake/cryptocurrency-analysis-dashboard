"""
crypto_daily_snapshot.py

Daily scheduled script. Fetches today's snapshot for 20 cryptocurrencies
and appends 20 rows to a rolling CSV (one row per coin per day).

All fields returned by CMC are captured as-is — no column filtering.
Column prefixes:
  (none)   — CoinMarketCap coin-level fields (id, name, slug, symbol, ...)
  aud_     — CoinMarketCap AUD quote fields (aud_price, aud_market_cap, ...)
  global_  — CoinMarketCap global market metrics, same value for all coins

Manually added columns: timestamp, symbol.

Total API calls: 2 (regardless of number of coins tracked).

Run manually:
    python tools/crypto_daily_snapshot.py

Or schedule via Windows Task Scheduler (see workflows/crypto_daily_data.md).
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "raw"
LOG_DIR    = BASE_DIR / "logs"
LOG_FILE   = LOG_DIR / "run.log"
OUTPUT_CSV = OUTPUT_DIR / "crypto_daily_snapshots.csv"

# ---------------------------------------------------------------------------
# Watchlist — CMC symbols only
# Most consistently top-20 non-stablecoin cryptocurrencies.
# To add/remove a coin: update this list and re-run.
# ---------------------------------------------------------------------------
WATCHLIST = [
    "BTC",  "ETH",  "BNB",  "SOL",  "XRP",
    "DOGE", "ADA",  "TRX",  "AVAX", "TON",
    "LINK", "SHIB", "DOT",  "POL",  "LTC",
    "BCH",  "UNI",  "NEAR", "XLM",  "ATOM",
]

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
CMC_QUOTES_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
CMC_GLOBAL_URL = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"

# Global DataFrame — populated after each run, accessible for manual analysis
df = None


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config() -> str:
    """Load .env and return CMC_API_KEY. Raises EnvironmentError if missing."""
    load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("CMC_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "CMC_API_KEY is not set. Add your CoinMarketCap API key to .env"
        )
    return api_key


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _flatten(d: dict, prefix: str = "", skip_keys: set = None) -> dict:
    """
    Flatten one level of a dict into scalar values, adding a prefix to each key.
    Lists are joined with '|'. Nested dicts and keys in skip_keys are skipped.
    """
    skip_keys = skip_keys or set()
    result = {}
    for k, v in d.items():
        if k in skip_keys:
            continue
        key = f"{prefix}{k}"
        if isinstance(v, list):
            result[key] = "|".join(str(i) for i in v)
        elif not isinstance(v, dict):
            result[key] = v
    return result


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------
def fetch_cmc_quotes(session: requests.Session, api_key: str) -> dict:
    """
    Fetch all available fields for watchlist coins from CMC.

    Returns dict keyed by CMC symbol. Each value is a flat dict of all
    coin-level fields (no prefix) and AUD quote fields (prefix: aud_).
    """
    symbols = ",".join(WATCHLIST)
    headers = {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}
    params  = {"symbol": symbols, "convert": "AUD"}

    resp = session.get(CMC_QUOTES_URL, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    body = resp.json()

    if body.get("status", {}).get("error_code", 0) != 0:
        raise RuntimeError(
            f"CMC API error: {body['status'].get('error_message', 'unknown')}"
        )

    result = {}
    for symbol, data in body["data"].items():
        # CMC returns a list when multiple coins share a symbol; take the first
        coin = data[0] if isinstance(data, list) else data

        # Flatten top-level coin fields, skip the nested quote dict
        flat = _flatten(coin, prefix="", skip_keys={"quote"})

        # Flatten AUD quote fields separately
        aud_quote = coin.get("quote", {}).get("AUD", {})
        flat.update(_flatten(aud_quote, prefix="aud_"))

        result[symbol] = flat

    logging.info("CMC quotes: received data for %d coins", len(result))
    return result


def fetch_cmc_global(session: requests.Session, api_key: str) -> dict:
    """
    Fetch all available global market metrics from CMC.

    Returns a flat dict of all scalar global fields (prefix: global_).
    The nested USD quote block is skipped as AUD is the project currency.
    """
    time.sleep(1)  # Space out CMC requests

    headers = {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}
    resp = session.get(CMC_GLOBAL_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    body = resp.json()

    if body.get("status", {}).get("error_code", 0) != 0:
        raise RuntimeError(
            f"CMC global API error: {body['status'].get('error_message', 'unknown')}"
        )

    return _flatten(body["data"], prefix="global_", skip_keys={"quote"})


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------
def build_rows(cmc_quotes: dict, cmc_global: dict, timestamp) -> list:
    """Merge CMC data into one row per coin."""
    rows = []
    for symbol in WATCHLIST:
        row = {
            "timestamp": timestamp,
            "symbol":    symbol,
        }
        row.update(cmc_quotes.get(symbol, {}))
        row.update(cmc_global)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# CSV writer (append mode)
# ---------------------------------------------------------------------------
def append_csv(rows: list):
    """
    Append rows to output/crypto_daily_snapshots.csv using pandas.

    If the existing file contains cg_* columns (old format), it is archived
    to crypto_daily_snapshots_archive_{date}.csv before writing the new file.

    Creates the file with a header on first run; appends without header after.
    Columns are inferred from the data — no hardcoded column list.
    """
    global df
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)

    # Archive old file if it has CoinGecko columns
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, encoding="utf-8-sig") as f:
            first_line = f.readline()
        if any(col.startswith("cg_") for col in first_line.split(",")):
            archive_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            archive_path = OUTPUT_DIR / f"crypto_daily_snapshots_archive_{archive_date}.csv"
            OUTPUT_CSV.rename(archive_path)
            logging.info("Archived old CSV (had cg_* columns) to %s", archive_path.name)

    write_header = not OUTPUT_CSV.exists()
    df.to_csv(OUTPUT_CSV, mode="a", index=False, header=write_header, encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# Run log
# ---------------------------------------------------------------------------
def log_run(status: str, rows: int, detail: str = ""):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"{ts} | crypto_daily_snapshot | rows={rows} | status={status}"
    if detail:
        line += f" | {detail}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    """
    Fetch CMC data, append to CSV, and populate the module-level `df`.

    Safe to call from a notebook or interactive session — no sys.exit() calls.
    Exit codes are only applied when the script is run directly.
    """
    setup_logging()
    timestamp = pd.to_datetime("now")

    api_key = load_config()

    with requests.Session() as session:
        logging.info(
            "Fetching quotes for %d coins from CoinMarketCap (AUD)...",
            len(WATCHLIST),
        )
        cmc_quotes = fetch_cmc_quotes(session, api_key)

        logging.info("Fetching global metrics from CoinMarketCap...")
        cmc_global = fetch_cmc_global(session, api_key)

    rows = build_rows(cmc_quotes, cmc_global, timestamp)
    append_csv(rows)

    log_run("SUCCESS", rows=len(rows))
    logging.info("Done. Appended %d rows to %s", len(rows), OUTPUT_CSV)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except EnvironmentError as e:
        logging.error(str(e))
        log_run("FAILED", rows=0, detail=str(e))
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logging.error("Network error: %s", e)
        log_run("FAILED", rows=0, detail=f"network error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logging.error(str(e))
        log_run("FAILED", rows=0, detail=str(e))
        sys.exit(1)
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        log_run("FAILED", rows=0, detail=str(e))
        sys.exit(1)