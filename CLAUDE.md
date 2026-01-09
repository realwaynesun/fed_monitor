# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Then add required keys (see Environment Variables below)

# Data fetching
python scripts/fetch_data.py --backfill    # Initial 2-year backfill
python scripts/fetch_data.py               # Incremental fetch (new data only)
python scripts/fetch_data.py --days 30     # Fetch last N days

# Dashboard
streamlit run dashboard/app.py

# Alerts
python scripts/check_alerts.py --dry-run   # Evaluate without notifications
python scripts/check_alerts.py --summary   # Show current breaches
python scripts/check_alerts.py --test-telegram  # Test Telegram connection

# Scheduler (long-running daemon)
python scripts/run_scheduler.py
```

## Environment Variables

Required in `.env`:
- `FRED_API_KEY` - Get from https://fred.stlouisfed.org/ (My Account → API Keys)
- `TELEGRAM_BOT_TOKEN` - Create via @BotFather on Telegram (required for alerts)
- `TELEGRAM_CHAT_ID` - Your chat ID for receiving notifications

## Architecture

This is a Fed monetary policy monitoring system that fetches FRED data, calculates derived metrics, and sends Telegram alerts on threshold breaches.

### Data Flow

1. **FRED API → SQLite**: `fred_client.py` fetches raw series, stores in `observations` table
2. **Raw → Derived**: `metrics.py` calculates derived metrics (spreads, ratios) using pandas eval on expressions from config
3. **Derived → Alerts**: `alerts.py` evaluates rule expressions against metric context (value, d1, d5, ma20, etc.)
4. **Alerts → Telegram**: `notifier.py` sends on state transitions (OK→BREACH only, not repeated breaches)

### Config-Driven Design

Everything is defined in `config/fed_monitor_config.yaml`:
- **series**: FRED series IDs to fetch (key, series_id, frequency, unit)
- **derived**: Calculated metrics with pandas-compatible expressions (e.g., `"(effr - iorb) * 100"`)
- **metrics**: Change periods (d1, d5, d20) and rolling windows (ma5, ma20, zscore20)
- **alerts**: Rules like `"value > 5"` or `"abs(d1) > 100"` with severity levels
- **panel**: Dashboard chart/table layouts

### Key Patterns

- **Config singleton**: `get_config()` returns cached `FedMonitorConfig` instance
- **Weekly data alignment**: Weekly FRED series are forward-filled to daily via `df.resample("D").ffill()`
- **Alert state tracking**: SQLite `alert_state` table tracks OK/BREACH state; notifications only fire on transitions
- **Safe eval**: Alert rules use restricted eval with only `abs`, `min`, `max` builtins

### Database Tables (SQLite)

- `observations`: Raw FRED data (series_key, date, value)
- `derived_metrics`: Calculated values
- `alert_state`: Current breach state per alert
- `alerts_log`: Historical state transitions
- `fetch_log`: Data fetch history for debugging

### Modifying Configuration

All changes to series, alerts, and dashboard layout are made in `config/fed_monitor_config.yaml`. After editing:
- **New series**: Run `fetch_data.py --backfill` to populate data
- **New derived metrics**: Data calculated on-the-fly from raw series
- **New alerts**: Take effect on next `check_alerts.py` run
- **Dashboard changes**: Reflected on next page load (5-minute cache TTL)

### Alert ID Generation

Alert IDs are generated as `{key}:{severity}:{hash(rule) % 10000}`. This allows multiple rules per metric (e.g., warning at 10, critical at 25) while maintaining stable state tracking across config edits.
