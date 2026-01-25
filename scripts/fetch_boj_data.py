#!/usr/bin/env python3
"""
CLI script to fetch data from Bank of Japan.
Usage:
    python scripts/fetch_boj_data.py             # Fetch new data since last fetch
    python scripts/fetch_boj_data.py --backfill  # Backfill 30 days of history
    python scripts/fetch_boj_data.py --days 10   # Fetch last 10 days
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
from src.boj_client import fetch_boj_series, backfill_boj


def main():
    parser = argparse.ArgumentParser(description="Fetch BOJ data for Fed Monitor")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Backfill historical data (default: 30 days)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Fetch data for the last N days",
    )

    args = parser.parse_args()

    # Initialize database (uses same schema as Fed Monitor)
    print("Initializing database...")
    init_db()

    # Fetch data
    if args.backfill:
        days = args.days or 30
        print(f"\nBackfilling {days} days of BOJ data...")
        results = backfill_boj(days=days)
    elif args.days:
        print(f"\nFetching last {args.days} days of BOJ data...")
        results = fetch_boj_series(backfill_days=args.days)
    else:
        print("\nFetching new BOJ data since last fetch...")
        results = fetch_boj_series()

    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    for key, count in sorted(results.items()):
        if count > 0:
            print(f"  {key}: {count} observations")

    print("\nDone!")


if __name__ == "__main__":
    main()
