# Economy in One Dashboard — multi-indicator macroeconomic visualization
# Co-authored with CoCo
import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="The Economy in One Dashboard", layout="wide")
st.title("The Economy in One Dashboard")
st.caption("Key U.S. macroeconomic indicators from the Snowflake Public Data (Free) listing")

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))

# --- Data loaders ---

@st.cache_data(ttl=3600)
def load_gdp():
    """Real GDP percent change from preceding period (quarterly, seasonally adjusted)."""
    return conn.query("""
        SELECT DATE, VALUE AS GDP_PCT_CHANGE
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES
        WHERE VARIABLE = 'BEA_NIPA_1.1.1_A191RL_Q'
        ORDER BY DATE
    """)

@st.cache_data(ttl=3600)
def load_unemployment():
    """Civilian unemployment rate (monthly, seasonally adjusted)."""
    return conn.query("""
        SELECT DATE, VALUE AS UNEMPLOYMENT_RATE
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES
        WHERE VARIABLE = 'LNS14000000.M_SA'
        ORDER BY DATE
    """)

@st.cache_data(ttl=3600)
def load_fed_funds():
    """Federal funds effective rate (monthly)."""
    return conn.query("""
        SELECT DATE, VALUE AS FED_FUNDS_RATE
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES
        WHERE VARIABLE = 'H15_RIFSPFF_N.M'
        ORDER BY DATE
    """)

@st.cache_data(ttl=3600)
def load_cpi():
    """Consumer Price Index — All Items (monthly, seasonally adjusted).
    We compute year-over-year percent change as the inflation rate.
    """
    return conn.query("""
        SELECT DATE, VALUE AS CPI_INDEX
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.BUREAU_OF_LABOR_STATISTICS_PRICE_TIMESERIES
        WHERE VARIABLE = 'CPI:_All_items,_Seasonally_adjusted,_Monthly'
          AND GEO_ID = 'country/USA'
        ORDER BY DATE
    """)


# --- Load data ---
with st.spinner("Loading economic data..."):
    gdp_df = load_gdp()
    unemp_df = load_unemployment()
    fed_df = load_fed_funds()
    cpi_df = load_cpi()

# Compute CPI YoY inflation rate
cpi_df["DATE"] = pd.to_datetime(cpi_df["DATE"])
cpi_df = cpi_df.sort_values("DATE").reset_index(drop=True)
cpi_df["CPI_YOY"] = cpi_df["CPI_INDEX"].pct_change(periods=12) * 100

# Ensure date types
for df in [gdp_df, unemp_df, fed_df]:
    df["DATE"] = pd.to_datetime(df["DATE"])

# --- Sidebar ---
with st.sidebar:
    st.header("Controls")

    # Date range
    min_date = pd.Timestamp("2000-01-01")
    max_date = unemp_df["DATE"].max()
    date_range = st.slider(
        "Date range",
        min_value=min_date.to_pydatetime(),
        max_value=max_date.to_pydatetime(),
        value=(pd.Timestamp("2005-01-01").to_pydatetime(), max_date.to_pydatetime()),
        format="YYYY-MM",
    )
    start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])

    # Indicator toggles
    st.subheader("Indicators")
    show_gdp = st.checkbox("GDP Growth (quarterly)", value=True)
    show_cpi = st.checkbox("CPI Inflation (YoY %)", value=True)
    show_unemp = st.checkbox("Unemployment Rate", value=True)
    show_fed = st.checkbox("Federal Funds Rate", value=True)

    # Refresh button
    if st.button("Refresh Data"):
        load_gdp.clear()
        load_unemployment.clear()
        load_fed_funds.clear()
        load_cpi.clear()
        st.rerun()

# --- Filter data by selected range ---
gdp_filt = gdp_df[(gdp_df["DATE"] >= start_date) & (gdp_df["DATE"] <= end_date)]
unemp_filt = unemp_df[(unemp_df["DATE"] >= start_date) & (unemp_df["DATE"] <= end_date)]
fed_filt = fed_df[(fed_df["DATE"] >= start_date) & (fed_df["DATE"] <= end_date)]
cpi_filt = cpi_df[(cpi_df["DATE"] >= start_date) & (cpi_df["DATE"] <= end_date)].dropna(subset=["CPI_YOY"])

# --- KPI row ---
def get_latest_delta(df, value_col):
    """Return the latest value and the change from the prior observation."""
    if len(df) < 2:
        return (None, None)
    latest = df[value_col].iloc[-1]
    prior = df[value_col].iloc[-2]
    return (latest, latest - prior)

kpi_cols = st.columns(4)

with kpi_cols[0]:
    val, delta = get_latest_delta(gdp_filt, "GDP_PCT_CHANGE")
    st.metric(
        "GDP Growth (Q/Q %)",
        f"{val:.1f}%" if val is not None else "—",
        f"{delta:+.1f} pp" if delta is not None else None,
        border=True,
    )

with kpi_cols[1]:
    val, delta = get_latest_delta(cpi_filt, "CPI_YOY")
    st.metric(
        "Inflation (CPI YoY %)",
        f"{val:.1f}%" if val is not None else "—",
        f"{delta:+.1f} pp" if delta is not None else None,
        border=True,
    )

with kpi_cols[2]:
    val, delta = get_latest_delta(unemp_filt, "UNEMPLOYMENT_RATE")
    st.metric(
        "Unemployment Rate",
        f"{val:.1f}%" if val is not None else "—",
        f"{delta:+.1f} pp" if delta is not None else None,
        delta_color="inverse",
        border=True,
    )

with kpi_cols[3]:
    val, delta = get_latest_delta(fed_filt, "FED_FUNDS_RATE")
    st.metric(
        "Fed Funds Rate",
        f"{val:.2f}%" if val is not None else "—",
        f"{delta:+.2f} pp" if delta is not None else None,
        border=True,
    )

# --- Main time-series charts ---
st.divider()

# Build combined chart data
chart_data = pd.DataFrame({"DATE": pd.Series(dtype="datetime64[ns]")})

if show_gdp and not gdp_filt.empty:
    chart_data = chart_data.merge(
        gdp_filt[["DATE", "GDP_PCT_CHANGE"]], on="DATE", how="outer"
    )

if show_cpi and not cpi_filt.empty:
    chart_data = chart_data.merge(
        cpi_filt[["DATE", "CPI_YOY"]], on="DATE", how="outer"
    )

if show_unemp and not unemp_filt.empty:
    chart_data = chart_data.merge(
        unemp_filt[["DATE", "UNEMPLOYMENT_RATE"]], on="DATE", how="outer"
    )

if show_fed and not fed_filt.empty:
    chart_data = chart_data.merge(
        fed_filt[["DATE", "FED_FUNDS_RATE"]], on="DATE", how="outer"
    )

chart_data = chart_data.sort_values("DATE").set_index("DATE")

if not chart_data.empty and len(chart_data.columns) > 0:
    st.subheader("Economic Indicators Over Time")
    st.line_chart(chart_data, use_container_width=True)
else:
    st.info("Select at least one indicator to display.")

# --- Individual panel charts for detail ---
st.divider()
st.subheader("Detailed Views")

detail_cols = st.columns(2)

with detail_cols[0]:
    if show_gdp and not gdp_filt.empty:
        with st.container(border=True):
            st.markdown("**Real GDP Growth (% change from preceding quarter)**")
            st.bar_chart(gdp_filt.set_index("DATE")["GDP_PCT_CHANGE"], use_container_width=True)

    if show_unemp and not unemp_filt.empty:
        with st.container(border=True):
            st.markdown("**Civilian Unemployment Rate (%)**")
            st.area_chart(unemp_filt.set_index("DATE")["UNEMPLOYMENT_RATE"], use_container_width=True)

with detail_cols[1]:
    if show_cpi and not cpi_filt.empty:
        with st.container(border=True):
            st.markdown("**CPI Inflation — Year-over-Year (%)**")
            st.line_chart(cpi_filt.set_index("DATE")["CPI_YOY"], use_container_width=True)

    if show_fed and not fed_filt.empty:
        with st.container(border=True):
            st.markdown("**Federal Funds Effective Rate (%)**")
            st.area_chart(fed_filt.set_index("DATE")["FED_FUNDS_RATE"], use_container_width=True)

# --- Footer ---
st.divider()
st.caption(
    "Data source: Snowflake Public Data (Free) — BEA, BLS, Federal Reserve. "
    "All data has a ~3 month lag from real-time."
)
