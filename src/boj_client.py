"""
BOJ (Bank of Japan) data client for Fed Monitor.
Fetches economic data from Bank of Japan statistics.

Unlike FRED, BOJ does not provide a REST API. Data is fetched by:
1. Direct Excel file downloads (for daily data like TONA)
2. BOJ Time-Series Data Search CSV exports (for historical data)
"""

import io
import time
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd
import requests

from .config import get_config
from .database import upsert_observations, log_fetch, get_latest_observation


# =============================================================================
# Japanese Column Name Mappings
# =============================================================================

# TONA (Uncollateralized Overnight Call Rate) Excel columns
TONA_COLUMNS = {
    "日付": "date",
    "無担保コールO/N物レート": "tona",
    "無担保コールO/N物レート（速報）": "tona_preliminary",
    "無担保コールO/N物レート（確報）": "tona_final",
    "出来高": "volume",
    "出来高（税引後）": "volume_after_tax",
}

# Call Market Statistics columns
CALL_MARKET_COLUMNS = {
    "無担保コール": "unsecured_call",
    "有担保コール": "secured_call",
    "翌日物": "overnight",
    "ターム物": "term",
}

# Current Account Balance columns
CURRENT_ACCOUNT_COLUMNS = {
    "当座預金残高": "current_account_balance",
    "準備預金残高": "reserve_balance",
    "超過準備": "excess_reserves",
    "所要準備額": "required_reserves",
}

# BOJ Balance Sheet columns
BOJ_BS_COLUMNS = {
    "総資産": "total_assets",
    "国債": "jgb_holdings",
    "国庫短期証券": "tb_holdings",
    "ETF": "etf_holdings",
    "J-REIT": "jreit_holdings",
    "CP等": "cp_holdings",
    "社債": "corporate_bond_holdings",
    "貸出金": "loans",
    "当座預金": "current_deposits",
    "政府預金": "government_deposits",
    "発行銀行券": "banknotes_issued",
}


# =============================================================================
# BOJ Data URLs
# =============================================================================

class BojUrls:
    """URL patterns for BOJ data downloads."""

    # Base URLs
    BASE = "https://www.boj.or.jp"

    # TONA / Call Market Data (Daily)
    # Preliminary: released ~17:15 JST same day
    # Final: released ~10:00 JST next business day
    TONA_PRELIMINARY = "/statistics/market/short/mutan/d_release/mp/mp{date}.xlsx"
    TONA_FINAL = "/statistics/market/short/mutan/d_release/md/{year}/md{date}.xlsx"

    # Call Market Statistics (with volume)
    CALL_MARKET_PRELIMINARY = "/statistics/market/short/mutan/d_release/others/pcall.xlsx"
    CALL_MARKET_FINAL = "/statistics/market/short/mutan/d_release/others/fcall.xlsx"

    # Market Operations / Current Account Balance (Daily)
    # jd = final, jx = provisional, jp = projection
    MARKET_OPS_FINAL = "/statistics/boj/fm/juq/d_release/jd/{year}/jd{date}.xlsx"
    MARKET_OPS_PROVISIONAL = "/statistics/boj/fm/juq/d_release/jx/jx{date}.xlsx"
    MARKET_OPS_PROJECTION = "/statistics/boj/fm/juq/d_release/jp/jp{date}.xlsx"

    # Current Account Balances by Sector (Monthly)
    CURRENT_ACCOUNT_MONTHLY = "/statistics/boj/other/cabs/"

    # BOJ Time-Series Data Search
    STAT_SEARCH_BASE = "https://www.stat-search.boj.or.jp"

    @classmethod
    def tona_url(cls, dt: datetime, preliminary: bool = False) -> str:
        """Get TONA Excel download URL for a specific date."""
        date_str = dt.strftime("%Y%m%d")
        if preliminary:
            path = cls.TONA_PRELIMINARY.format(date=date_str)
        else:
            path = cls.TONA_FINAL.format(year=dt.year, date=date_str)
        return cls.BASE + path

    @classmethod
    def market_ops_url(
        cls,
        dt: datetime,
        data_type: Literal["final", "provisional", "projection"] = "final",
    ) -> str:
        """
        Get market operations Excel URL for a specific date.

        Args:
            dt: Date for the data
            data_type: "final" (jd), "provisional" (jx), or "projection" (jp)
        """
        date_str = dt.strftime("%Y%m%d")
        if data_type == "final":
            path = cls.MARKET_OPS_FINAL.format(year=dt.year, date=date_str)
        elif data_type == "provisional":
            path = cls.MARKET_OPS_PROVISIONAL.format(date=date_str)
        else:  # projection
            path = cls.MARKET_OPS_PROJECTION.format(date=date_str)
        return cls.BASE + path


# =============================================================================
# BOJ Client
# =============================================================================

class BojClient:
    """Client for fetching data from Bank of Japan."""

    def __init__(self):
        self.config = get_config()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; FedMonitor/1.0)",
            "Accept-Language": "ja,en;q=0.9",
        })

    def _download_excel(self, url: str, header: int | None = None) -> pd.DataFrame | None:
        """
        Download and parse an Excel file from BOJ.

        Args:
            url: Full URL to the Excel file
            header: Row to use as header (None = no header)

        Returns:
            DataFrame or None if download fails
        """
        try:
            response = self._session.get(url, timeout=30)
            response.raise_for_status()

            # Parse Excel
            df = pd.read_excel(
                io.BytesIO(response.content),
                engine="openpyxl",
                header=header,
            )
            return df

        except requests.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing Excel from {url}: {e}")
            return None

    def _normalize_columns(
        self,
        df: pd.DataFrame,
        column_map: dict[str, str],
    ) -> pd.DataFrame:
        """
        Normalize Japanese column names to English.

        Args:
            df: DataFrame with Japanese columns
            column_map: Mapping of Japanese -> English names

        Returns:
            DataFrame with normalized column names
        """
        # Try to match columns (partial match for flexibility)
        rename_map = {}
        for jp_col, en_col in column_map.items():
            for col in df.columns:
                if jp_col in str(col):
                    rename_map[col] = en_col
                    break

        if rename_map:
            df = df.rename(columns=rename_map)

        return df

    def fetch_tona(
        self,
        date: datetime | None = None,
        preliminary: bool = False,
    ) -> dict | None:
        """
        Fetch TONA (Uncollateralized Overnight Call Rate) for a specific date.

        Args:
            date: Date to fetch (defaults to yesterday for final, today for preliminary)
            preliminary: If True, fetch preliminary data (same day ~17:15)

        Returns:
            Dict with 'date', 'average', 'high', 'low' or None if failed
        """
        if date is None:
            if preliminary:
                date = datetime.now()
            else:
                # Final data is for previous business day
                date = datetime.now() - timedelta(days=1)

        url = BojUrls.tona_url(date, preliminary)
        df = self._download_excel(url, header=None)

        if df is None:
            return None

        # Parse the specific BOJ TONA Excel format:
        # Row 9 (0-indexed): Average (平均)
        # Row 10: Maximum (最高)
        # Row 11: Minimum (最低)
        # Column 2: Value in percent
        try:
            result = {
                "date": date.strftime("%Y-%m-%d"),
                "average": float(df.iloc[9, 2]),  # 平均 Average
                "high": float(df.iloc[10, 2]),    # 最高 Maximum
                "low": float(df.iloc[11, 2]),     # 最低 Minimum
            }
            return result
        except (IndexError, ValueError, TypeError) as e:
            print(f"Error parsing TONA data for {date}: {e}")
            return None

    def fetch_tona_range(
        self,
        start_date: datetime,
        end_date: datetime | None = None,
        data_type: Literal["final", "preliminary"] = "final",
    ) -> pd.DataFrame:
        """
        Fetch TONA data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to yesterday)
            data_type: "final" or "preliminary"

        Returns:
            DataFrame with columns: date, tona (average), tona_high, tona_low
        """
        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)

        all_data = []
        current = start_date

        while current <= end_date:
            # Skip weekends
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                result = self.fetch_tona(current, preliminary=(data_type == "preliminary"))
                if result is not None:
                    all_data.append({
                        "date": result["date"],
                        "tona": result["average"],
                        "tona_high": result["high"],
                        "tona_low": result["low"],
                    })
                    print(f"  Fetched TONA for {current.strftime('%Y-%m-%d')}: {result['average']:.3f}%")

                # Be polite to BOJ servers
                time.sleep(0.3)

            current += timedelta(days=1)

        if not all_data:
            return pd.DataFrame()

        return pd.DataFrame(all_data)

    def fetch_call_market_stats(self) -> pd.DataFrame:
        """
        Fetch latest call market statistics (with volume breakdown).

        Returns:
            DataFrame with call market statistics
        """
        url = BojUrls.BASE + BojUrls.CALL_MARKET_FINAL
        df = self._download_excel(url)

        if df is None:
            return pd.DataFrame()

        df = self._normalize_columns(df, CALL_MARKET_COLUMNS)
        return df

    def fetch_market_ops(
        self,
        date: datetime | None = None,
        data_type: Literal["final", "provisional", "projection"] = "final",
    ) -> dict | None:
        """
        Fetch BOJ market operations data including current account balances.

        This data includes:
        - 当座預金残高 (Current Account Balances)
        - 準備預金残高 (Reserve Balances)
        - 超過準備 (Excess Reserves)
        - マネタリーベース (Monetary Base)
        - Various market operation details

        Args:
            date: Date to fetch (defaults to previous business day for final)
            data_type: "final", "provisional", or "projection"

        Returns:
            Dict with parsed market operations data, or None if failed
        """
        if date is None:
            # Default to previous business day for final data
            date = datetime.now() - timedelta(days=1)
            # Skip weekends
            while date.weekday() >= 5:
                date -= timedelta(days=1)

        url = BojUrls.market_ops_url(date, data_type)
        df = self._download_excel(url, header=None)

        if df is None:
            return None

        # Parse the specific BOJ market operations Excel format
        # Data is in specific rows, column 7 for final results
        # Row indices (0-based):
        #   60: 当座預金増減 (Net change in current account)
        #   63: 当座預金残高 (Current account balance)
        #   65: 準備預金残高 (Reserve balance)
        #   69: 超過準備 (Excess reserves)
        #   71: 非準預先残高 (Non-reserve requirement balances)
        #   74: マネタリーベース (Monetary base)

        # Column index depends on data type
        # Final: column 7, Provisional: column 6, Projection: column 5
        col_map = {"final": 7, "provisional": 6, "projection": 5}
        col_idx = col_map.get(data_type, 7)

        try:
            def safe_float(row_idx: int) -> float | None:
                """Safely extract float value from DataFrame."""
                try:
                    val = df.iloc[row_idx, col_idx]
                    if pd.isna(val):
                        return None
                    return float(val)
                except (IndexError, ValueError, TypeError):
                    return None

            result = {
                "date": date.strftime("%Y-%m-%d"),
                "data_type": data_type,
                # All values in 100 million yen (億円)
                "current_account_change": safe_float(60),      # 当座預金増減
                "current_account_balance": safe_float(63),     # 当座預金残高
                "reserve_balance": safe_float(65),             # 準備預金残高
                "excess_reserves": safe_float(69),             # 超過準備
                "non_reserve_balance": safe_float(71),         # 非準預先残高
                "monetary_base": safe_float(74),               # マネタリーベース
            }

            # Validate we got at least the main balance
            if result["current_account_balance"] is None:
                print(f"Warning: Could not parse current account balance for {date}")
                return None

            return result

        except Exception as e:
            print(f"Error parsing market ops data for {date}: {e}")
            return None

    def fetch_market_ops_range(
        self,
        start_date: datetime,
        end_date: datetime | None = None,
    ) -> pd.DataFrame:
        """
        Fetch market operations data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to yesterday)

        Returns:
            DataFrame with market operations data
        """
        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)

        all_data = []
        current = start_date

        while current <= end_date:
            # Skip weekends
            if current.weekday() < 5:
                result = self.fetch_market_ops(current, data_type="final")
                if result is not None:
                    all_data.append(result)
                    cab = result["current_account_balance"]
                    print(f"  Fetched market ops for {current.strftime('%Y-%m-%d')}: "
                          f"当座預金 {cab:,.0f}億円")

                # Be polite to BOJ servers
                time.sleep(0.3)

            current += timedelta(days=1)

        if not all_data:
            return pd.DataFrame()

        return pd.DataFrame(all_data)

    def fetch_and_store_market_ops(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, int]:
        """
        Fetch market operations data and store in database.

        Stores multiple series:
        - current_account_balance (当座預金残高)
        - reserve_balance (準備預金残高)
        - excess_reserves (超過準備)
        - monetary_base (マネタリーベース)

        Args:
            start_date: Start date (defaults to last stored + 1)
            end_date: End date (defaults to yesterday)

        Returns:
            Dict of series_key -> rows stored
        """
        # Series to store
        series_keys = [
            ("current_account_balance", "current_account_balance"),
            ("reserve_balance", "reserve_balance"),
            ("excess_reserves", "excess_reserves"),
            ("monetary_base", "monetary_base"),
        ]

        # Determine start date from the main series
        if start_date is None:
            last_date, _ = get_latest_observation("current_account_balance")
            if last_date:
                start_date = datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
            else:
                start_date = datetime.now() - timedelta(days=30)

        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)
            while end_date.weekday() >= 5:
                end_date -= timedelta(days=1)

        if start_date > end_date:
            print("  market_ops: already up to date")
            return {k: 0 for k, _ in series_keys}

        try:
            df = self.fetch_market_ops_range(start_date, end_date)

            if df.empty:
                for key, _ in series_keys:
                    log_fetch(key, "success", 0)
                return {k: 0 for k, _ in series_keys}

            results = {}
            for db_key, col_name in series_keys:
                if col_name in df.columns:
                    df_store = df[["date", col_name]].copy()
                    df_store.columns = ["date", "value"]
                    df_store["date"] = pd.to_datetime(df_store["date"])
                    df_store = df_store.set_index("date")
                    df_store = df_store.dropna()

                    rows = upsert_observations(db_key, df_store)
                    log_fetch(db_key, "success", rows)
                    results[db_key] = rows
                else:
                    results[db_key] = 0

            total = sum(results.values())
            print(f"  market_ops: {total} total observations stored")
            return results

        except Exception as e:
            for key, _ in series_keys:
                log_fetch(key, "error", 0, str(e))
            print(f"  market_ops: ERROR - {e}")
            return {k: 0 for k, _ in series_keys}

    def fetch_and_store_tona(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Fetch TONA data and store in database.

        Args:
            start_date: Start date (defaults to last stored + 1)
            end_date: End date (defaults to yesterday)

        Returns:
            Number of observations stored
        """
        series_key = "tona"

        # Determine start date
        if start_date is None:
            last_date, _ = get_latest_observation(series_key)
            if last_date:
                start_date = datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
            else:
                # Default to 30 days ago for initial fetch
                start_date = datetime.now() - timedelta(days=30)

        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)

        if start_date > end_date:
            print(f"  {series_key}: already up to date")
            return 0

        try:
            # For TONA, we need to fetch day by day since BOJ provides daily files
            df = self.fetch_tona_range(start_date, end_date)

            if df.empty:
                log_fetch(series_key, "success", 0)
                return 0

            # Prepare for database storage
            df_store = df[["date", "tona"]].copy()
            df_store.columns = ["date", "value"]
            df_store["date"] = pd.to_datetime(df_store["date"])
            df_store = df_store.set_index("date")
            df_store = df_store.dropna()

            rows = upsert_observations(series_key, df_store)
            log_fetch(series_key, "success", rows)
            print(f"  {series_key}: {rows} observations stored")
            return rows

        except Exception as e:
            log_fetch(series_key, "error", 0, str(e))
            print(f"  {series_key}: ERROR - {e}")
            return 0


# =============================================================================
# Convenience Functions
# =============================================================================

def fetch_boj_series(
    start_date: str | None = None,
    end_date: str | None = None,
    backfill_days: int | None = None,
) -> dict[str, int]:
    """
    Fetch all configured BOJ series.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        backfill_days: Number of days to backfill

    Returns:
        Dict of series_key -> rows fetched
    """
    client = BojClient()
    results = {}

    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    if backfill_days and start_dt is None:
        start_dt = datetime.now() - timedelta(days=backfill_days)

    print("Fetching BOJ series...")

    # Fetch TONA (Uncollateralized Overnight Call Rate)
    print("\n[1/2] Fetching TONA...")
    rows = client.fetch_and_store_tona(start_dt, end_dt)
    results["tona"] = rows

    # Fetch Market Operations (Current Account Balances, etc.)
    print("\n[2/2] Fetching Market Operations...")
    market_ops_results = client.fetch_and_store_market_ops(start_dt, end_dt)
    results.update(market_ops_results)

    total = sum(results.values())
    print(f"\nDone. Total: {total} observations across {len(results)} series.")
    return results


def backfill_boj(days: int = 30) -> dict[str, int]:
    """
    Backfill BOJ series with historical data.

    Note: BOJ daily Excel files are only available for recent dates.
    For longer history, use BOJ Time-Series Data Search.

    Args:
        days: Number of days to backfill (default 30)

    Returns:
        Dict of series_key -> rows fetched
    """
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Backfilling {days} days of BOJ data ({start_date} to {end_date})...")
    return fetch_boj_series(start_date=start_date, end_date=end_date)
