# Workflow: Build Star-Schema Tables

**Objective:** Read the raw daily snapshot CSV and produce 4 clean star-schema tables for Power BI in `output/tables/`.

---

## Inputs

| Input | Source | Notes |
|-------|--------|-------|
| Raw snapshot CSV | `output/raw/crypto_daily_snapshots.csv` | Must exist before running |

---

## Tool

```
tools/build_tables.py
```

**Run manually (after `crypto_daily_snapshot.py`):**
```bash
python tools/build_tables.py
```

---

## Output

| Table | Location | Grain | Notes |
|-------|----------|-------|-------|
| `dim_coin` | `output/tables/dim_coin.csv` | One row per coin | Keyed on `id` |
| `dim_date` | `output/tables/dim_date.csv` | One row per calendar date | Keyed on `date` |
| `fact_coin_prices` | `output/tables/fact_coin_prices.csv` | One row per coin per snapshot | FK: `id` → `dim_coin`, `date` → `dim_date` |
| `fact_global_market` | `output/tables/fact_global_market.csv` | One row per snapshot | FK: `date` → `dim_date` |
| Run log | `logs/run.log` | One line per execution | |

**Note:** All 4 table CSVs are overwritten on each run - they are always rebuilt from the full raw CSV.

---

## Column Groups

**dim_coin:** `id`, `symbol`, `name`, `slug`, `date_added`, `max_supply`, `infinite_supply`

**dim_date:** `date`, `year`, `quarter`, `month`, `day`, `month_name`, `week`, `day_of_week`, `day_name`

**fact_coin_prices:** `timestamp`, `date`, `id`, `cmc_rank`, `circulating_supply`, `total_supply`, `aud_price`, `aud_volume_24h`, `aud_cex_volume_24h`, `aud_dex_volume_24h`, `aud_volume_change_24h`, `aud_percent_change_*`, `aud_market_cap`, `aud_market_cap_dominance`, `aud_fully_diluted_market_cap`

**fact_global_market:** `timestamp`, `date`, `global_btc_dominance`, `global_eth_dominance`, `global_defi_volume_24h`, `global_defi_market_cap`, `global_stablecoin_volume_24h`, `global_stablecoin_market_cap`, `global_derivatives_volume_24h`

---

## Cleaning Applied

| Step | Detail |
|------|--------|
| Deduplicate | On `timestamp + symbol`, keep first |
| Parse datetimes | `timestamp`, `last_updated`, `date_added` → datetime |
| Fix integers | `id`, `cmc_rank` → int |
| Add `date` column | Normalized from `timestamp` (time component stripped) |
| Deduplicate dims | `dim_coin` on `id`; `dim_date` on `date` |
| Deduplicate global | `fact_global_market` on `timestamp + date` |

---

## Edge Cases & Failure Handling

| Scenario | Behaviour |
|----------|-----------|
| Raw CSV missing | Exits with code `1`, logs error |
| Column missing from raw CSV | Raises `KeyError`, logs, exits `1` |
| Unexpected error | Logs full error, exits `1` |
| `output/tables/` missing | Created automatically |

---

## Maintenance

- **Add/remove columns:** Update the column selection lists in `build_tables.py` and this workflow.
- **Add a new table:** Add the DataFrame to the `tables` dict in `build_tables.py`.
- **Run order:** Always run `crypto_daily_snapshot.py` first, then `build_tables.py`.
