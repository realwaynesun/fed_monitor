"""
Config loader for Fed Monitor.
Parses YAML config and provides typed access to series, derived metrics, and alerts.
"""

import os
from pathlib import Path
from typing import Any

import yaml


class FedMonitorConfig:
    """Loads and provides access to fed_monitor_config.yaml."""

    def __init__(self, config_path: str | Path | None = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "fed_monitor_config.yaml"

        self.config_path = Path(config_path)
        self._raw = self._load_yaml()
        self._series_by_key = {s["key"]: s for s in self._raw.get("series", [])}
        self._derived_by_key = {d["key"]: d for d in self._raw.get("derived", [])}

    def _load_yaml(self) -> dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def version(self) -> str:
        return self._raw.get("version", "unknown")

    @property
    def timezone(self) -> str:
        return self._raw.get("timezone", "UTC")

    # -------------------------------------------------------------------------
    # Data Sources
    # -------------------------------------------------------------------------
    @property
    def fred_base_url(self) -> str:
        return self._raw["data_sources"]["fred"]["base_url"]

    @property
    def fred_api_key(self) -> str:
        env_var = self._raw["data_sources"]["fred"]["api_key_env"]
        key = os.environ.get(env_var, "")
        if not key:
            raise ValueError(f"Missing environment variable: {env_var}")
        return key

    @property
    def fred_rate_limit(self) -> dict:
        return self._raw["data_sources"]["fred"].get("rate_limit", {
            "requests_per_minute": 100,
            "retry_delay_seconds": 5
        })

    # -------------------------------------------------------------------------
    # Series
    # -------------------------------------------------------------------------
    @property
    def series(self) -> list[dict]:
        """All raw FRED series definitions."""
        return self._raw.get("series", [])

    def get_series(self, key: str) -> dict | None:
        """Get series definition by key."""
        return self._series_by_key.get(key)

    @property
    def series_keys(self) -> list[str]:
        """All series keys."""
        return list(self._series_by_key.keys())

    # -------------------------------------------------------------------------
    # Derived Metrics
    # -------------------------------------------------------------------------
    @property
    def derived(self) -> list[dict]:
        """All derived metric definitions."""
        return self._raw.get("derived", [])

    def get_derived(self, key: str) -> dict | None:
        """Get derived metric definition by key."""
        return self._derived_by_key.get(key)

    @property
    def derived_keys(self) -> list[str]:
        """All derived metric keys."""
        return list(self._derived_by_key.keys())

    # -------------------------------------------------------------------------
    # Metrics Calculations
    # -------------------------------------------------------------------------
    @property
    def metric_changes(self) -> list[dict]:
        """Period-over-period change definitions (d1, d5, etc.)."""
        return self._raw.get("metrics", {}).get("changes", [])

    @property
    def metric_rolling(self) -> list[dict]:
        """Rolling statistics definitions (ma5, ma20, etc.)."""
        return self._raw.get("metrics", {}).get("rolling", [])

    # -------------------------------------------------------------------------
    # Alerts
    # -------------------------------------------------------------------------
    @property
    def alerts(self) -> list[dict]:
        """All alert rule definitions."""
        return self._raw.get("alerts", [])

    def alerts_by_severity(self, severity: str) -> list[dict]:
        """Filter alerts by severity (info, warning, critical)."""
        return [a for a in self.alerts if a.get("severity") == severity]

    def alerts_by_category(self, category: str) -> list[dict]:
        """Filter alerts by category (rates, liquidity, stress, balance_sheet)."""
        return [a for a in self.alerts if a.get("category") == category]

    # -------------------------------------------------------------------------
    # Panel / Dashboard
    # -------------------------------------------------------------------------
    @property
    def panel_refresh_interval(self) -> int:
        """Dashboard refresh interval in seconds."""
        return self._raw.get("panel", {}).get("refresh_interval_seconds", 300)

    @property
    def panel_charts(self) -> list[dict]:
        """Chart definitions for dashboard."""
        return self._raw.get("panel", {}).get("charts", [])

    @property
    def panel_tables(self) -> list[dict]:
        """Table definitions for dashboard."""
        return self._raw.get("panel", {}).get("tables", [])

    # -------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------
    @property
    def telegram_enabled(self) -> bool:
        return self._raw.get("notifications", {}).get("telegram", {}).get("enabled", False)

    @property
    def telegram_bot_token(self) -> str:
        env_var = self._raw["notifications"]["telegram"]["bot_token_env"]
        return os.environ.get(env_var, "")

    @property
    def telegram_chat_id(self) -> str:
        env_var = self._raw["notifications"]["telegram"]["chat_id_env"]
        return os.environ.get(env_var, "")

    @property
    def telegram_parse_mode(self) -> str:
        return self._raw.get("notifications", {}).get("telegram", {}).get("parse_mode", "markdown")

    # -------------------------------------------------------------------------
    # Schedule
    # -------------------------------------------------------------------------
    @property
    def schedule(self) -> dict:
        """Scheduler configuration."""
        return self._raw.get("schedule", {})

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    @property
    def database_type(self) -> str:
        return self._raw.get("database", {}).get("type", "sqlite")

    @property
    def database_path(self) -> str:
        return self._raw.get("database", {}).get("path", "fed_monitor.db")


# Singleton instance for easy import
_config: FedMonitorConfig | None = None


def get_config(config_path: str | Path | None = None) -> FedMonitorConfig:
    """Get or create the config singleton."""
    global _config
    if _config is None or config_path is not None:
        _config = FedMonitorConfig(config_path)
    return _config
