#!/usr/bin/env python3
"""
CLI script to check alert thresholds.
Usage:
    python scripts/check_alerts.py              # Check all alerts
    python scripts/check_alerts.py --dry-run    # Check without notifications
    python scripts/check_alerts.py --critical   # Only check critical alerts
    python scripts/check_alerts.py --test-telegram  # Test Telegram connection
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

from src.database import init_db
from src.alerts import evaluate_all_alerts, check_alerts_with_state, get_breach_summary
from src.notifier import send_alert, test_telegram


def main():
    parser = argparse.ArgumentParser(description="Check Fed Monitor alerts")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check alerts without sending notifications",
    )
    parser.add_argument(
        "--critical",
        action="store_true",
        help="Only check critical severity alerts",
    )
    parser.add_argument(
        "--test-telegram",
        action="store_true",
        help="Send a test message to Telegram",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary of current breaches",
    )

    args = parser.parse_args()

    # Initialize database
    init_db()

    # Test Telegram
    if args.test_telegram:
        print("Sending test message to Telegram...")
        if test_telegram():
            print("Success! Check your Telegram.")
        else:
            print("Failed. Check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return

    # Show summary
    if args.summary:
        summary = get_breach_summary()
        print("\n=== Current Breach Summary ===")
        for severity in ["critical", "warning", "info"]:
            breaches = summary[severity]
            print(f"\n{severity.upper()} ({len(breaches)}):")
            for b in breaches:
                value = b.get("value")
                value_str = f"{value:.2f}" if value else "N/A"
                print(f"  - {b['key']}: {value_str}")
                print(f"    Rule: {b['rule']}")
                print(f"    {b['note']}")
        return

    # Determine severity filter
    severity_filter = ["critical"] if args.critical else None

    # Check alerts
    print("Checking alerts...")
    results = evaluate_all_alerts()

    triggered = [r for r in results if r["triggered"]]
    if severity_filter:
        triggered = [r for r in triggered if r["severity"] in severity_filter]

    print(f"\nTotal alerts: {len(results)}")
    print(f"Triggered: {len(triggered)}")

    if triggered:
        print("\n=== Triggered Alerts ===")
        for r in triggered:
            value = r.get("value")
            value_str = f"{value:.4f}" if value else "N/A"
            print(f"\n[{r['severity'].upper()}] {r['key']}")
            print(f"  Value: {value_str}")
            print(f"  Rule: {r['rule']}")
            print(f"  Note: {r['note']}")

    # Send notifications (unless dry-run)
    if not args.dry_run:
        print("\nChecking for state transitions and sending notifications...")

        def notify(alert_result):
            print(f"  Sending notification for: {alert_result['key']}")
            send_alert(alert_result)

        new_breaches = check_alerts_with_state(
            notify_callback=notify,
            severity_filter=severity_filter or ["critical"],  # Default to critical only
        )

        if new_breaches:
            print(f"\nSent {len(new_breaches)} notification(s).")
        else:
            print("\nNo new state transitions (no notifications sent).")
    else:
        print("\n(Dry run - no notifications sent)")


if __name__ == "__main__":
    main()
