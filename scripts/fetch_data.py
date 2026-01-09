#!/usr/bin/env python3
"""
CLI script to fetch data from FRED.
Usage:
    python scripts/fetch_data.py             # Fetch new data since last fetch
    python scripts/fetch_data.py --backfill  # Backfill 2 years of history
    python scripts/fetch_data.py --days 30   # Fetch last 30 days
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
from src.fred_client import fetch_all_series, backfill_all
from src.metrics import store_derived_metrics


def main():
    parser = argparse.ArgumentParser(description="Fetch FRED data for Fed Monitor")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Backfill 2 years of historical data",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Fetch data for the last N days",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=2,
        help="Years of history to backfill (default: 2)",
    )

    args = parser.parse_args()

    # Initialize database
    print("Initializing database...")
    init_db()

    # Fetch data
    if args.backfill:
        print(f"\nBackfilling {args.years} years of data...")
        results = backfill_all(years=args.years)
    elif args.days:
        print(f"\nFetching last {args.days} days of data...")
        results = fetch_all_series(backfill_days=args.days)
    else:
        print("\nFetching new data since last fetch...")
        results = fetch_all_series()

    # Calculate and store derived metrics
    print("\nCalculating derived metrics...")
    derived_count = store_derived_metrics()
    print(f"Stored {derived_count} derived metric values.")

    print("\nDone!")


if __name__ == "__main__":
    main()
