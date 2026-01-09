#!/usr/bin/env python3
"""
Scheduler for Fed Monitor.
Runs scheduled tasks: data fetching, alert checking, daily summaries.

Usage:
    python scripts/run_scheduler.py  # Run the scheduler daemon
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import get_config
from src.database import init_db
from src.fred_client import fetch_all_series
from src.metrics import store_derived_metrics, get_latest_values
from src.alerts import check_alerts_with_state
from src.notifier import send_alert, send_daily_summary


def job_fetch_daily():
    """Fetch daily FRED data."""
    print(f"\n[{datetime.now()}] Running daily data fetch...")
    try:
        results = fetch_all_series()
        store_derived_metrics()
        total = sum(results.values())
        print(f"  Fetched {total} observations.")
    except Exception as e:
        print(f"  Error: {e}")


def job_fetch_weekly():
    """Fetch weekly H.4.1 data (runs on Thursday)."""
    print(f"\n[{datetime.now()}] Running weekly data fetch...")
    try:
        # Fetch with a bit more history to catch any delayed weekly data
        results = fetch_all_series(backfill_days=14)
        store_derived_metrics()
        total = sum(results.values())
        print(f"  Fetched {total} observations.")
    except Exception as e:
        print(f"  Error: {e}")


def job_check_alerts():
    """Check alerts and send notifications for new breaches."""
    print(f"\n[{datetime.now()}] Checking alerts...")
    try:
        new_breaches = check_alerts_with_state(
            notify_callback=send_alert,
            severity_filter=["critical"],  # Only notify on critical
        )
        if new_breaches:
            print(f"  {len(new_breaches)} new breach(es) notified.")
        else:
            print("  No new breaches.")
    except Exception as e:
        print(f"  Error: {e}")


def job_daily_summary():
    """Send daily summary of significant changes."""
    print(f"\n[{datetime.now()}] Sending daily summary...")
    try:
        config = get_config()
        latest = get_latest_values()

        # Find significant changes (|d1| > threshold)
        significant = []
        for key, metrics in latest.items():
            d1 = metrics.get("d1")
            if d1 is None:
                continue

            # Define significance thresholds by type
            series_def = config.get_series(key) or config.get_derived(key) or {}
            unit = series_def.get("unit", "")

            is_significant = False
            if unit in ["percent", "bps"]:
                is_significant = abs(d1) > 2  # >2bp change
            elif unit == "usd_billions":
                is_significant = abs(d1) > 10  # >$10B change
            elif unit == "usd_millions":
                is_significant = abs(d1) > 10000  # >$10B change
            elif unit == "ratio":
                is_significant = abs(d1) > 0.01  # >1% ratio change

            if is_significant:
                significant.append({
                    "key": key,
                    "value": metrics.get("value"),
                    "d1": d1,
                })

        if significant:
            send_daily_summary(significant)
            print(f"  Sent summary with {len(significant)} significant changes.")
        else:
            print("  No significant changes today.")

    except Exception as e:
        print(f"  Error: {e}")


def main():
    # Initialize database
    print("Initializing database...")
    init_db()

    config = get_config()
    schedule_config = config.schedule
    tz = config.timezone

    scheduler = BlockingScheduler(timezone=tz)

    # Parse cron schedules from config
    if "fetch_daily" in schedule_config:
        cron = schedule_config["fetch_daily"]["cron"]
        parts = cron.split()
        scheduler.add_job(
            job_fetch_daily,
            CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone=tz,
            ),
            id="fetch_daily",
            name="Daily FRED fetch",
        )
        print(f"Scheduled: fetch_daily at {cron} ({tz})")

    if "fetch_weekly" in schedule_config:
        cron = schedule_config["fetch_weekly"]["cron"]
        parts = cron.split()
        scheduler.add_job(
            job_fetch_weekly,
            CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone=tz,
            ),
            id="fetch_weekly",
            name="Weekly H.4.1 fetch",
        )
        print(f"Scheduled: fetch_weekly at {cron} ({tz})")

    if "check_alerts" in schedule_config:
        cron = schedule_config["check_alerts"]["cron"]
        parts = cron.split()
        # Handle */30 syntax for minutes
        minute = parts[0]
        hour = parts[1]

        scheduler.add_job(
            job_check_alerts,
            CronTrigger(
                minute=minute,
                hour=hour,
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone=tz,
            ),
            id="check_alerts",
            name="Alert checks",
        )
        print(f"Scheduled: check_alerts at {cron} ({tz})")

    if "daily_summary" in schedule_config:
        cron = schedule_config["daily_summary"]["cron"]
        parts = cron.split()
        scheduler.add_job(
            job_daily_summary,
            CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone=tz,
            ),
            id="daily_summary",
            name="Daily summary",
        )
        print(f"Scheduled: daily_summary at {cron} ({tz})")

    print(f"\nScheduler started. Timezone: {tz}")
    print("Press Ctrl+C to exit.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")


if __name__ == "__main__":
    main()
