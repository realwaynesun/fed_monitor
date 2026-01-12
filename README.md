# Wayne's Macro Dashboard

A Fed monetary policy monitoring system that tracks FRED economic data, calculates derived metrics, and provides alerts on threshold breaches.

**Live Dashboard**: https://realwaynesun.github.io/fed_monitor/

## Features

- **Key Metrics Panel**: EFFR, IORB, SOFR, spreads, reserves at a glance
- **16 Interactive Charts**: Policy rates, balance sheet, financial conditions
- **Automated Alerts**: Telegram notifications on threshold breaches
- **Mobile Responsive**: Works on desktop, tablet, and phone
- **Daily Updates**: Automated via GitHub Actions

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your FRED_API_KEY

# Fetch data
python scripts/fetch_data.py --backfill

# Build static dashboard
python scripts/export_json.py

# Preview locally
cd static && python3 -m http.server 8080
```

## Project Structure

```
fed_monitor/
├── config/
│   └── fed_monitor_config.yaml    # Series, metrics, alerts, charts
├── src/
│   ├── config.py                  # YAML loader
│   ├── database.py                # SQLite operations
│   ├── fred_client.py             # FRED API client
│   ├── metrics.py                 # Derived metrics calculation
│   ├── alerts.py                  # Alert rule evaluation
│   └── notifier.py                # Telegram notifications
├── scripts/
│   ├── fetch_data.py              # Fetch FRED data
│   ├── export_json.py             # Export to JSON for static site
│   ├── check_alerts.py            # Evaluate alert rules
│   └── run_scheduler.py           # Automated scheduler
├── static/
│   ├── index.html                 # Static dashboard (Plotly.js)
│   └── data.json                  # Dashboard data
└── .github/workflows/
    └── deploy-pages.yml           # GitHub Pages deployment
```

## Environment Variables

Create `.env` from `.env.example`:

```
FRED_API_KEY=your_key_here          # Required - get from fred.stlouisfed.org
TELEGRAM_BOT_TOKEN=your_bot_token   # Optional - for alerts
TELEGRAM_CHAT_ID=your_chat_id       # Optional - for alerts
```

## Documentation

- [PLAN.md](PLAN.md) - Implementation plan and architecture
- [CLAUDE.md](CLAUDE.md) - AI assistant instructions
- [.claude/SKILLS.md](.claude/SKILLS.md) - Reusable workflows

## License

MIT License - Use it however you want.
