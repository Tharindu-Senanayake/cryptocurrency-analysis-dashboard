# Workflow: Daily Crypto Snapshot

**Objective:** Append 20 rows (one per coin) to `output/crypto_daily_snapshots.csv` with today's market data for the top 20 cryptocurrencies in AUD.

---

## Inputs

| Input | Source | Notes |
|-------|--------|-------|
| `CMC_API_KEY` | `.env` | Free-tier CoinMarketCap key |
| Watchlist | Hardcoded in script | 20 symbols — edit `WATCHLIST` list in script to change |
| Currency | AUD | Hardcoded |

---

## Data Sources

| Source | API | Credentials | Fields fetched |
|--------|-----|-------------|----------------|
| CoinMarketCap | `pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest` | `CMC_API_KEY` | All coin-level fields + AUD quote fields |
| CoinMarketCap Global | `pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest` | `CMC_API_KEY` | All global market metrics |

**Total API calls per run: 2** (independent of watchlist size).

---

## Tool

```
tools/crypto_daily_snapshot.py
```

**Run manually:**
```bash
python tools/crypto_daily_snapshot.py
```

---

## Output

| Item | Location | Notes |
|------|----------|-------|
| CSV data | `output/raw/crypto_daily_snapshots.csv` | Appended — never overwritten |
| Run log | `logs/run.log` | One line per execution |

**CSV column groups:**

| Column prefix | Source | Example columns |
|---------------|--------|-----------------|
| *(none)* | CMC coin-level | `id`, `name`, `symbol`, `slug`, `cmc_rank`, `circulating_supply`, `total_supply`, `last_updated` |
| `aud_` | CMC AUD quote | `aud_price`, `aud_volume_24h`, `aud_market_cap`, `aud_percent_change_24h`, `aud_percent_change_7d` |
| `global_` | CMC global metrics | `global_btc_dominance`, `global_total_market_cap`, `global_active_cryptocurrencies` |

**Manually added columns:** `timestamp` (script run time), `symbol`

**Unique key per row:** `timestamp + symbol`

---

## Scheduling (Windows Task Scheduler)

1. Open Task Scheduler → Create Basic Task
2. **Trigger:** Daily, preferred time `08:00` (after markets settle)
3. **Action:** Start a Program
   - Program: `C:\path\to\python.exe`
   - Arguments: `tools/crypto_daily_snapshot.py`
   - Start in: `D:\Portfolio\Cryptocurrency analysis`
4. **Settings:** Run whether user is logged on or not; do not store password if script has no GUI

**Exit codes:** `0` = success, `1` = failure (logged to `run.log`)

---

## Edge Cases & Failure Handling

| Scenario | Behaviour |
|----------|-----------|
| `CMC_API_KEY` missing or blank | Exits with code `1`, logs error — no API call made |
| CMC returns non-zero error code | Raises `RuntimeError`, logs message, exits `1` |
| Network timeout (>15s) | Raises `requests.exceptions.RequestException`, logs, exits `1` |
| Symbol not returned by CMC | Row still written with only `timestamp` and `symbol` — CMC fields empty |
| Script run twice on the same day | Duplicate rows appended — deduplicate in analysis using `timestamp + symbol` key |
| Output directory missing | Created automatically |
| Existing CSV has `cg_*` columns (old format) | Archived to `crypto_daily_snapshots_archive_{date}.csv` before new file is created |

---

## Maintenance

- **Add/remove a coin:** Edit the `WATCHLIST` list in `tools/crypto_daily_snapshot.py`. Use the CMC symbol (e.g. `"BTC"`).
- **Change currency:** Update `convert` param in `fetch_cmc_quotes` and prefix convention for quote columns.
- **Rotate API key:** Update `CMC_API_KEY` in `.env` — no code change needed.
- **Check free-tier limits:** CoinMarketCap free tier allows ~333 calls/day. This script uses 2 per run — safe for multiple runs daily.
- **Interactive use:** Import and call `main()` from a notebook — `df` is populated after each run with no `sys.exit()` side effects.
