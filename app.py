import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(
    page_title="AI Infrastructure vs Platform Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("AI Infrastructure vs Platform Relative Strength Dashboard")
st.caption("SOXX / Platform Basket and QQQ / Platform Basket")

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Settings")

period_label = st.sidebar.selectbox(
    "Analysis period",
    ["6 months", "1 year", "3 years", "5 years"],
    index=1
)

period_map = {
    "6 months": "6mo",
    "1 year": "1y",
    "3 years": "3y",
    "5 years": "5y"
}

period = period_map[period_label]

infra_tickers = st.sidebar.multiselect(
    "Infrastructure tickers",
    ["SOXX", "QQQ", "SMH", "NVDA", "AVGO", "AMD", "ARM", "INTC", "TSM"],
    default=["SOXX", "QQQ"]
)

platform_tickers = st.sidebar.multiselect(
    "Platform basket tickers",
    ["GOOGL", "MSFT", "AMZN", "META", "AAPL", "NFLX", "ORCL"],
    default=["GOOGL", "MSFT", "AMZN", "META"]
)

basket_method = st.sidebar.radio(
    "Platform basket method",
    ["Equal-weight index", "Simple price average"],
    index=0
)

show_raw_data = st.sidebar.checkbox("Show raw data table", value=False)

# -----------------------------
# Data loading
# -----------------------------
@st.cache_data(ttl=3600)
def load_prices(tickers, period):
    data = yf.download(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if data.empty:
        return pd.DataFrame()

    if "Adj Close" in data.columns:
        prices = data["Adj Close"].copy()
    else:
        prices = data["Close"].copy()

    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])

    prices = prices.dropna(how="all")
    return prices


all_tickers = sorted(list(set(infra_tickers + platform_tickers)))

if len(infra_tickers) == 0 or len(platform_tickers) == 0:
    st.warning("Please select at least one infrastructure ticker and one platform basket ticker.")
    st.stop()

prices = load_prices(all_tickers, period)

if prices.empty:
    st.error("No data was loaded. Please check ticker symbols or try again later.")
    st.stop()

missing = [t for t in all_tickers if t not in prices.columns]
if missing:
    st.warning(f"Some tickers were not loaded: {', '.join(missing)}")

available_infra = [t for t in infra_tickers if t in prices.columns]
available_platform = [t for t in platform_tickers if t in prices.columns]

if len(available_infra) == 0 or len(available_platform) == 0:
    st.error("Not enough ticker data was loaded to calculate the dashboard.")
    st.stop()

prices = prices[available_infra + available_platform].dropna()

# -----------------------------
# Platform basket calculation
# -----------------------------
platform_prices = prices[available_platform].copy()

if basket_method == "Equal-weight index":
    # Each platform stock starts at 100, then the average becomes the platform basket.
    platform_indexed = platform_prices / platform_prices.iloc[0] * 100
    platform_basket = platform_indexed.mean(axis=1)
else:
    # Simple average of stock prices. Easier, but less clean because high-priced stocks dominate.
    platform_basket = platform_prices.mean(axis=1)

result = pd.DataFrame(index=prices.index)
result["PLATFORM_BASKET"] = platform_basket

for ticker in available_infra:
    if basket_method == "Equal-weight index":
        ticker_index = prices[ticker] / prices[ticker].iloc[0] * 100
        ratio = ticker_index / result["PLATFORM_BASKET"]
    else:
        ratio = prices[ticker] / result["PLATFORM_BASKET"]

    result[f"{ticker}_PLATFORM_RATIO"] = ratio
    result[f"{ticker}_PLATFORM_IDX"] = ratio / ratio.iloc[0] * 100

# -----------------------------
# Helper functions
# -----------------------------
def pct_change_from_days(series, days):
    if len(series) <= days:
        return None
    return (series.iloc[-1] / series.iloc[-days - 1] - 1) * 100

def trend_text(value):
    if value is None:
        return "Not enough data"
    if value > 3:
        return "Strong relative strength"
    if value > 0:
        return "Mild relative strength"
    if value > -3:
        return "Mild relative weakness"
    return "Strong relative weakness"

def format_pct(value):
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"

# -----------------------------
# Summary cards
# -----------------------------
st.subheader("Current Relative Strength Summary")

cols = st.columns(len(available_infra))

for col, ticker in zip(cols, available_infra):
    idx_col = f"{ticker}_PLATFORM_IDX"
    current_value = result[idx_col].iloc[-1]
    one_month = pct_change_from_days(result[idx_col], 21)

    with col:
        st.metric(
            label=f"{ticker} vs Platform",
            value=f"{current_value:.2f}",
            delta=format_pct(one_month)
        )
        st.caption(f"1-month signal: {trend_text(one_month)}")

# -----------------------------
# Main chart
# -----------------------------
st.subheader("Relative Strength Chart")
st.caption("Index starts at 100 on the first available trading day.")

fig, ax = plt.subplots(figsize=(13, 6))

for ticker in available_infra:
    ax.plot(
        result.index,
        result[f"{ticker}_PLATFORM_IDX"],
        label=f"{ticker} / Platform Basket"
    )

ax.axhline(100, linestyle="--", linewidth=1)
ax.set_title("AI Infrastructure vs Platform Relative Strength")
ax.set_xlabel("Date")
ax.set_ylabel("Index, first day = 100")
ax.legend()
ax.grid(True, alpha=0.3)

st.pyplot(fig)

# -----------------------------
# Detailed table
# -----------------------------
st.subheader("Latest Readings")

summary_rows = []

for ticker in available_infra:
    idx_col = f"{ticker}_PLATFORM_IDX"
    series = result[idx_col]

    summary_rows.append({
        "Ticker": ticker,
        "Current Index": round(series.iloc[-1], 2),
        "1W Change": format_pct(pct_change_from_days(series, 5)),
        "1M Change": format_pct(pct_change_from_days(series, 21)),
        "3M Change": format_pct(pct_change_from_days(series, 63)),
        "Interpretation": trend_text(pct_change_from_days(series, 21))
    })

summary_df = pd.DataFrame(summary_rows)
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# -----------------------------
# Explanation
# -----------------------------
st.subheader("How to Read This Dashboard")

st.markdown("""
- If the line rises above 100, the selected infrastructure ticker is outperforming the platform basket.
- If the line falls below 100, the selected infrastructure ticker is underperforming the platform basket.
- The platform basket is currently built from the selected platform companies in the sidebar.
- The default platform basket is GOOGL, MSFT, AMZN, and META.
- Data is refreshed automatically, with a one-hour cache to avoid unnecessary repeated downloads.
""")

# -----------------------------
# Download
# -----------------------------
csv = result.to_csv(encoding="utf-8-sig")
st.download_button(
    label="Download calculated data as CSV",
    data=csv,
    file_name=f"ai_infra_platform_dashboard_{datetime.today().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

if show_raw_data:
    st.subheader("Raw Price Data")
    st.dataframe(prices.tail(100), use_container_width=True)
