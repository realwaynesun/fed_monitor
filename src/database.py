"""
Database module for Fed Monitor.
SQLite/Turso storage for observations, derived metrics, and alert logs.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import get_config, get_secret


def get_db_path() -> Path:
    """Get database path from config."""
    config = get_config()
    return Path(__file__).parent.parent / config.database_path


def _use_turso() -> bool:
    """Check if Turso cloud database is configured."""
    return bool(get_secret("TURSO_DATABASE_URL"))


def _get_turso_connection():
    """Get a Turso/libsql connection."""
    import libsql_experimental as libsql
    url = get_secret("TURSO_DATABASE_URL")
    token = get_secret("TURSO_AUTH_TOKEN")
    return libsql.connect(url, auth_token=token)


def init_db() -> None:
    """Initialize database schema."""
    if _use_turso():
        conn = _get_turso_connection()
    else:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)

    try:
        cursor = conn.cursor()

        # Raw FRED observations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_key TEXT NOT NULL,
                date TEXT NOT NULL,
                value REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(series_key, date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_key_date ON observations(series_key, date)")

        # Derived metrics (calculated values)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS derived_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_key TEXT NOT NULL,
                date TEXT NOT NULL,
                value REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(metric_key, date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_derived_key_date ON derived_metrics(metric_key, date)")

        # Alert state tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL DEFAULT 'ok',
                last_value REAL,
                last_transition_time TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Alert log (historical triggers)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                state_from TEXT NOT NULL,
                state_to TEXT NOT NULL,
                value REAL,
                note TEXT,
                triggered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_log_time ON alerts_log(triggered_at)")

        # Fetch log (for debugging)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fetch_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_key TEXT NOT NULL,
                status TEXT NOT NULL,
                rows_fetched INTEGER DEFAULT 0,
                error_message TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_connection():
    """Context manager for database connections."""
    if _use_turso():
        conn = _get_turso_connection()
    else:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# Observations
# -----------------------------------------------------------------------------
def upsert_observations(series_key: str, df: pd.DataFrame) -> int:
    """
    Insert or update observations for a series.
    df must have 'date' and 'value' columns (or DatetimeIndex).
    Returns number of rows upserted.
    """
    if df.empty:
        return 0

    # Normalize dataframe
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
        df.columns = ["date", "value"]

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["series_key"] = series_key

    with get_connection() as conn:
        cursor = conn.cursor()
        rows = df[["series_key", "date", "value"]].values.tolist()

        cursor.executemany("""
            INSERT INTO observations (series_key, date, value)
            VALUES (?, ?, ?)
            ON CONFLICT(series_key, date) DO UPDATE SET
                value = excluded.value,
                created_at = CURRENT_TIMESTAMP
        """, rows)

        conn.commit()
        return len(rows)


def get_observations(
    series_key: str,
    start_date: str | None = None,
    end_date: str | None = None
) -> pd.DataFrame:
    """
    Get observations for a series as a DataFrame.
    Returns DataFrame with DatetimeIndex and 'value' column.
    """
    query = "SELECT date, value FROM observations WHERE series_key = ?"
    params = [series_key]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date"

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        return pd.DataFrame(columns=["value"])

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


def get_all_observations(
    series_keys: list[str],
    start_date: str | None = None,
    end_date: str | None = None
) -> pd.DataFrame:
    """
    Get observations for multiple series as a wide DataFrame.
    Returns DataFrame with DatetimeIndex and one column per series.
    """
    dfs = {}
    for key in series_keys:
        df = get_observations(key, start_date, end_date)
        if not df.empty:
            dfs[key] = df["value"]

    if not dfs:
        return pd.DataFrame()

    result = pd.DataFrame(dfs)
    result = result.sort_index()
    return result


def get_latest_observation(series_key: str) -> tuple[str | None, float | None]:
    """Get the most recent observation date and value for a series."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, value FROM observations
            WHERE series_key = ?
            ORDER BY date DESC LIMIT 1
        """, (series_key,))
        row = cursor.fetchone()
        if row:
            return row["date"], row["value"]
        return None, None


# -----------------------------------------------------------------------------
# Derived Metrics
# -----------------------------------------------------------------------------
def upsert_derived_metrics(metric_key: str, df: pd.DataFrame) -> int:
    """Insert or update derived metric values."""
    if df.empty:
        return 0

    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
        df.columns = ["date", "value"]

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["metric_key"] = metric_key

    with get_connection() as conn:
        cursor = conn.cursor()
        rows = df[["metric_key", "date", "value"]].values.tolist()

        cursor.executemany("""
            INSERT INTO derived_metrics (metric_key, date, value)
            VALUES (?, ?, ?)
            ON CONFLICT(metric_key, date) DO UPDATE SET
                value = excluded.value,
                created_at = CURRENT_TIMESTAMP
        """, rows)

        conn.commit()
        return len(rows)


def get_derived_metric(
    metric_key: str,
    start_date: str | None = None,
    end_date: str | None = None
) -> pd.DataFrame:
    """Get derived metric values as a DataFrame."""
    query = "SELECT date, value FROM derived_metrics WHERE metric_key = ?"
    params = [metric_key]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date"

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        return pd.DataFrame(columns=["value"])

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


# -----------------------------------------------------------------------------
# Alert State
# -----------------------------------------------------------------------------
def get_alert_state(alert_id: str) -> dict | None:
    """Get current state for an alert."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_state WHERE alert_id = ?", (alert_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def update_alert_state(
    alert_id: str,
    state: str,
    value: float | None = None
) -> str | None:
    """
    Update alert state. Returns previous state if changed, None otherwise.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Get current state
        cursor.execute("SELECT state FROM alert_state WHERE alert_id = ?", (alert_id,))
        row = cursor.fetchone()
        prev_state = row["state"] if row else "ok"

        now = datetime.utcnow().isoformat()

        if row:
            cursor.execute("""
                UPDATE alert_state
                SET state = ?, last_value = ?, updated_at = ?,
                    last_transition_time = CASE WHEN state != ? THEN ? ELSE last_transition_time END
                WHERE alert_id = ?
            """, (state, value, now, state, now, alert_id))
        else:
            cursor.execute("""
                INSERT INTO alert_state (alert_id, state, last_value, last_transition_time, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (alert_id, state, value, now, now))

        conn.commit()

        return prev_state if prev_state != state else None


def log_alert_transition(
    alert_id: str,
    severity: str,
    state_from: str,
    state_to: str,
    value: float | None,
    note: str | None
) -> None:
    """Log an alert state transition."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts_log (alert_id, severity, state_from, state_to, value, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (alert_id, severity, state_from, state_to, value, note))
        conn.commit()


# -----------------------------------------------------------------------------
# Fetch Log
# -----------------------------------------------------------------------------
def log_fetch(series_key: str, status: str, rows_fetched: int = 0, error: str | None = None) -> None:
    """Log a data fetch attempt."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fetch_log (series_key, status, rows_fetched, error_message)
            VALUES (?, ?, ?, ?)
        """, (series_key, status, rows_fetched, error))
        conn.commit()


def get_fetch_history(series_key: str, limit: int = 10) -> list[dict]:
    """Get recent fetch history for a series."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM fetch_log
            WHERE series_key = ?
            ORDER BY fetched_at DESC
            LIMIT ?
        """, (series_key, limit))
        return [dict(row) for row in cursor.fetchall()]
