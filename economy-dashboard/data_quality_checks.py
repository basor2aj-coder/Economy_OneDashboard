# Reusable data quality validation module for economic indicator dashboards
# Co-authored with CoCo
import pandas as pd
from datetime import datetime


def check_empty(df, indicator_name):
    """Check if a DataFrame is empty or has no usable rows."""
    if df is None or df.empty:
        return {"check": "empty_data", "indicator": indicator_name, "message": f"{indicator_name} data returned no rows."}
    return None


def check_stale(df, date_col, indicator_name, max_age_days=120):
    """Check if the most recent observation is older than max_age_days."""
    if df is None or df.empty:
        return None
    latest = pd.to_datetime(df[date_col]).max()
    threshold = pd.Timestamp.now() - pd.Timedelta(days=max_age_days)
    if latest < threshold:
        return {
            "check": "stale_data",
            "indicator": indicator_name,
            "message": f"{indicator_name} data may be stale (last: {latest.strftime('%b %Y')}).",
        }
    return None


def check_range(df, value_col, indicator_name, min_val, max_val):
    """Check if values fall outside an expected range."""
    if df is None or df.empty:
        return None
    actual_min = df[value_col].min()
    actual_max = df[value_col].max()
    if actual_max > max_val or actual_min < min_val:
        return {
            "check": "anomalous_value",
            "indicator": indicator_name,
            "message": f"{indicator_name} contains values outside expected range ({min_val}–{max_val}%).",
        }
    return None


def run_all_checks(gdp_df, unemp_df, fed_df, cpi_df):
    """Run all data quality checks and return a list of warning dicts.

    Each warning has keys: check, indicator, message.
    Returns an empty list if all checks pass.
    """
    warnings = []

    # Empty checks
    for df, name in [
        (gdp_df, "GDP"),
        (unemp_df, "Unemployment"),
        (fed_df, "Fed Funds"),
    ]:
        result = check_empty(df, name)
        if result:
            warnings.append(result)

    if cpi_df is None or cpi_df.empty or ("CPI_YOY" in cpi_df.columns and cpi_df["CPI_YOY"].dropna().empty):
        warnings.append({"check": "empty_data", "indicator": "CPI", "message": "CPI data returned no rows or insufficient history for YoY calculation."})

    # Staleness checks (120-day threshold)
    for df, date_col, name in [
        (gdp_df, "DATE", "GDP"),
        (unemp_df, "DATE", "Unemployment"),
        (fed_df, "DATE", "Fed Funds"),
    ]:
        result = check_stale(df, date_col, name)
        if result:
            warnings.append(result)

    # Range checks
    result = check_range(unemp_df, "UNEMPLOYMENT_RATE", "Unemployment", 0, 30)
    if result:
        warnings.append(result)

    result = check_range(fed_df, "FED_FUNDS_RATE", "Fed Funds", 0, 25)
    if result:
        warnings.append(result)

    if cpi_df is not None and "CPI_YOY" in cpi_df.columns and not cpi_df["CPI_YOY"].dropna().empty:
        if cpi_df["CPI_YOY"].abs().max() > 20:
            warnings.append({
                "check": "anomalous_value",
                "indicator": "CPI",
                "message": "CPI YoY inflation exceeds 20% — verify data integrity.",
            })

    return warnings


def log_warnings(warnings, session_log):
    """Append warnings (or a clean-run entry) to a session log list.

    Args:
        warnings: list of warning dicts from run_all_checks()
        session_log: list to append log entries to (typically st.session_state.dq_log)

    Returns:
        The updated session_log list.
    """
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if warnings:
        for w in warnings:
            session_log.append({
                "timestamp": run_timestamp,
                "check": w["check"],
                "indicator": w["indicator"],
                "message": w["message"],
            })
    else:
        session_log.append({
            "timestamp": run_timestamp,
            "check": "all_passed",
            "indicator": "—",
            "message": "All data quality checks passed.",
        })
    return session_log
