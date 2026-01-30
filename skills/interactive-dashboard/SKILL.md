---
name: interactive-dashboard
description: Create an interactive data dashboard using Streamlit to visualize advertising performance metrics.
---

# Interactive Dashboard Skill

This skill provides a standard procedure for creating a high-performance, interactive dashboard using Streamlit. It is designed to visualize large datasets (like ad-tech reports) with dynamic filtering and key performance indicators (KPIs).

## Prerequisites

-   **Python 3.9+**
-   **Streamlit** installed (`pip install streamlit`)
-   **Pandas** installed (`pip install pandas`)
-   **Plotly** (optional, for advanced charts)

## Implementation Steps

### 1. Project Structure

Create a `dashboard` directory or file (e.g., `dashboard_app.py`) in your project root.

### 2. Data Loading (Performance Optimized)

Use `@st.cache_data` to load data efficiently. Ensure data types are optimized (e.g., categories).

```python
import streamlit as st
import pandas as pd

@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    # Convert date columns to datetime
    if '日期' in df.columns:
        df['日期'] = pd.to_datetime(df['日期'], format='%Y%m%d', errors='coerce')
    return df

df = load_data('path/to/your/data.csv')
```

### 3. Sidebar Filters

Implement dynamic filters in the sidebar. Filters should cascade if possible (e.g., selecting a Supplier updates the available Sites).

```python
st.sidebar.header("Filter Options")

# Date Range
min_date = df['日期'].min()
max_date = df['日期'].max()
date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])

# Dimensional Filters
suppliers = st.sidebar.multiselect("Supplier", options=df['供應商名稱'].unique())
sites = st.sidebar.multiselect("Site", options=df['網站名稱'].unique())
antifraud = st.sidebar.multiselect("Antifraud Status", options=df['antifroud'].fillna('Clean').unique())

# Apply Filters
mask = (df['日期'] >= pd.to_datetime(date_range[0])) & (df['日期'] <= pd.to_datetime(date_range[1]))
if suppliers:
    mask &= df['供應商名稱'].isin(suppliers)
if sites:
    mask &= df['網站名稱'].isin(sites)
if antifraud:
    # Handle NaN for 'Clean'
    if 'Clean' in antifraud:
        mask &= (df['antifroud'].isin(antifraud) | df['antifroud'].isna())
    else:
        mask &= df['antifroud'].isin(antifraud)

filtered_df = df[mask]
```

### 4. KPI Cards

Display high-level metrics at the top using `st.metric`.

-   **Total Tracked Ads**: Sum of tracked ads.
-   **Viewability Rate**: Weighted average or recalculation based on sums.
-   **IVT Rate**: Percent of invalid traffic.

```python
col1, col2, col3 = st.columns(3)

total_ads = filtered_df['Total Tracked Ads (Viewability)'].sum()
viewable_ads = filtered_df['Viewable Impressions (Viewability)'].sum()
measured_ads = filtered_df['Measured Ads (Viewability)'].sum()

viewability_rate = (viewable_ads / measured_ads * 100) if measured_ads > 0 else 0

col1.metric("Total Tracked Ads", f"{total_ads:,}")
col2.metric("Viewability Rate", f"{viewability_rate:.2f}%")
```

### 5. Visualizations

Use `st.bar_chart`, `st.line_chart`, or `plotly` for detailed analysis.

-   **Trend Line**: Group by `Date` and plot metrics.
-   **Breakdown**: Pie chart of `Supplier` or `Site` share.

```python
st.subheader("Daily Trend")
daily_data = filtered_df.groupby('日期')['Total Tracked Ads (Viewability)'].sum()
st.line_chart(daily_data)
```

## Validation

Run the app locally to test:
`streamlit run dashboard_app.py`
