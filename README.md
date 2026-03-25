# Cryptocurrency Analysis Dashboard

A fully automated data pipeline that tracks a fixed watchlist of 20 major cryptocurrencies (AUD) — selected at project start based on market cap ranking — stores daily price snapshots in a star-schema data warehouse, and visualises them in an interactive Power BI dashboard with mobile support.

---

## What It Does

- Tracks a fixed watchlist of 20 major cryptocurrencies selected at project start based on market cap ranking
- Appends 20 rows per day to a rolling raw CSV (append-only, never overwritten)
- Rebuilds a star-schema from the raw data for use in Power BI
- Runs automatically every day via GitHub Actions - no PC required

---

## Dashboard

> Power BI dashboard with desktop and mobile layouts connected to live GitHub data.



---

## Architecture

This project follows the **WAT framework** (Workflows → Agent → Tools):

```
CoinMarketCap API
       │
       ▼
tools/crypto_daily_snapshot.py   ← fetches & appends raw data
       │
       ▼
output/raw/crypto_daily_snapshots.csv   ← append-only rolling CSV
       │
       ▼
tools/build_tables.py   ← builds star schema
       │
       ▼
output/tables/          ← dim_coin, dim_date, fact_coin_prices, fact_global_market
       │
       ▼
Power BI Dashboard      ← connected via GitHub raw CSV URLs
```

GitHub Actions runs both scripts daily at midnight UTC (10am AEST) and commits the updated data files back to the repo.

---

## Data Model

**Star schema - 4 tables:**

| Table | Type | Description |
|---|---|---|
| `dim_coin` | Dimension | Static coin attributes (name, slug, max supply) |
| `dim_date` | Dimension | Date hierarchy (year, quarter, month, week, day) |
| `fact_coin_prices` | Fact | Daily price, volume, and market cap per coin |
| `fact_global_market` | Fact | Daily global market metrics (BTC dominance, DeFi, stablecoins) |

**Relationships:**

```
fact_coin_prices ──── dim_coin        (on id)
fact_coin_prices ──── dim_date        (on date)
fact_global_market ── dim_date        (on date)
```

**Tracked coins:** BTC, ETH, BNB, SOL, XRP, DOGE, ADA, TRX, AVAX, TON, LINK, SHIB, DOT, POL, LTC, BCH, UNI, NEAR, XLM, ATOM

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data collection | Python, CoinMarketCap API |
| Storage | CSV (append-only raw + star-schema tables) |
| Automation | GitHub Actions (daily cron) |
| Visualisation | Power BI Desktop (desktop + mobile layout) |

---

## Project Structure

```
notebooks/           # Jupyter notebook for interactive analysis
output/
  raw/               # Rolling raw snapshot CSV (append-only)
  tables/            # Star-schema CSVs for Power BI
reports/             # Power BI report (.pbix)
logs/                # Execution log
tools/               # Python pipeline scripts
workflows/           # Markdown SOPs for each pipeline step
.github/workflows/   # GitHub Actions automation
requirements.txt
```

---

## Running Locally

```bash
# 1. Clone the repo
git clone https://github.com/Tharindu-Senanayake/cryptocurrency-analysis-dashboard.git
cd cryptocurrency-analysis-dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your CoinMarketCap API key
echo CMC_API_KEY=your_key_here > .env

# 4. Fetch today's data
python tools/crypto_daily_snapshot.py

# 5. Build the star-schema tables
python tools/build_tables.py
```

---

## Automation

GitHub Actions runs the full pipeline daily:

- **Schedule:** midnight UTC (10am AEST / 11am AEDT)
- **Steps:** checkout → install deps → fetch snapshot → build tables → commit & push data
- **Secret required:** `CMC_API_KEY` (add under repo Settings → Secrets → Actions)

---

## Acknowledgements

- Data sourced from [CoinMarketCap API](https://coinmarketcap.com/api/)
- Project structure and pipeline setup assisted by [Claude Code](https://claude.ai/code)
