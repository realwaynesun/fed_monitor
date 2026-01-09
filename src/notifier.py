"""
Notification system for Fed Monitor.
Sends alerts via Telegram.
"""

from datetime import datetime
from typing import Any

import requests

from .config import get_config


class TelegramNotifier:
    """Send notifications via Telegram Bot API."""

    def __init__(self):
        self.config = get_config()
        self.enabled = self.config.telegram_enabled
        self.bot_token = self.config.telegram_bot_token
        self.chat_id = self.config.telegram_chat_id
        self.parse_mode = self.config.telegram_parse_mode

    def _validate(self) -> bool:
        """Check if Telegram is properly configured."""
        if not self.enabled:
            return False
        if not self.bot_token or not self.chat_id:
            print("Warning: Telegram not configured (missing bot_token or chat_id)")
            return False
        return True

    def send_message(self, text: str, parse_mode: str | None = None) -> bool:
        """
        Send a message via Telegram.

        Args:
            text: Message text (supports markdown if parse_mode is set)
            parse_mode: Override parse mode (markdown, html, or None)

        Returns:
            True if sent successfully
        """
        if not self._validate():
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
        }

        mode = parse_mode or self.parse_mode
        if mode:
            payload["parse_mode"] = mode.capitalize()

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Telegram send failed: {e}")
            return False


def format_alert_message(alert_result: dict[str, Any]) -> str:
    """
    Format an alert result as a Telegram message.

    Args:
        alert_result: Result from evaluate_alert

    Returns:
        Formatted message string (markdown)
    """
    severity = alert_result.get("severity", "info")
    key = alert_result.get("key", "unknown")
    note = alert_result.get("note", "")
    value = alert_result.get("value")
    context = alert_result.get("context", {})

    # Severity emoji
    emoji_map = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "ℹ️",
    }
    emoji = emoji_map.get(severity, "📊")

    # Get series label from config
    config = get_config()
    series_def = config.get_series(key) or config.get_derived(key) or {}
    label = series_def.get("label", key)
    unit = series_def.get("unit", "")

    # Format value with unit
    if value is not None:
        if unit in ["percent", "bps"]:
            value_str = f"{value:.2f}"
        elif unit == "usd_millions":
            value_str = f"${value:,.0f}M"
        elif unit == "usd_billions":
            value_str = f"${value:,.1f}B"
        else:
            value_str = f"{value:,.2f}"
    else:
        value_str = "N/A"

    # Build message
    lines = [
        f"{emoji} *{severity.upper()}*: {label}",
        "",
        f"*Current:* {value_str}",
    ]

    # Add trend context
    d1 = context.get("d1")
    d5 = context.get("d5")
    if d1 is not None:
        sign = "+" if d1 > 0 else ""
        if unit in ["percent", "bps"]:
            lines.append(f"*1D Change:* {sign}{d1:.2f}")
        else:
            lines.append(f"*1D Change:* {sign}{d1:,.0f}")

    if d5 is not None:
        sign = "+" if d5 > 0 else ""
        if unit in ["percent", "bps"]:
            lines.append(f"*5D Change:* {sign}{d5:.2f}")
        else:
            lines.append(f"*5D Change:* {sign}{d5:,.0f}")

    # Add note
    if note:
        lines.append("")
        lines.append(f"_{note}_")

    # Timestamp
    lines.append("")
    lines.append(f"`{datetime.now().strftime('%Y-%m-%d %H:%M')} {config.timezone}`")

    return "\n".join(lines)


def format_daily_summary(significant_changes: list[dict]) -> str:
    """
    Format a daily summary message.

    Args:
        significant_changes: List of metrics with significant changes

    Returns:
        Formatted message string (markdown)
    """
    config = get_config()
    now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"📊 *Fed Monitor Daily Summary*",
        f"*Date:* {now}",
        "",
    ]

    if not significant_changes:
        lines.append("_No significant changes today._")
    else:
        lines.append("*Significant Changes:*")
        for item in significant_changes:
            key = item.get("key", "")
            series_def = config.get_series(key) or config.get_derived(key) or {}
            label = series_def.get("label", key)
            unit = series_def.get("unit", "")

            value = item.get("value")
            d1 = item.get("d1")

            if value is not None and d1 is not None:
                sign = "+" if d1 > 0 else ""
                if unit in ["percent", "bps"]:
                    lines.append(f"• {label}: {value:.2f} ({sign}{d1:.2f})")
                elif unit == "usd_millions":
                    lines.append(f"• {label}: ${value:,.0f}M ({sign}{d1:,.0f})")
                elif unit == "usd_billions":
                    lines.append(f"• {label}: ${value:,.1f}B ({sign}{d1:.1f})")
                else:
                    lines.append(f"• {label}: {value:,.2f} ({sign}{d1:,.2f})")

    lines.append("")
    lines.append(f"`{config.timezone}`")

    return "\n".join(lines)


def send_alert(alert_result: dict[str, Any]) -> bool:
    """
    Send an alert notification via Telegram.

    Args:
        alert_result: Result from evaluate_alert

    Returns:
        True if sent successfully
    """
    notifier = TelegramNotifier()
    message = format_alert_message(alert_result)
    return notifier.send_message(message)


def send_daily_summary(significant_changes: list[dict]) -> bool:
    """
    Send daily summary via Telegram.

    Args:
        significant_changes: List of metrics with significant changes

    Returns:
        True if sent successfully
    """
    notifier = TelegramNotifier()
    message = format_daily_summary(significant_changes)
    return notifier.send_message(message)


def test_telegram() -> bool:
    """
    Send a test message to verify Telegram configuration.

    Returns:
        True if successful
    """
    notifier = TelegramNotifier()
    return notifier.send_message(
        "✅ *Fed Monitor* - Telegram connection test successful!",
        parse_mode="markdown",
    )
