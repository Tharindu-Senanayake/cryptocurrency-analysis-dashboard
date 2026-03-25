"""
build_tables.py

Reads the raw daily snapshot CSV and builds 4 star-schema tables:
  dim_coin           - one row per coin (static attributes)
  dim_date           - one row per calendar date
  fact_coin_prices   - one row per coin per snapshot (price/market metrics)
  fact_global_market - one row per snapshot (global market metrics)

Run after crypto_daily_snapshot.py has appended new data.

Run manually:
    python tools/build_tables.py
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).resolve().parent.parent
RAW_DIR    = BASE_DIR / "output" / "raw"
TABLES_DIR = BASE_DIR / "output" / "tables"
LOG_DIR    = BASE_DIR / "logs"
LOG_FILE   = LOG_DIR / "run.log"
INPUT_CSV  = RAW_DIR / "crypto_daily_snapshots.csv"

OUTPUT_TABLES = {
    "dim_coin":           TABLES_DIR / "dim_coin.csv",
    "dim_date":           TABLES_DIR / "dim_date.csv",
    "fact_coin_prices":   TABLES_DIR / "fact_coin_prices.csv",
    "fact_global_market": TABLES_DIR / "fact_global_market.csv",
}


# ---------------------------------------------------------------------------
# Logging
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
# Run log
# ---------------------------------------------------------------------------
def log_run(status: str, detail: str = ""):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"{ts} | build_tables | status={status}"
    if detail:
        line += f" | {detail}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    setup_logging()

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Raw snapshot CSV not found: {INPUT_CSV}")

    logging.info("Loading %s", INPUT_CSV.name)
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    logging.info("Loaded %d rows, %d columns", len(df), len(df.columns))

    # Deduplicate
    df = df.drop_duplicates(subset=["timestamp", "symbol"], keep="first")

    # Select working columns
    df2 = df[[
        "timestamp", "id", "symbol", "name", "slug", "cmc_rank", "date_added",
        "max_supply", "circulating_supply", "total_supply", "infinite_supply",
        "last_updated", "aud_price", "aud_volume_24h",
        "aud_cex_volume_24h", "aud_dex_volume_24h", "aud_volume_change_24h",
        "aud_percent_change_1h", "aud_percent_change_24h", "aud_percent_change_7d",
        "aud_percent_change_30d", "aud_percent_change_60d", "aud_percent_change_90d",
        "aud_market_cap", "aud_market_cap_dominance", "aud_fully_diluted_market_cap",
        "global_eth_dominance", "global_btc_dominance", "global_defi_volume_24h",
        "global_defi_market_cap", "global_stablecoin_volume_24h",
        "global_stablecoin_market_cap", "global_derivatives_volume_24h",
    ]].copy()

    # Parse datetimes
    df2["timestamp"]    = pd.to_datetime(df2["timestamp"])
    df2["last_updated"] = pd.to_datetime(df2["last_updated"])
    df2["date_added"]   = pd.to_datetime(df2["date_added"])

    # Fix integer columns
    df2["id"]       = df2["id"].astype(int)
    df2["cmc_rank"] = df2["cmc_rank"].astype(int)

    # Add date column
    df2["date"] = df2["timestamp"].dt.normalize()

    # --- dim_coin ---
    dim_coin = df2[["id", "symbol", "name", "slug", "date_added", "max_supply", "infinite_supply"]].copy()
    dim_coin = dim_coin.drop_duplicates(subset=["id"], keep="first")

    # --- fact_coin_prices ---
    fact_coin_prices = df2[[
        "timestamp", "date", "id", "cmc_rank", "circulating_supply",
        "total_supply", "aud_price", "aud_volume_24h", "aud_cex_volume_24h",
        "aud_dex_volume_24h", "aud_volume_change_24h", "aud_percent_change_1h",
        "aud_percent_change_24h", "aud_percent_change_7d", "aud_percent_change_30d",
        "aud_percent_change_60d", "aud_percent_change_90d", "aud_market_cap",
        "aud_market_cap_dominance", "aud_fully_diluted_market_cap",
    ]].copy()

    # --- fact_global_market ---
    fact_global_market = df2[[
        "timestamp", "date", "global_btc_dominance", "global_eth_dominance",
        "global_defi_volume_24h", "global_defi_market_cap",
        "global_stablecoin_volume_24h", "global_stablecoin_market_cap",
        "global_derivatives_volume_24h",
    ]].drop_duplicates(subset=["timestamp", "date"]).copy()

    # --- dim_date ---
    dim_date = df2[["date"]].drop_duplicates().copy()
    dim_date["year"]        = dim_date["date"].dt.year
    dim_date["quarter"]     = dim_date["date"].dt.quarter
    dim_date["month"]       = dim_date["date"].dt.month
    dim_date["day"]         = dim_date["date"].dt.day
    dim_date["month_name"]  = dim_date["date"].dt.month_name()
    dim_date["week"]        = dim_date["date"].dt.isocalendar().week.astype(int)
    dim_date["day_of_week"] = dim_date["date"].dt.dayofweek
    dim_date["day_name"]    = dim_date["date"].dt.day_name()

    # --- Save ---
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    tables = {
        "dim_coin":           dim_coin,
        "dim_date":           dim_date,
        "fact_coin_prices":   fact_coin_prices,
        "fact_global_market": fact_global_market,
    }

    for name, tdf in tables.items():
        path = OUTPUT_TABLES[name]
        tdf.to_csv(path, index=False, encoding="utf-8-sig")
        logging.info("Saved %s - %d rows, %d cols", name, len(tdf), len(tdf.columns))

    log_run("SUCCESS", detail=f"tables built from {len(df)} raw rows")
    logging.info("Done.")


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except FileNotFoundError as e:
        logging.error(str(e))
        log_run("FAILED", detail=str(e))
        sys.exit(1)
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        log_run("FAILED", detail=str(e))
        sys.exit(1)
