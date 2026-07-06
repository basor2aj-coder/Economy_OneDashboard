# The Economy in One Dashboard

A real-time U.S. macroeconomic dashboard built with **Streamlit in Snowflake**, sourcing live federal data via the **Snowflake Marketplace** with zero ETL.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?logo=snowflake&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Tests](https://github.com/basor2aj-coder/Economy_OneDashboard/actions/workflows/tests.yml/badge.svg)

![Dashboard Screenshot](Dashboard_Screenshot.png)

## Overview

This dashboard visualizes four key U.S. economic indicators on a shared timeline, making it easy to see how they interact across economic cycles:

| Indicator | Source | Frequency |
|-----------|--------|-----------|
| Real GDP Growth (% change) | Bureau of Economic Analysis (BEA) | Quarterly |
| CPI Inflation (Year-over-Year %) | Bureau of Labor Statistics (BLS) | Monthly |
| Civilian Unemployment Rate | Bureau of Labor Statistics (BLS) | Monthly |
| Federal Funds Effective Rate | Federal Reserve | Monthly |

## Features

- **KPI cards** showing latest values with period-over-period deltas and contextual help tooltips
- **Combined Altair chart** with dual y-axes — GDP as bars (right axis), rates as lines (left axis)
- **NBER recession shading** — grey vertical bands marking the 2001, 2007–2009, and 2020 recessions
- **Detailed panel views** — individual bar, area, and line charts with hover tooltips for each indicator
- **Interactive controls** — date range slider, indicator toggles, manual cache refresh
- **Dark/light theme** — auto-switches based on system preference via `.streamlit/config.toml`
- **Error handling** — friendly message with marketplace link if the dataset isn't installed
- **No external dependencies** — uses only Altair and Pandas (pre-installed in the Streamlit runtime)

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Snowflake Marketplace                          │
│  └─ Snowflake Public Data (Free)                │
│     ├─ FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES  │
│     └─ BUREAU_OF_LABOR_STATISTICS_PRICE_...      │
└────────────────────┬────────────────────────────┘
                     │ SQL queries (no ETL)
                     ▼
┌─────────────────────────────────────────────────┐
│  Streamlit in Snowflake (Container Runtime)     │
│  └─ streamlit_app.py                            │
│     ├─ @st.cache_data loaders                   │
│     ├─ YoY inflation calculation                │
│     └─ Interactive Streamlit UI                 │
└─────────────────────────────────────────────────┘
```

**Key design decisions:**
- Queries live data directly from Snowflake's shared data layer — no pipelines, no staging tables
- Computes CPI year-over-year inflation on the fly from the raw index
- Uses `@st.cache_data` with 1-hour TTL to balance freshness and performance
- Altair for visualization (pre-installed, no EAI needed) with `resolve_scale(y="independent")` for dual axes
- Graceful degradation — try/except with user-friendly error if marketplace data is unavailable

## Prerequisites

1. A [Snowflake account](https://signup.snowflake.com/) (free trial works)
2. Install the **[Snowflake Public Data (Free)](https://app.snowflake.com/marketplace/listing/GZTSZ290BV255)** listing from the Marketplace
3. A warehouse (the app uses `COMPUTE_WH` by default — edit `snowflake.yml` to change)

## Running the App

### In Snowflake (recommended)

1. Open **Snowsight → Workspaces**
2. Upload or clone this project into a Workspace folder
3. Open `streamlit_app.py`
4. Click **Run**

### Locally (for development)

```bash
# Create a .streamlit/secrets.toml with your Snowflake credentials:
# [connections.snowflake]
# account = "your-account"
# user = "your-user"
# password = "your-password"
# warehouse = "COMPUTE_WH"
# role = "your-role"

pip install streamlit snowflake-connector-python
streamlit run streamlit_app.py
```

## Project Structure

```
economy-dashboard/
├── .streamlit/config.toml   # Streamlit theme configuration
├── .gitignore
├── pyproject.toml            # Python dependencies
├── snowflake.yml             # Snowflake app deployment config
├── streamlit_app.py          # Main dashboard application
└── README.md
```

## Skills Demonstrated

- **Cloud data engineering** — querying live government datasets via Snowflake Marketplace data sharing (zero ETL)
- **Full-stack data application** — SQL, Python data transformation, and interactive UI in one project
- **Data visualization** — dual-axis charts, recession band overlays, consistent color system, dark/light theme adaptation
- **Production patterns** — error handling, cache management, parameterized filtering, responsive layout
- **Domain knowledge** — joining datasets across different temporal granularities (quarterly GDP vs. monthly CPI/unemployment)

## Data Sources

All data comes from the [Snowflake Public Data (Free)](https://app.snowflake.com/marketplace/listing/GZTSZ290BV255) Marketplace listing, which aggregates 90+ public domain datasets including:

- **BEA** (Bureau of Economic Analysis) — GDP and national accounts
- **BLS** (Bureau of Labor Statistics) — Employment, prices, and inflation
- **Federal Reserve** — Interest rates, credit, and monetary policy data

## License

MIT
