"""
Alert evaluation system for Fed Monitor.
Evaluates alert rules and tracks state transitions (OK <-> BREACH).
"""

import re
from typing import Any

from .config import get_config
from .database import (
    get_alert_state,
    update_alert_state,
    log_alert_transition,
)
from .metrics import calculate_all_metrics


def make_alert_id(alert_def: dict) -> str:
    """Generate a unique ID for an alert definition."""
    key = alert_def["key"]
    rule = alert_def["rule"]
    severity = alert_def["severity"]
    # Create a stable ID from key + rule hash
    return f"{key}:{severity}:{hash(rule) % 10000}"


def evaluate_rule(rule: str, context: dict[str, float], key: str = "") -> bool:
    """
    Safely evaluate an alert rule expression.

    Args:
        rule: Rule expression like "value > 5" or "abs(value) > 10"
        context: Dict of variable names to values (e.g., {"value": 4.5, "d1": -0.2})
        key: Metric key for better error messages

    Returns:
        True if rule is triggered, False otherwise
    """
    # Only allow safe builtins
    safe_builtins = {
        "abs": abs,
        "min": min,
        "max": max,
        "True": True,
        "False": False,
    }

    try:
        return bool(eval(rule, {"__builtins__": safe_builtins}, context))
    except NameError as e:
        # Missing variable - likely d1/d5 not available for this metric
        # This is expected for some weekly metrics, so don't warn loudly
        return False
    except Exception as e:
        print(f"Warning: Could not evaluate rule '{rule}' for {key}: {e}")
        return False


def get_alert_context(key: str, df=None) -> dict[str, float]:
    """
    Build context dict for evaluating an alert on a metric.

    Args:
        key: Metric key
        df: Pre-loaded metrics DataFrame (optional)

    Returns:
        Dict with 'value', 'd1', 'd5', 'd20', 'ma20', etc.
    """
    import pandas as pd

    if df is None:
        df = calculate_all_metrics()

    if df.empty or key not in df.columns:
        return {}

    series = df[key].dropna()
    if series.empty:
        return {}

    # Get the latest date with valid data for this key
    latest_date = series.index[-1]
    latest_value = series.iloc[-1]
    context = {"value": latest_value}

    # Get all metrics from the same date (or closest available)
    all_suffixes = ["d1", "d5", "d20", "pct1", "pct5", "ma5", "ma20", "std20", "zscore20"]

    for suffix in all_suffixes:
        col = f"{key}_{suffix}"
        if col not in df.columns:
            continue

        # Try to get value from the same date as the main value
        try:
            val = df.loc[latest_date, col]
            if pd.notna(val):
                context[suffix] = val
                continue
        except KeyError:
            pass

        # Fallback: get the most recent non-NaN value
        col_series = df[col].dropna()
        if not col_series.empty:
            context[suffix] = col_series.iloc[-1]

    return context


def evaluate_alert(alert_def: dict, df=None) -> dict[str, Any]:
    """
    Evaluate a single alert definition.

    Args:
        alert_def: Alert definition from config
        df: Pre-loaded metrics DataFrame (optional)

    Returns:
        Dict with evaluation results
    """
    key = alert_def["key"]
    rule = alert_def["rule"]
    severity = alert_def["severity"]
    note = alert_def.get("note", "")
    category = alert_def.get("category", "")
    alert_id = make_alert_id(alert_def)

    context = get_alert_context(key, df)

    result = {
        "alert_id": alert_id,
        "key": key,
        "rule": rule,
        "severity": severity,
        "note": note,
        "category": category,
        "triggered": False,
        "value": context.get("value"),
        "context": context,
        "state_changed": False,
        "previous_state": None,
    }

    if not context:
        result["error"] = "No data available"
        return result

    # Evaluate the rule
    result["triggered"] = evaluate_rule(rule, context, key)

    return result


def evaluate_all_alerts(df=None) -> list[dict[str, Any]]:
    """
    Evaluate all configured alerts.

    Returns:
        List of evaluation results for all alerts
    """
    config = get_config()

    if df is None:
        df = calculate_all_metrics()

    results = []
    for alert_def in config.alerts:
        result = evaluate_alert(alert_def, df)
        results.append(result)

    return results


def check_alerts_with_state(
    notify_callback=None,
    severity_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Check all alerts and track state transitions.
    Only triggers notifications on state change (OK -> BREACH).

    Args:
        notify_callback: Function to call when alert transitions to BREACH
                        Signature: callback(alert_result)
        severity_filter: Only process these severities (default: all)

    Returns:
        List of alerts that transitioned to BREACH
    """
    config = get_config()
    df = calculate_all_metrics()

    triggered_alerts = []

    for alert_def in config.alerts:
        severity = alert_def["severity"]

        # Filter by severity if specified
        if severity_filter and severity not in severity_filter:
            continue

        result = evaluate_alert(alert_def, df)
        alert_id = result["alert_id"]

        # Determine new state
        new_state = "breach" if result["triggered"] else "ok"

        # Update state and check for transition
        prev_state = update_alert_state(
            alert_id,
            new_state,
            result.get("value"),
        )

        if prev_state is not None:
            # State changed
            result["state_changed"] = True
            result["previous_state"] = prev_state

            # Log the transition
            log_alert_transition(
                alert_id=alert_id,
                severity=severity,
                state_from=prev_state,
                state_to=new_state,
                value=result.get("value"),
                note=result.get("note"),
            )

            # Notify on transition to BREACH
            if new_state == "breach":
                triggered_alerts.append(result)

                if notify_callback:
                    notify_callback(result)

    return triggered_alerts


def get_current_breaches() -> list[dict[str, Any]]:
    """
    Get all alerts currently in BREACH state.

    Returns:
        List of alert results for breached alerts
    """
    results = evaluate_all_alerts()
    return [r for r in results if r["triggered"]]


def get_breach_summary() -> dict[str, list[dict]]:
    """
    Get summary of current breaches grouped by severity.

    Returns:
        Dict with 'critical', 'warning', 'info' keys
    """
    breaches = get_current_breaches()

    summary = {
        "critical": [],
        "warning": [],
        "info": [],
    }

    for breach in breaches:
        severity = breach.get("severity", "info")
        if severity in summary:
            summary[severity].append(breach)

    return summary
