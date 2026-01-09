# Fed Monitor Implementation Plan

## Overview
Build a Fed monetary policy monitoring system with:
- **P0**: Web dashboard (Streamlit) for data visualization
- **P1**: Telegram alerts on critical threshold breaches

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Dashboard | Streamlit | Simplest for Python, good charts, easy to share later |
| Database | SQLite | Sufficient for single user, ~20 series, 2 years |
| Charts | Plotly (via Streamlit) | Interactive, good time series support |
| Data | pandas | Standard for time series manipulation |
| HTTP | requests | Simple, no async complexity needed |
| Telegram | requests (raw API) | Simpler than python-telegram-bot for just sending |
| Scheduler | APScheduler | Robust, cron syntax support |

## Project Structure

Location: `~/fed_monitor/`

```
fed_monitor/
├── config/
│   └── fed_monitor_config.yaml    # Your existing config (copy here)
├── src/
│   ├── __init__.py
│   ├── config.py                  # YAML loader + validation
│   ├── database.py                # SQLite schema + queries
│   ├── fred_client.py             # FRED API wrapper
│   ├── metrics.py                 # Derived metrics + rolling calcs
│   ├── alerts.py                  # Rule evaluation + state tracking
│   └── notifier.py                # Telegram sender
├── dashboard/
│   └── app.py                     # Streamlit dashboard
├── scripts/
│   ├── fetch_data.py              # CLI: fetch latest data
│   ├── check_alerts.py            # CLI: evaluate alerts
│   └── run_scheduler.py           # Long-running scheduled jobs
├── requirements.txt
├── .env.example                   # Template for API keys
└── fed_monitor.db                 # SQLite database (auto-created)
```

## Implementation Phases

### Phase 1: Foundation
1. **Config loader** (`src/config.py`)
   - Parse YAML, validate structure
   - Expose typed access to series, derived, alerts

2. **Database** (`src/database.py`)
   - Tables: `observations`, `derived_metrics`, `alerts_log`, `fetch_log`
   - Helper functions for insert/query

3. **FRED client** (`src/fred_client.py`)
   - Fetch single series
   - Handle rate limiting (100 req/min)
   - Backfill support (2 years)

### Phase 2: Metrics Engine
4. **Metrics calculator** (`src/metrics.py`)
   - Evaluate derived expressions (safe eval with pandas)
   - Compute rolling stats (ma5, ma20, std20, zscore20)
   - Compute diffs (d1, d5, d20, pct1, pct5)

### Phase 3: Dashboard (P0)
5. **Streamlit app** (`dashboard/app.py`)
   - Sidebar: date range picker (30D/90D/1Y/Custom)
   - 8 charts as defined in config
   - 2 data tables
   - Manual refresh button
   - Alert status panel (current breaches)

### Phase 4: Alerts (P1)
6. **Alert evaluator** (`src/alerts.py`)
   - Parse rule expressions
   - Track state: OK ↔ BREACH
   - Only notify on state transitions (not repeated breaches)

7. **Telegram notifier** (`src/notifier.py`)
   - Send formatted messages
   - Include: metric name, current value, threshold, trend context

### Phase 5: Automation
8. **Scheduler** (`scripts/run_scheduler.py`)
   - Daily fetch at 7am Tokyo (weekdays)
   - Weekly H.4.1 fetch Thursday 8am
   - Alert checks every 30 min during trading hours
   - Daily summary at 10pm (significant changes only)

## Key Design Decisions

### Derived Metrics Evaluation
Use pandas eval with a restricted namespace:
```python
# Safe: only allows series keys + basic math
df.eval("(effr - iorb) * 100")
```

### Alert State Tracking
Store in SQLite `alerts_log`:
```
| alert_key | state | last_transition_time | last_value |
```
Only send Telegram when `state` changes from OK to BREACH.

### Forward-Fill for Weekly Data
When loading data for dashboard/alerts:
```python
df = df.resample('D').ffill()  # Fill gaps in weekly series
```

### Dashboard Sharing (Later)
- Option 1: Streamlit Community Cloud (free, public URL)
- Option 2: Basic auth via `streamlit-authenticator`
- Option 3: Deploy on cloud VM with nginx + password

## Environment Variables (.env)

```
FRED_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## FRED API Key Instructions

1. Go to https://fred.stlouisfed.org/
2. Click "My Account" → Sign up (free)
3. Go to "API Keys" in account settings
4. Click "Request API Key"
5. Copy key to `.env` file

## Telegram Bot Setup

1. Message @BotFather on Telegram
2. Send `/newbot`, follow prompts
3. Copy the bot token to `.env`
4. Message your new bot, then visit:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Find your `chat_id` in the response, add to `.env`

## Verification Plan

### After Phase 1-2 (Foundation):
```bash
python scripts/fetch_data.py --backfill
# Verify: fed_monitor.db has data, no errors
```

### After Phase 3 (Dashboard):
```bash
streamlit run dashboard/app.py
# Verify: All 8 charts render, tables show values
```

### After Phase 4-5 (Alerts):
```bash
python scripts/check_alerts.py --dry-run
# Verify: Rules evaluate, state tracking works
# Then test with real Telegram notification
```

## Dependencies (requirements.txt)

```
pandas>=2.0
pyyaml>=6.0
requests>=2.28
streamlit>=1.30
plotly>=5.18
python-dotenv>=1.0
apscheduler>=3.10
```

## Estimated Lines of Code

| File | ~Lines |
|------|--------|
| config.py | 80 |
| database.py | 120 |
| fred_client.py | 100 |
| metrics.py | 150 |
| alerts.py | 100 |
| notifier.py | 50 |
| dashboard/app.py | 300 |
| scripts/* | 150 |
| **Total** | **~1050** |
