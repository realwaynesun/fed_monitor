# Fed Monitor Skills

Reusable workflows for the Fed Monitor project. Use these by typing the command (e.g., `/push`) or asking Claude to perform the workflow.

---

## /push - Push to Main

Push all changes to the main branch.

```bash
git status
git diff
git add -A
git commit -m "<message>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push origin main
```

---

## /deploy - Deploy to GitHub Pages

Deploy static dashboard and monitor status.

```bash
gh run list --limit 3                    # Check status
gh workflow run deploy-pages.yml         # Manual trigger
gh run watch <run-id>                    # Watch progress
```

URL: https://realwaynesun.github.io/fed_monitor/

---

## /build - Build Static Dashboard

Fetch FRED data and export to JSON.

```bash
./scripts/build_static.sh                # Quick build
python scripts/fetch_data.py             # Fetch only
python scripts/export_json.py            # Export only
```

---

## /serve - Run Local Server

Preview dashboard locally.

```bash
cd static && python3 -m http.server 8080
# Open http://localhost:8080
```

---

## /backfill - Backfill FRED Data

Fetch historical data for all series.

```bash
python scripts/fetch_data.py --backfill  # Full 2-year backfill
python scripts/fetch_data.py --days 30   # Last N days
```

---

## /alerts - Check Alerts

Evaluate alert rules and notifications.

```bash
python scripts/check_alerts.py --dry-run      # No notifications
python scripts/check_alerts.py --summary      # Show breaches
python scripts/check_alerts.py --test-telegram # Test connection
```

---

## /review-charts - Review Chart Issues

Analyze and fix chart display problems.

**Common issues:**
- Crowded legends → Use SHORT_LABELS mapping
- Wrong chart type → Time series = line charts
- Scale mismatch → Split into separate charts
- Mobile overlap → Hide legends, increase height

**Files:** `static/index.html` (Plotly.js), `dashboard/app.py` (Streamlit)

---

## /fix-mobile - Fix Mobile Display

Address responsive design issues.

**CSS breakpoints:**
- Tablet: `@media (max-width: 768px)`
- Phone: `@media (max-width: 480px)`

**Common fixes:**
- Chart height: increase to 280px minimum
- Legends: hide on phone (`showlegend: false`)
- Margins: increase left margin for y-axis labels
- Tables: add `overflow-x: auto`

---

## /update-config - Update Configuration

Apply new YAML config changes.

1. Compare with `config/fed_monitor_config.yaml`
2. Check for code changes needed in `src/metrics.py`, `src/alerts.py`
3. Apply config
4. Run `python scripts/fetch_data.py --backfill` for new series
5. Test with `./scripts/build_static.sh`

---

## /check-deploy - Check Deployment Status

Monitor GitHub Actions.

```bash
gh run list --limit 5           # List runs
gh run view <id>                # Details
gh run view <id> --log          # With logs
gh run rerun <id>               # Re-run failed
```

---

## Quick Reference

| Skill | Purpose |
|-------|---------|
| `/push` | Commit and push to main |
| `/deploy` | Deploy to GitHub Pages |
| `/build` | Fetch data + export JSON |
| `/serve` | Local HTTP server |
| `/backfill` | Fetch historical FRED data |
| `/alerts` | Check alert rules |
| `/review-charts` | Fix chart issues |
| `/fix-mobile` | Fix responsive design |
| `/update-config` | Apply new config |
| `/check-deploy` | Monitor deployments |
