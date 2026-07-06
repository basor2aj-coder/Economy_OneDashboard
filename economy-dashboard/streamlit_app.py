# Economy in One Dashboard — multi-indicator macroeconomic visualization
# Co-authored with CoCo
import os
from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt
from data_quality_checks import run_all_checks, log_warnings

st.set_page_config(page_title="The Economy in One Dashboard", page_icon="📊", layout="wide")
st.title("📊 The Economy in One Dashboard")
st.caption("Key U.S. macroeconomic indicators from the Snowflake Public Data (Free) listing")

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))

# --- Consistent color palette ---
COLORS = {
    "GDP": "#1f77b4",
    "CPI": "#d62728",
    "UNEMP": "#9e9e9e",
    "FED": "#2ca02c",
}

# NBER recession periods (start, end) for shading
RECESSIONS = pd.DataFrame([
    {"start": "2001-03-01", "end": "2001-11-01"},
    {"start": "2007-12-01", "end": "2009-06-01"},
    {"start": "2020-02-01", "end": "2020-04-01"},
])
RECESSIONS["start"] = pd.to_datetime(RECESSIONS["start"])
RECESSIONS["end"] = pd.to_datetime(RECESSIONS["end"])

# --- Data loaders ---

@st.cache_data(ttl=3600)
def load_gdp():
    return conn.query("""
        SELECT DATE, VALUE AS GDP_PCT_CHANGE
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES
        WHERE VARIABLE = 'BEA_NIPA_1.1.1_A191RL_Q'
        ORDER BY DATE
    """)

@st.cache_data(ttl=3600)
def load_unemployment():
    return conn.query("""
        SELECT DATE, VALUE AS UNEMPLOYMENT_RATE
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES
        WHERE VARIABLE = 'LNS14000000.M_SA'
        ORDER BY DATE
    """)

@st.cache_data(ttl=3600)
def load_fed_funds():
    return conn.query("""
        SELECT DATE, VALUE AS FED_FUNDS_RATE
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES
        WHERE VARIABLE = 'H15_RIFSPFF_N.M'
        ORDER BY DATE
    """)

@st.cache_data(ttl=3600)
def load_cpi():
    return conn.query("""
        SELECT DATE, VALUE AS CPI_INDEX
        FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.BUREAU_OF_LABOR_STATISTICS_PRICE_TIMESERIES
        WHERE VARIABLE = 'CPI:_All_items,_Seasonally_adjusted,_Monthly'
          AND GEO_ID = 'country/USA'
        ORDER BY DATE
    """)


# --- Load data ---
try:
    with st.spinner("Loading economic data..."):
        gdp_df = load_gdp()
        unemp_df = load_unemployment()
        fed_df = load_fed_funds()
        cpi_df = load_cpi()
        if "data_loaded_at" not in st.session_state:
            st.session_state.data_loaded_at = datetime.now()
except Exception as e:
    st.error(
        "**Failed to load economic data.** "
        "Make sure the [Snowflake Public Data (Free)](https://app.snowflake.com/marketplace/listing/GZTSZ290BV255) "
        "listing is installed in your Snowflake account and your role has access to the "
        "`SNOWFLAKE_PUBLIC_DATA_FREE` database."
    )
    st.exception(e)
    st.stop()

# Compute CPI YoY inflation rate
cpi_df["DATE"] = pd.to_datetime(cpi_df["DATE"])
cpi_df = cpi_df.sort_values("DATE").reset_index(drop=True)
cpi_df["CPI_YOY"] = cpi_df["CPI_INDEX"].pct_change(periods=12) * 100

for df in [gdp_df, unemp_df, fed_df]:
    df["DATE"] = pd.to_datetime(df["DATE"])

# --- Data quality validation ---
warnings = run_all_checks(gdp_df, unemp_df, fed_df, cpi_df)

# Log warnings to session state for tracking frequency
if "dq_log" not in st.session_state:
    st.session_state.dq_log = []
st.session_state.dq_log = log_warnings(warnings, st.session_state.dq_log)

if warnings:
    with st.expander(f"⚠️ Data quality ({len(warnings)} warning{'s' if len(warnings) > 1 else ''})", expanded=False):
        for w in warnings:
            st.warning(w["message"])

        # Export log as CSV
        st.divider()
        log_df = pd.DataFrame(st.session_state.dq_log)
        st.download_button(
            "📥 Export DQ log (CSV)",
            data=log_df.to_csv(index=False),
            file_name="data_quality_log.csv",
            mime="text/csv",
        )

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Controls")

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

    st.subheader("Indicators")
    show_gdp = st.checkbox("GDP Growth (quarterly)", value=True)
    show_cpi = st.checkbox("CPI Inflation (YoY %)", value=True)
    show_unemp = st.checkbox("Unemployment Rate", value=True)
    show_fed = st.checkbox("Federal Funds Rate", value=True)

    if st.button("🔄 Refresh Data"):
        load_gdp.clear()
        load_unemployment.clear()
        load_fed_funds.clear()
        load_cpi.clear()
        st.session_state.data_loaded_at = datetime.now()
        st.rerun()

    st.divider()
    loaded_at = st.session_state.get("data_loaded_at")
    if loaded_at:
        st.caption(f"Data loaded: {loaded_at.strftime('%b %d, %Y %I:%M %p')} UTC")

# --- Filter data by selected range ---
gdp_filt = gdp_df[(gdp_df["DATE"] >= start_date) & (gdp_df["DATE"] <= end_date)]
unemp_filt = unemp_df[(unemp_df["DATE"] >= start_date) & (unemp_df["DATE"] <= end_date)]
fed_filt = fed_df[(fed_df["DATE"] >= start_date) & (fed_df["DATE"] <= end_date)]
cpi_filt = cpi_df[(cpi_df["DATE"] >= start_date) & (cpi_df["DATE"] <= end_date)].dropna(subset=["CPI_YOY"])

# --- KPI row ---
def get_latest_delta(df, value_col):
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
        help="Real GDP percent change from preceding quarter, seasonally adjusted annual rate (BEA)",
    )

with kpi_cols[1]:
    val, delta = get_latest_delta(cpi_filt, "CPI_YOY")
    st.metric(
        "Inflation (CPI YoY %)",
        f"{val:.1f}%" if val is not None else "—",
        f"{delta:+.1f} pp" if delta is not None else None,
        border=True,
        help="Consumer Price Index year-over-year change, all items, seasonally adjusted (BLS)",
    )

with kpi_cols[2]:
    val, delta = get_latest_delta(unemp_filt, "UNEMPLOYMENT_RATE")
    st.metric(
        "Unemployment Rate",
        f"{val:.2f}%" if val is not None else "—",
        f"{delta:+.2f} pp" if delta is not None else None,
        delta_color="inverse",
        border=True,
        help="Civilian unemployment rate, seasonally adjusted (BLS)",
    )

with kpi_cols[3]:
    val, delta = get_latest_delta(fed_filt, "FED_FUNDS_RATE")
    st.metric(
        "Fed Funds Rate",
        f"{val:.2f}%" if val is not None else "—",
        f"{delta:+.2f} pp" if delta is not None else None,
        border=True,
        help="Federal funds effective rate, monthly average (Federal Reserve)",
    )

# --- Combined Altair chart with dual y-axes and recession bands ---
st.divider()

any_selected = show_gdp or show_cpi or show_unemp or show_fed

if any_selected:
    with st.container(border=True):
        st.subheader("Economic Indicators Over Time")

        # Filter recession bands to visible range
        rec_visible = RECESSIONS[
            (RECESSIONS["end"] >= start_date) & (RECESSIONS["start"] <= end_date)
        ].copy()
        rec_visible["start"] = rec_visible["start"].clip(lower=start_date)
        rec_visible["end"] = rec_visible["end"].clip(upper=end_date)

        # Recession shading layer
        recession_layer = alt.Chart(rec_visible).mark_rect(
            opacity=0.15, color="grey"
        ).encode(
            x="start:T",
            x2="end:T",
        )

        # Build line layers for rates (primary y-axis)
        rate_layers = []

        if show_cpi and not cpi_filt.empty:
            rate_layers.append(
                alt.Chart(cpi_filt).mark_line(
                    strokeWidth=2, color=COLORS["CPI"]
                ).encode(
                    x=alt.X("DATE:T", title=None),
                    y=alt.Y("CPI_YOY:Q", title="Rate (%)"),
                    tooltip=[
                        alt.Tooltip("DATE:T", title="Date", format="%b %Y"),
                        alt.Tooltip("CPI_YOY:Q", title="CPI Inflation (%)", format=".1f"),
                    ],
                )
            )

        if show_unemp and not unemp_filt.empty:
            rate_layers.append(
                alt.Chart(unemp_filt).mark_line(
                    strokeWidth=2, color=COLORS["UNEMP"], strokeDash=[4, 2]
                ).encode(
                    x=alt.X("DATE:T", title=None),
                    y=alt.Y("UNEMPLOYMENT_RATE:Q", title="Rate (%)"),
                    tooltip=[
                        alt.Tooltip("DATE:T", title="Date", format="%b %Y"),
                        alt.Tooltip("UNEMPLOYMENT_RATE:Q", title="Unemployment (%)", format=".1f"),
                    ],
                )
            )

        if show_fed and not fed_filt.empty:
            rate_layers.append(
                alt.Chart(fed_filt).mark_line(
                    strokeWidth=2, color=COLORS["FED"]
                ).encode(
                    x=alt.X("DATE:T", title=None),
                    y=alt.Y("FED_FUNDS_RATE:Q", title="Rate (%)"),
                    tooltip=[
                        alt.Tooltip("DATE:T", title="Date", format="%b %Y"),
                        alt.Tooltip("FED_FUNDS_RATE:Q", title="Fed Funds (%)", format=".2f"),
                    ],
                )
            )

        # GDP as bars on secondary y-axis (layered with resolve_scale)
        if show_gdp and not gdp_filt.empty:
            gdp_bars = alt.Chart(gdp_filt).mark_bar(
                opacity=0.4, color=COLORS["GDP"], width=15
            ).encode(
                x=alt.X("DATE:T", title=None),
                y=alt.Y("GDP_PCT_CHANGE:Q", title="GDP Growth (%)"),
                tooltip=[
                    alt.Tooltip("DATE:T", title="Date", format="%b %Y"),
                    alt.Tooltip("GDP_PCT_CHANGE:Q", title="GDP Growth (%)", format=".1f"),
                ],
            )
        else:
            gdp_bars = None

        # Compose the chart
        if rate_layers:
            rates_chart = alt.layer(*rate_layers)
        else:
            rates_chart = None

        if gdp_bars and rates_chart:
            combined = alt.layer(
                recession_layer, gdp_bars, rates_chart
            ).resolve_scale(
                y="independent"
            ).properties(
                height=450,
            )
        elif gdp_bars:
            combined = alt.layer(recession_layer, gdp_bars).properties(height=450)
        elif rates_chart:
            combined = alt.layer(recession_layer, rates_chart).properties(height=450)
        else:
            combined = recession_layer.properties(height=450)

        st.altair_chart(combined, use_container_width=True)

        # Legend (manual since we use independent scales)
        legend_items = []
        if show_gdp:
            legend_items.append(f"<span style='color:{COLORS['GDP']}'>■</span> GDP Growth (bars, right axis)")
        if show_cpi:
            legend_items.append(f"<span style='color:{COLORS['CPI']}'>━</span> CPI Inflation")
        if show_unemp:
            legend_items.append(f"<span style='color:{COLORS['UNEMP']}'>╌</span> Unemployment Rate")
        if show_fed:
            legend_items.append(f"<span style='color:{COLORS['FED']}'>━</span> Fed Funds Rate")
        legend_items.append("<span style='color:grey'>█</span> Recession")

        st.markdown(
            "&nbsp;&nbsp;&nbsp;".join(legend_items),
            unsafe_allow_html=True,
        )
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
            chart = alt.Chart(gdp_filt).mark_bar(color=COLORS["GDP"]).encode(
                x=alt.X("DATE:T", title=None),
                y=alt.Y("GDP_PCT_CHANGE:Q", title="%"),
                tooltip=[
                    alt.Tooltip("DATE:T", format="%b %Y"),
                    alt.Tooltip("GDP_PCT_CHANGE:Q", title="Growth %", format=".1f"),
                ],
            ).properties(height=220)
            st.altair_chart(chart, use_container_width=True)

    if show_unemp and not unemp_filt.empty:
        with st.container(border=True):
            st.markdown("**Civilian Unemployment Rate (%)**")
            chart = alt.Chart(unemp_filt).mark_area(
                color=COLORS["UNEMP"], opacity=0.3,
                line={"color": COLORS["UNEMP"], "strokeWidth": 1.5},
            ).encode(
                x=alt.X("DATE:T", title=None),
                y=alt.Y("UNEMPLOYMENT_RATE:Q", title="%", scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip("DATE:T", format="%b %Y"),
                    alt.Tooltip("UNEMPLOYMENT_RATE:Q", title="Rate %", format=".1f"),
                ],
            ).properties(height=220)
            st.altair_chart(chart, use_container_width=True)

with detail_cols[1]:
    if show_cpi and not cpi_filt.empty:
        with st.container(border=True):
            st.markdown("**CPI Inflation — Year-over-Year (%)**")
            chart = alt.Chart(cpi_filt).mark_line(
                color=COLORS["CPI"], strokeWidth=1.5
            ).encode(
                x=alt.X("DATE:T", title=None),
                y=alt.Y("CPI_YOY:Q", title="%"),
                tooltip=[
                    alt.Tooltip("DATE:T", format="%b %Y"),
                    alt.Tooltip("CPI_YOY:Q", title="Inflation %", format=".1f"),
                ],
            ).properties(height=220)
            st.altair_chart(chart, use_container_width=True)

    if show_fed and not fed_filt.empty:
        with st.container(border=True):
            st.markdown("**Federal Funds Effective Rate (%)**")
            chart = alt.Chart(fed_filt).mark_area(
                color=COLORS["FED"], opacity=0.2,
                line={"color": COLORS["FED"], "strokeWidth": 1.5},
            ).encode(
                x=alt.X("DATE:T", title=None),
                y=alt.Y("FED_FUNDS_RATE:Q", title="%"),
                tooltip=[
                    alt.Tooltip("DATE:T", format="%b %Y"),
                    alt.Tooltip("FED_FUNDS_RATE:Q", title="Rate %", format=".2f"),
                ],
            ).properties(height=220)
            st.altair_chart(chart, use_container_width=True)

# --- Footer ---
st.divider()
st.caption(
    "Data source: Snowflake Public Data (Free) — BEA, BLS, Federal Reserve. "
    "Grey bands = NBER recession periods. All data has a ~3 month lag from real-time."
)
