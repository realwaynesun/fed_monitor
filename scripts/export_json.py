#!/usr/bin/env python3
"""
Export dashboard data to static JSON for the static HTML dashboard.
Run this daily via cron to keep data fresh.

Usage:
    python scripts/export_json.py                    # Export Fed data (default)
    python scripts/export_json.py --monitor boj      # Export BOJ data
    python scripts/export_json.py --days 365         # Export last 365 days
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_monitor_config
from src.database import init_db
from src.metrics import calculate_all_metrics, get_latest_values
from src.alerts import evaluate_all_alerts


# Key metrics for glanceable display by monitor type
KEY_METRICS_FED = [
    ("effr", "EFFR", "percent", "rate"),
    ("iorb", "IORB", "percent", "rate"),
    ("sofr", "SOFR", "percent", "rate"),
    ("spread_effr_iorb", "EFFR-IORB", "bps", "spread"),
    ("spread_sofr_effr", "SOFR-EFFR", "bps", "spread"),
    ("walcl_mil", "Fed Assets", "usd_millions", "balance"),
    ("rrp_usage_bil", "RRP Usage", "usd_billions", "balance"),
    ("reserves_mil", "Reserves", "usd_millions", "balance"),
]

KEY_METRICS_BOJ = [
    ("jgb_10y", "10Y JGB", "percent", "rate"),
    ("usdjpy", "USD/JPY", "jpy_per_usd", "rate"),
    ("boj_total_assets", "BOJ Assets", "jpy_100millions", "balance"),
]


def export_dashboard_data(
    output_dir: Path,
    days: int = 365,
    monitor: Literal["fed", "boj"] = "fed",
):
    """Export all dashboard data to JSON files."""

    init_db()
    config = get_monitor_config(monitor)

    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"Exporting {monitor.upper()} data from {start_str} to {end_str}...")

    # Calculate metrics (no ffill for charts)
    df = calculate_all_metrics(start_str, end_str, ffill=False, monitor=monitor)

    if df.empty:
        print(f"Warning: No data available for {monitor.upper()} Monitor")
        # Create empty but valid output
        output = {
            "generated_at": datetime.now().isoformat(),
            "date_range": {"start": start_str, "end": end_str},
            "config_version": config.version,
            "monitor": monitor,
            "key_metrics": [],
            "charts": [],
            "tables": [],
            "alerts": {"critical": [], "warning": [], "info": []},
        }
        output_file = output_dir / f"{monitor}-data.json"
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Created empty {output_file}")
        return True

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
    latest = get_latest_values(monitor=monitor)
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
        alert_results = evaluate_all_alerts(monitor=monitor)
        alerts_data = {
            "critical": [a for a in alert_results if a["severity"] == "critical" and a["triggered"]],
            "warning": [a for a in alert_results if a["severity"] == "warning" and a["triggered"]],
            "info": [a for a in alert_results if a["severity"] == "info" and a["triggered"]],
        }
    except Exception as e:
        print(f"Warning: Could not evaluate alerts: {e}")
        alerts_data = {"critical": [], "warning": [], "info": []}

    # Build key metrics summary for glanceable display
    key_metrics_def = KEY_METRICS_FED if monitor == "fed" else KEY_METRICS_BOJ

    key_metrics_data = []
    for key, label, unit, category in key_metrics_def:
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
        "monitor": monitor,
        "key_metrics": key_metrics_data,
        "charts": charts_data,
        "tables": tables_data,
        "alerts": alerts_data,
    }

    # Write JSON to monitor-specific file
    output_file = output_dir / f"{monitor}-data.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Exported to {output_file}")
    print(f"  Charts: {len(charts_data)}")
    print(f"  Tables: {len(tables_data)}")
    print(f"  Alerts: {len(alerts_data['critical'])} critical, {len(alerts_data['warning'])} warning")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export dashboard data to JSON")
    parser.add_argument(
        "--monitor",
        type=str,
        choices=["fed", "boj"],
        default="fed",
        help="Which monitor to export (default: fed)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days of data to export (default: 365)",
    )

    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "static"
    output_dir.mkdir(exist_ok=True)

    success = export_dashboard_data(output_dir, args.days, args.monitor)
    sys.exit(0 if success else 1)
