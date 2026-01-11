# Fed Monitor Implementation Plan

## Overview

Build a Fed monetary policy monitoring system with:
- **P0**: Static HTML dashboard (GitHub Pages) for data visualization
- **P1**: Telegram alerts on critical threshold breaches
- **P2**: Automated UI review workflow

---

## Phase 1: Foundation (Completed)

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Dashboard | Static HTML + Plotly.js | No server needed, GitHub Pages hosting |
| Database | SQLite | Sufficient for single user, ~50 series, 2 years |
| Charts | Plotly.js | Interactive, good time series support |
| Data | pandas | Standard for time series manipulation |
| HTTP | requests | Simple, no async complexity needed |
| Telegram | requests (raw API) | Simpler than python-telegram-bot for just sending |
| Scheduler | APScheduler + GitHub Actions | Local + automated daily updates |

### Project Structure

```
fed_monitor/
├── config/
│   └── fed_monitor_config.yaml    # Series, derived metrics, alerts, charts
├── src/
│   ├── config.py                  # YAML loader + validation
│   ├── database.py                # SQLite schema + queries
│   ├── fred_client.py             # FRED API wrapper
│   ├── metrics.py                 # Derived metrics + rolling calcs
│   ├── alerts.py                  # Rule evaluation + state tracking
│   └── notifier.py                # Telegram sender
├── dashboard/
│   └── app.py                     # Streamlit dashboard (legacy)
├── static/
│   ├── index.html                 # Static dashboard
│   └── data.json                  # Exported data for static site
├── scripts/
│   ├── fetch_data.py              # CLI: fetch latest data
│   ├── check_alerts.py            # CLI: evaluate alerts
│   ├── export_json.py             # Export data to JSON
│   ├── build_static.sh            # Build script
│   └── run_scheduler.py           # Long-running scheduled jobs
├── .github/
│   └── workflows/
│       └── deploy-pages.yml       # GitHub Pages deployment
├── .claude/
│   └── SKILLS.md                  # Reusable workflows
└── requirements.txt
```

---

## Phase 2: Static Dashboard Migration (Completed)

### Goal
Replace Streamlit with static HTML for:
- Zero server maintenance
- Free GitHub Pages hosting
- Full control over design
- Mobile-friendly responsive design

### Implementation Steps
1. Create `scripts/export_json.py` to export dashboard data
2. Create `static/index.html` with Plotly.js charts
3. Add responsive CSS for mobile/tablet
4. Set up GitHub Actions for daily deployment

### Key Features
- Dark theme matching original Streamlit design
- Interactive Plotly.js charts
- Responsive layout (desktop, tablet, phone)
- Automatic daily updates via GitHub Actions

---

## Phase 3: GitHub Pages Deployment (Completed)

### Workflow: `.github/workflows/deploy-pages.yml`

```yaml
name: Deploy to GitHub Pages
on:
  schedule:
    - cron: '0 7 * * *'  # Daily at 7am UTC
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - Checkout repo
      - Setup Python
      - Install dependencies
      - Fetch FRED data
      - Export to JSON
      - Deploy to GitHub Pages
```

### URL
https://realwaynesun.github.io/fed_monitor/

---

## Phase 4: Professional UI Review (Completed)

### Goal
Automated dashboard review from economist/trader perspective using Playwright.

### Review Criteria

#### 1. Professional Economist Perspective
- **Data hierarchy**: Most important metrics (EFFR, reserves, spreads) prominently displayed
- **Alert clarity**: Threshold breaches immediately visible and actionable
- **Metric groupings**: Logical groupings (policy rates, balance sheet, financial stress)
- **Time context**: Sufficient historical context for trend analysis

#### 2. Trader Perspective
- **Glanceability**: Key readings understood in <5 seconds
- **Signal clarity**: Warning signs (spread blowouts, reserve stress) unmistakable
- **Comparison ease**: Related metrics easily compared (EFFR vs IORB)
- **Mobile usability**: Usable on phone between trades

#### 3. Technical Professionalism
- **Visual consistency**: Consistent colors, fonts, spacing
- **Chart best practices**: Appropriate chart types, clear labels, readable axes
- **Information density**: Right balance of data vs whitespace
- **Color semantics**: Red=bad, green=good applied consistently

### Implementation
1. Install Playwright in venv
2. Capture screenshots at 3 viewports (desktop, tablet, phone)
3. Analyze against criteria
4. Implement fixes
5. Deploy and verify

### Playwright Script
```python
from playwright.sync_api import sync_playwright

VIEWPORTS = [
    {"name": "desktop", "width": 1920, "height": 1080},
    {"name": "tablet", "width": 768, "height": 1024},
    {"name": "phone", "width": 375, "height": 812},
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for vp in VIEWPORTS:
        page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
        page.goto("https://realwaynesun.github.io/fed_monitor/")
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        page.screenshot(path=f"/tmp/dashboard_{vp['name']}.png", full_page=True)
        page.close()
    browser.close()
```

---

## Phase 5: Dashboard Improvements (Completed)

### Key Metrics Summary Panel
- 8 metrics at top for instant glance
- EFFR, IORB, SOFR (rates - cyan)
- EFFR-IORB, SOFR-EFFR (spreads - yellow)
- Fed Assets, RRP Usage, Reserves (balance - teal)
- Daily change indicators (+/-)

### Alert Visibility Improvements
- Status dots next to each alert item
- Color-coded by severity (red/yellow/blue)
- Better visual hierarchy

### Chart Enhancements
- Current value annotations on desktop/tablet
- Line styles for visual hierarchy (dashed for bounds)
- Short labels for cleaner legends

### Responsive Design
- 4-column grid for key metrics on all devices
- Hidden legends on phone (hover to see)
- Taller charts on mobile (280px)
- Horizontal scrollable tables

---

## Future Plans

### P2: Enhanced Alerts
- Email notifications as backup to Telegram
- Weekly summary reports
- Alert history dashboard

### P3: Data Enhancements
- Add more FRED series (bank reserves, repo volumes)
- Historical event annotations on charts
- Recession shading

### P4: Advanced Features
- Custom alert rules via UI
- Multiple dashboard themes
- Export to PDF reports

---

## Environment Variables (.env)

```
FRED_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## Quick Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Data
python scripts/fetch_data.py --backfill    # Full 2-year backfill
python scripts/fetch_data.py               # Incremental fetch

# Build static site
python scripts/export_json.py              # Export to JSON
cd static && python3 -m http.server 8080   # Local preview

# Alerts
python scripts/check_alerts.py --dry-run   # Evaluate without notifications
python scripts/check_alerts.py --summary   # Show current breaches

# UI Review
source venv/bin/activate
pip install playwright
playwright install chromium
python /tmp/capture_dashboard.py           # Capture screenshots
```

---

## Verification Checklist

- [x] FRED data fetching works
- [x] Derived metrics calculate correctly
- [x] Static dashboard renders all charts
- [x] GitHub Pages deployment succeeds
- [x] Mobile responsive design works
- [x] Key metrics panel shows all 8 metrics
- [x] Alerts display with status dots
- [x] Playwright screenshots capture correctly
