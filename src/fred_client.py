"""
FRED API client for Fed Monitor.
Fetches economic data series from the Federal Reserve Economic Data API.
"""

import time
from datetime import datetime, timedelta

import pandas as pd
import requests

from .config import get_config
from .database import upsert_observations, log_fetch, get_latest_observation


class FredClient:
    """Client for fetching data from FRED API."""

    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.fred_base_url
        self.api_key = self.config.fred_api_key
        self.rate_limit = self.config.fred_rate_limit
        self._last_request_time = 0.0
        self._request_count = 0
        self._minute_start = time.time()

    def _throttle(self) -> None:
        """Enforce rate limiting."""
        now = time.time()

        # Reset counter every minute
        if now - self._minute_start >= 60:
            self._request_count = 0
            self._minute_start = now

        # Check if we've hit the limit
        if self._request_count >= self.rate_limit["requests_per_minute"]:
            sleep_time = 60 - (now - self._minute_start)
            if sleep_time > 0:
                print(f"Rate limit reached, sleeping {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            self._request_count = 0
            self._minute_start = time.time()

        self._request_count += 1

    def fetch_series(
        self,
        series_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """
        Fetch a single series from FRED.

        Args:
            series_id: FRED series ID (e.g., "EFFR")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with DatetimeIndex and 'value' column
        """
        self._throttle()

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
        }

        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date

        url = f"{self.base_url}/series/observations"

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            observations = data.get("observations", [])
            if not observations:
                return pd.DataFrame(columns=["value"])

            # Parse observations
            records = []
            for obs in observations:
                date = obs["date"]
                value_str = obs["value"]
                # FRED uses "." for missing values
                value = None if value_str == "." else float(value_str)
                records.append({"date": date, "value": value})

            df = pd.DataFrame(records)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df = df.dropna()  # Remove missing values

            return df

        except requests.RequestException as e:
            print(f"Error fetching {series_id}: {e}")
            raise

    def fetch_and_store(
        self,
        series_key: str,
        series_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """
        Fetch series from FRED and store in database.

        Args:
            series_key: Internal key for the series
            series_id: FRED series ID
            start_date: Start date
            end_date: End date

        Returns:
            Number of observations stored
        """
        try:
            df = self.fetch_series(series_id, start_date, end_date)

            if df.empty:
                log_fetch(series_key, "success", 0)
                return 0

            rows = upsert_observations(series_key, df)
            log_fetch(series_key, "success", rows)
            print(f"  {series_key}: {rows} observations stored")
            return rows

        except Exception as e:
            log_fetch(series_key, "error", 0, str(e))
            print(f"  {series_key}: ERROR - {e}")
            return 0


def fetch_all_series(
    start_date: str | None = None,
    end_date: str | None = None,
    backfill_days: int | None = None,
) -> dict[str, int]:
    """
    Fetch all configured series from FRED.

    Args:
        start_date: Start date (overrides backfill_days)
        end_date: End date (defaults to today)
        backfill_days: Number of days to backfill (default: fetch from latest)

    Returns:
        Dict of series_key -> rows fetched
    """
    config = get_config()
    client = FredClient()
    results = {}

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Fetching {len(config.series)} series from FRED...")

    for series_def in config.series:
        series_key = series_def["key"]
        series_id = series_def["series_id"]

        # Determine start date
        fetch_start = start_date
        if fetch_start is None:
            if backfill_days:
                fetch_start = (datetime.now() - timedelta(days=backfill_days)).strftime("%Y-%m-%d")
            else:
                # Fetch from last observation
                last_date, _ = get_latest_observation(series_key)
                if last_date:
                    # Start from the day after last observation
                    fetch_start = (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        rows = client.fetch_and_store(series_key, series_id, fetch_start, end_date)
        results[series_key] = rows

        # Small delay between requests for politeness
        time.sleep(0.1)

    total = sum(results.values())
    print(f"Done. Total: {total} observations across {len(results)} series.")
    return results


def backfill_all(years: int = 2) -> dict[str, int]:
    """
    Backfill all series with historical data.

    Args:
        years: Number of years of history to fetch

    Returns:
        Dict of series_key -> rows fetched
    """
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Backfilling {years} years of data ({start_date} to {end_date})...")
    return fetch_all_series(start_date=start_date, end_date=end_date)
