"""
Streamlit Dashboard for Fed Monitor.
Visualizes Fed monetary policy data, derived metrics, and alert status.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.config import get_config
from src.database import init_db
from src.metrics import calculate_all_metrics, get_latest_values

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Page config
st.set_page_config(
    page_title="Fed Monitor",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
init_db()

# Load config
config = get_config()


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
st.sidebar.title("Fed Monitor")
st.sidebar.markdown(f"*Config v{config.version}*")

# Date range selector
st.sidebar.subheader("Date Range")
range_options = {
    "30 Days": 30,
    "90 Days": 90,
    "1 Year": 365,
    "2 Years": 730,
    "Custom": None,
}
selected_range = st.sidebar.radio("Quick Select", list(range_options.keys()), index=2)

if selected_range == "Custom":
    end_date = st.sidebar.date_input("End Date", datetime.now())
    start_date = st.sidebar.date_input(
        "Start Date",
        datetime.now() - timedelta(days=365),
    )
else:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=range_options[selected_range])

start_str = start_date.strftime("%Y-%m-%d") if isinstance(start_date, datetime) else start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d") if isinstance(end_date, datetime) else end_date.strftime("%Y-%m-%d")

# Refresh button
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Timezone:** {config.timezone}")


# -----------------------------------------------------------------------------
# Data Loading (cached)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_data(start: str, end: str) -> pd.DataFrame:
    """Load and calculate all metrics."""
    return calculate_all_metrics(start, end)


@st.cache_data(ttl=300)
def load_latest() -> dict:
    """Load latest values for all metrics."""
    return get_latest_values()


# Load data
try:
    df = load_data(start_str, end_str)
    latest = load_latest()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Have you run the data fetch script? Try: `python scripts/fetch_data.py --backfill`")
    st.stop()

if df.empty:
    st.warning("No data available. Please run the data fetch script first.")
    st.code("cd ~/fed_monitor && python scripts/fetch_data.py --backfill")
    st.stop()


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def create_line_chart(
    df: pd.DataFrame,
    series_keys: list[str],
    title: str,
    y_label: str,
    height: int = 400,
    reference_line: float | None = None,
) -> go.Figure:
    """Create a Plotly line chart."""
    available = [k for k in series_keys if k in df.columns]
    if not available:
        return None

    fig = go.Figure()

    for key in available:
        series_def = config.get_series(key) or config.get_derived(key) or {}
        label = series_def.get("label", key)

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[key],
            mode="lines",
            name=label,
            hovertemplate=f"{label}: %{{y:.4f}}<extra></extra>",
        ))

    if reference_line is not None:
        fig.add_hline(y=reference_line, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        height=height,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_area_chart(
    df: pd.DataFrame,
    series_keys: list[str],
    title: str,
    y_label: str,
    height: int = 400,
) -> go.Figure:
    """Create a Plotly area chart."""
    available = [k for k in series_keys if k in df.columns]
    if not available:
        return None

    fig = go.Figure()

    for key in available:
        series_def = config.get_series(key) or config.get_derived(key) or {}
        label = series_def.get("label", key)

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[key],
            mode="lines",
            fill="tozeroy",
            name=label,
            hovertemplate=f"{label}: %{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        height=height,
        hovermode="x unified",
    )

    return fig


def create_bar_chart(
    df: pd.DataFrame,
    series_keys: list[str],
    title: str,
    y_label: str,
    height: int = 400,
) -> go.Figure:
    """Create a Plotly bar chart for stress indicators."""
    available = [k for k in series_keys if k in df.columns]
    if not available:
        return None

    fig = go.Figure()

    for key in available:
        series_def = config.get_series(key) or config.get_derived(key) or {}
        label = series_def.get("label", key)

        fig.add_trace(go.Bar(
            x=df.index,
            y=df[key],
            name=label,
            hovertemplate=f"{label}: %{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        height=height,
        hovermode="x unified",
        barmode="group",
    )

    return fig


def format_value(value: float | None, unit: str = "") -> str:
    """Format a value for display."""
    if value is None:
        return "N/A"
    if unit in ["percent", "bps"]:
        return f"{value:.2f}"
    if unit in ["usd_millions"]:
        return f"{value:,.0f}M"
    if unit in ["usd_billions"]:
        return f"{value:,.1f}B"
    if unit == "ratio":
        return f"{value:.3f}"
    return f"{value:,.2f}"


def format_change(value: float | None, is_pct: bool = False) -> str:
    """Format a change value with color indicator."""
    if value is None:
        return ""
    sign = "+" if value > 0 else ""
    if is_pct:
        return f"{sign}{value:.2f}%"
    return f"{sign}{value:,.2f}"


# -----------------------------------------------------------------------------
# Main Content
# -----------------------------------------------------------------------------
st.title("Fed Monetary Policy Monitor")
st.markdown(f"Data from **{start_str}** to **{end_str}**")

# -----------------------------------------------------------------------------
# Charts
# -----------------------------------------------------------------------------
for chart_def in config.panel_charts:
    title = chart_def["title"]
    series = chart_def["series"]
    chart_type = chart_def.get("chart_type", "line")
    y_label = chart_def.get("y_axis_label", "")
    height = chart_def.get("height", 400)
    ref_line = chart_def.get("reference_line")

    if chart_type == "line":
        fig = create_line_chart(df, series, title, y_label, height, ref_line)
    elif chart_type == "area":
        fig = create_area_chart(df, series, title, y_label, height)
    elif chart_type == "bar":
        fig = create_bar_chart(df, series, title, y_label, height)
    else:
        fig = create_line_chart(df, series, title, y_label, height, ref_line)

    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No data available for chart: {title}")

# -----------------------------------------------------------------------------
# Data Tables
# -----------------------------------------------------------------------------
st.markdown("---")
st.header("Data Tables")

for table_def in config.panel_tables:
    title = table_def["title"]
    series = table_def["series"]
    columns = table_def.get("show_columns", ["value", "d1", "d5"])

    st.subheader(title)

    table_data = []
    for key in series:
        if key not in latest:
            continue

        metrics = latest[key]
        series_def = config.get_series(key) or config.get_derived(key) or {}
        unit = series_def.get("unit", "")

        row = {
            "Metric": series_def.get("label", key),
            "Date": metrics.get("date", ""),
        }

        for col in columns:
            if col == "value":
                row["Value"] = format_value(metrics.get("value"), unit)
            elif col in metrics:
                is_pct = col.startswith("pct")
                row[col.upper()] = format_change(metrics.get(col), is_pct)

        table_data.append(row)

    if table_data:
        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(f"No data available for table: {title}")


# -----------------------------------------------------------------------------
# Alert Status Panel
# -----------------------------------------------------------------------------
st.markdown("---")
st.header("Alert Status")

# Evaluate current alert status
from src.alerts import evaluate_all_alerts

try:
    alert_results = evaluate_all_alerts()

    # Group by severity
    critical = [a for a in alert_results if a["severity"] == "critical" and a["triggered"]]
    warning = [a for a in alert_results if a["severity"] == "warning" and a["triggered"]]
    info_alerts = [a for a in alert_results if a["severity"] == "info" and a["triggered"]]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Critical", len(critical))
        for a in critical:
            st.error(f"**{a['key']}**: {a['note']}")

    with col2:
        st.metric("Warning", len(warning))
        for a in warning:
            st.warning(f"**{a['key']}**: {a['note']}")

    with col3:
        st.metric("Info", len(info_alerts))
        for a in info_alerts:
            st.info(f"**{a['key']}**: {a['note']}")

    if not (critical or warning or info_alerts):
        st.success("All metrics within normal thresholds.")

except Exception as e:
    st.error(f"Error evaluating alerts: {e}")


# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
    f"({config.timezone})*"
)
