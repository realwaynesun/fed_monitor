"""
Metrics engine for Fed Monitor.
Calculates derived metrics, rolling statistics, and period-over-period changes.
"""

import re
from typing import Any

import numpy as np
import pandas as pd

from .config import get_config
from .database import (
    get_all_observations,
    get_derived_metric,
    upsert_derived_metrics,
)


def load_base_data(
    start_date: str | None = None,
    end_date: str | None = None,
    ffill: bool = True,
) -> pd.DataFrame:
    """
    Load all raw observations as a wide DataFrame.

    Args:
        start_date: Start date filter
        end_date: End date filter
        ffill: Forward-fill missing values (for weekly series alignment)

    Returns:
        DataFrame with DatetimeIndex, one column per series
    """
    config = get_config()
    series_keys = config.series_keys

    df = get_all_observations(series_keys, start_date, end_date)

    if df.empty:
        return df

    # Resample to daily and forward-fill for consistent panel
    if ffill:
        # asfreq creates daily index with NaN for missing days, then ffill propagates values
        df = df.asfreq("D").ffill()

    return df


def calculate_derived(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all derived metrics from raw data.

    Args:
        df: DataFrame with raw series as columns

    Returns:
        DataFrame with derived metric columns added
    """
    config = get_config()
    result = df.copy()

    for derived_def in config.derived:
        key = derived_def["key"]
        expr = derived_def["expr"]

        try:
            # Use pandas eval with the dataframe as local namespace
            # This safely evaluates expressions like "(effr - iorb) * 100"
            result[key] = result.eval(expr)
        except Exception as e:
            print(f"Warning: Could not calculate {key}: {e}")
            result[key] = np.nan

    return result


def calculate_changes(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Calculate period-over-period changes for a column.

    Args:
        df: DataFrame with the column
        column: Column name to calculate changes for

    Returns:
        DataFrame with change columns (d1, d5, d20, pct1, pct5)
    """
    config = get_config()
    result = pd.DataFrame(index=df.index)
    series = df[column]

    for change_def in config.metric_changes:
        name = change_def["name"]
        change_type = change_def["type"]
        periods = change_def["periods"]

        if change_type == "diff":
            result[f"{column}_{name}"] = series.diff(periods)
        elif change_type == "pct_change":
            result[f"{column}_{name}"] = series.pct_change(periods, fill_method=None) * 100

    return result


def calculate_rolling(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Calculate rolling statistics for a column.

    Args:
        df: DataFrame with the column
        column: Column name to calculate rolling stats for

    Returns:
        DataFrame with rolling columns (ma5, ma20, std20, zscore20)
    """
    config = get_config()
    result = pd.DataFrame(index=df.index)
    series = df[column]

    for rolling_def in config.metric_rolling:
        name = rolling_def["name"]
        rolling_type = rolling_def["type"]
        window = rolling_def["window"]

        if rolling_type == "rolling_mean":
            result[f"{column}_{name}"] = series.rolling(window).mean()
        elif rolling_type == "rolling_std":
            result[f"{column}_{name}"] = series.rolling(window).std()
        elif rolling_type == "zscore":
            ma = series.rolling(window).mean()
            std = series.rolling(window).std()
            result[f"{column}_{name}"] = (series - ma) / std.replace(0, np.nan)

    return result


def calculate_all_metrics(
    start_date: str | None = None,
    end_date: str | None = None,
    ffill: bool = True,
) -> pd.DataFrame:
    """
    Calculate all metrics: derived + changes + rolling for all series.

    Args:
        start_date: Start date filter
        end_date: End date filter
        ffill: Forward-fill missing values (set False for chart display)

    Returns:
        DataFrame with all metrics as columns
    """
    # Load raw data
    df = load_base_data(start_date, end_date, ffill=ffill)

    if df.empty:
        return df

    # Calculate derived metrics
    df = calculate_derived(df)

    # Calculate changes and rolling for each column
    all_columns = list(df.columns)
    changes_dfs = []
    rolling_dfs = []

    for col in all_columns:
        changes_dfs.append(calculate_changes(df, col))
        rolling_dfs.append(calculate_rolling(df, col))

    # Combine all
    for changes_df in changes_dfs:
        df = df.join(changes_df)
    for rolling_df in rolling_dfs:
        df = df.join(rolling_df)

    return df


def get_latest_values() -> dict[str, dict[str, Any]]:
    """
    Get the latest value and key metrics for all series.

    Returns:
        Dict of series_key -> {value, d1, d5, d20, ma20, ...}
    """
    df = calculate_all_metrics()

    if df.empty:
        return {}

    # Get the last row with valid data for each base series
    config = get_config()
    all_keys = config.series_keys + config.derived_keys

    result = {}
    for key in all_keys:
        if key not in df.columns:
            continue

        # Get last non-null value
        series = df[key].dropna()
        if series.empty:
            continue

        latest_date = series.index[-1]
        latest_row = df.loc[latest_date]

        metrics = {
            "value": latest_row.get(key),
            "date": latest_date.strftime("%Y-%m-%d"),
        }

        # Add changes and rolling if available (dynamically from config)
        suffixes = [c["name"] for c in config.metric_changes] + [r["name"] for r in config.metric_rolling]
        for suffix in suffixes:
            col = f"{key}_{suffix}"
            if col in df.columns:
                val = latest_row.get(col)
                if pd.notna(val):
                    metrics[suffix] = val

        result[key] = metrics

    return result


def get_metric_value(
    metric_key: str,
    metric_type: str = "value",
    date: str | None = None,
) -> float | None:
    """
    Get a specific metric value for alert evaluation.

    Args:
        metric_key: The series or derived metric key
        metric_type: "value", "d1", "d5", "d20", "ma20", etc.
        date: Specific date (defaults to latest)

    Returns:
        The metric value or None if not available
    """
    df = calculate_all_metrics()

    if df.empty:
        return None

    # Determine column name
    if metric_type == "value":
        col = metric_key
    else:
        col = f"{metric_key}_{metric_type}"

    if col not in df.columns:
        return None

    series = df[col].dropna()
    if series.empty:
        return None

    if date:
        try:
            return series.loc[date]
        except KeyError:
            return None

    return series.iloc[-1]


def store_derived_metrics() -> int:
    """
    Calculate and store all derived metrics in the database.

    Returns:
        Total number of rows stored
    """
    config = get_config()
    df = load_base_data()

    if df.empty:
        return 0

    df = calculate_derived(df)

    total = 0
    for key in config.derived_keys:
        if key in df.columns:
            metric_df = df[[key]].dropna()
            metric_df.columns = ["value"]
            rows = upsert_derived_metrics(key, metric_df)
            total += rows
            print(f"  {key}: {rows} values stored")

    return total
