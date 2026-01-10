#!/usr/bin/env python3
"""
Export dashboard data to static JSON for the static HTML dashboard.
Run this daily via cron to keep data fresh.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.database import init_db
from src.metrics import calculate_all_metrics, get_latest_values
from src.alerts import evaluate_all_alerts


def export_dashboard_data(output_dir: Path, days: int = 365):
    """Export all dashboard data to JSON files."""

    init_db()
    config = get_config()

    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"Exporting data from {start_str} to {end_str}...")

    # Calculate metrics (no ffill for charts)
    df = calculate_all_metrics(start_str, end_str, ffill=False)

    if df.empty:
        print("Error: No data available")
        return False

    # Build chart data
    charts_data = []
    for chart_def in config.panel_charts:
        title = chart_def["title"]
        series_keys = chart_def["series"]
        chart_type = chart_def.get("chart_type", "line")
        y_label = chart_def.get("y_axis_label", "")
        height = chart_def.get("height", 400)
        ref_line = chart_def.get("reference_line")

        # Get available series
        available = [k for k in series_keys if k in df.columns]
        if not available:
            continue

        # Build series data
        series_data = []
        for key in available:
            series_def = config.get_series(key) or config.get_derived(key) or {}
            label = series_def.get("label", key)

            # Get non-null data points
            s = df[key].dropna()

            series_data.append({
                "key": key,
                "label": label,
                "dates": [d.strftime("%Y-%m-%d") for d in s.index],
                "values": [round(v, 4) if v == v else None for v in s.values],
            })

        charts_data.append({
            "title": title,
            "type": chart_type,
            "y_label": y_label,
            "height": height,
            "reference_line": ref_line,
            "series": series_data,
        })

    # Build table data
    latest = get_latest_values()
    tables_data = []

    for table_def in config.panel_tables:
        title = table_def["title"]
        series_keys = table_def["series"]
        columns = table_def.get("show_columns", ["value", "d1", "d5"])

        rows = []
        for key in series_keys:
            if key not in latest:
                continue

            metrics = latest[key]
            series_def = config.get_series(key) or config.get_derived(key) or {}
            unit = series_def.get("unit", "")

            row = {
                "key": key,
                "label": series_def.get("label", key),
                "unit": unit,
                "date": metrics.get("date", ""),
            }

            for col in columns:
                if col == "value":
                    row["value"] = metrics.get("value")
                elif col in metrics:
                    row[col] = metrics.get(col)

            rows.append(row)

        tables_data.append({
            "title": title,
            "columns": columns,
            "rows": rows,
        })

    # Get alerts
    try:
        alert_results = evaluate_all_alerts()
        alerts_data = {
            "critical": [a for a in alert_results if a["severity"] == "critical" and a["triggered"]],
            "warning": [a for a in alert_results if a["severity"] == "warning" and a["triggered"]],
            "info": [a for a in alert_results if a["severity"] == "info" and a["triggered"]],
        }
    except Exception as e:
        print(f"Warning: Could not evaluate alerts: {e}")
        alerts_data = {"critical": [], "warning": [], "info": []}

    # Build key metrics summary for glanceable display
    KEY_METRICS = [
        ("effr", "EFFR", "percent", "rate"),
        ("iorb", "IORB", "percent", "rate"),
        ("sofr", "SOFR", "percent", "rate"),
        ("effr_iorb_spread", "EFFR-IORB", "bps", "spread"),
        ("sofr_effr_spread", "SOFR-EFFR", "bps", "spread"),
        ("walcl_mil", "Fed Assets", "usd_millions", "balance"),
        ("rrp_usage_bil", "RRP Usage", "usd_billions", "balance"),
        ("reserves_bil", "Reserves", "usd_billions", "balance"),
    ]

    key_metrics_data = []
    for key, label, unit, category in KEY_METRICS:
        if key in latest:
            m = latest[key]
            key_metrics_data.append({
                "key": key,
                "label": label,
                "unit": unit,
                "category": category,
                "value": m.get("value"),
                "d1": m.get("d1"),
                "date": m.get("date", ""),
            })

    # Build final output
    output = {
        "generated_at": datetime.now().isoformat(),
        "date_range": {"start": start_str, "end": end_str},
        "config_version": config.version,
        "key_metrics": key_metrics_data,
        "charts": charts_data,
        "tables": tables_data,
        "alerts": alerts_data,
    }

    # Write JSON
    output_file = output_dir / "data.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Exported to {output_file}")
    print(f"  Charts: {len(charts_data)}")
    print(f"  Tables: {len(tables_data)}")
    print(f"  Alerts: {len(alerts_data['critical'])} critical, {len(alerts_data['warning'])} warning")

    return True


if __name__ == "__main__":
    output_dir = Path(__file__).parent.parent / "static"
    output_dir.mkdir(exist_ok=True)

    # Allow custom days via command line
    days = 365
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass

    success = export_dashboard_data(output_dir, days)
    sys.exit(0 if success else 1)
