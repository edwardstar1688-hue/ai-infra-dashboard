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
st.caption("SOXX / Platform Basket and QQQ / Platform Basket with Moving Averages and Deviation Rates")

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

chart_mode = st.sidebar.radio(
    "Chart mode",
    ["Relative strength + moving averages", "Deviation from moving averages"],
    index=0
)

show_raw_data = st.sidebar.checkbox("Show raw data table", value=False)

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

platform_prices = prices[available_platform].copy()

if basket_method == "Equal-weight index":
    platform_indexed = platform_prices / platform_prices.iloc[0] * 100
    platform_basket = platform_indexed.mean(axis=1)
else:
    platform_basket = platform_prices.mean(axis=1)

result = pd.DataFrame(index=prices.index)
result["PLATFORM_BASKET"] = platform_basket

for ticker in available_infra:
    if basket_method == "Equal-weight index":
        ticker_index = prices[ticker] / prices[ticker].iloc[0] * 100
        ratio = ticker_index / result["PLATFORM_BASKET"]
    else:
        ratio = prices[ticker] / result["PLATFORM_BASKET"]

    rs_idx = ratio / ratio.iloc[0] * 100
    ma21 = rs_idx.rolling(window=21).mean()
    ma60 = rs_idx.rolling(window=60).mean()
    dev21 = (rs_idx / ma21 - 1) * 100
    dev60 = (rs_idx / ma60 - 1) * 100

    result[f"{ticker}_PLATFORM_RATIO"] = ratio
    result[f"{ticker}_PLATFORM_IDX"] = rs_idx
    result[f"{ticker}_MA21"] = ma21
    result[f"{ticker}_MA60"] = ma60
    result[f"{ticker}_DEV21_PCT"] = dev21
    result[f"{ticker}_DEV60_PCT"] = dev60

def format_pct(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:+.2f}%"

def format_num(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}"

def dev_signal(value):
    if value is None or pd.isna(value):
        return "Not enough data"
    if value >= 10:
        return "Above +10% reference"
    if value > 0:
        return "Above moving average"
    if value > -10:
        return "Below moving average"
    return "Below -10% reference"

st.subheader("Current Relative Strength Summary")

cols = st.columns(len(available_infra))

for col, ticker in zip(cols, available_infra):
    idx_col = f"{ticker}_PLATFORM_IDX"
    dev21_col = f"{ticker}_DEV21_PCT"
    current_value = result[idx_col].dropna().iloc[-1]
    current_dev21 = result[dev21_col].dropna().iloc[-1] if not result[dev21_col].dropna().empty else None

    with col:
        st.metric(
            label=f"{ticker} vs Platform",
            value=f"{current_value:.2f}",
            delta=format_pct(current_dev21)
        )
        st.caption(f"21-day MA deviation: {dev_signal(current_dev21)}")

if chart_mode == "Relative strength + moving averages":
    st.subheader("Relative Strength Index with 21-Day and 60-Day Moving Averages")
    st.caption("Relative strength index starts at 100 on the first available trading day.")

    for ticker in available_infra:
        fig, ax = plt.subplots(figsize=(13, 6))

        ax.plot(
            result.index,
            result[f"{ticker}_PLATFORM_IDX"],
            label=f"{ticker} / Platform Relative Strength Index",
            linewidth=1.8
        )
        ax.plot(
            result.index,
            result[f"{ticker}_MA21"],
            label="21-Day Moving Average",
            linestyle="--",
            linewidth=1.4
        )
        ax.plot(
            result.index,
            result[f"{ticker}_MA60"],
            label="60-Day Moving Average",
            linestyle=":",
            linewidth=1.6
        )

        ax.axhline(100, linestyle="-", linewidth=0.8)
        ax.set_title(f"{ticker} / Platform Relative Strength with Moving Averages")
        ax.set_xlabel("Date")
        ax.set_ylabel("Index, first day = 100")
        ax.legend()
        ax.grid(True, alpha=0.3)

        st.pyplot(fig)

if chart_mode == "Deviation from moving averages":
    st.subheader("Deviation Rate from Moving Averages")
    st.caption("Deviation formula: (Relative Strength Index / Moving Average - 1) × 100")

    for ticker in available_infra:
        fig, ax = plt.subplots(figsize=(13, 6))

        ax.plot(
            result.index,
            result[f"{ticker}_DEV21_PCT"],
            label="Deviation from 21-Day Moving Average (%)",
            linewidth=1.7
        )
        ax.plot(
            result.index,
            result[f"{ticker}_DEV60_PCT"],
            label="Deviation from 60-Day Moving Average (%)",
            linewidth=1.7
        )

        ax.axhline(10, linestyle="--", linewidth=1.2, label="+10% Reference Line")
        ax.axhline(-10, linestyle="--", linewidth=1.2, label="-10% Reference Line")
        ax.axhline(0, linestyle="-", linewidth=0.8)

        ax.set_title(f"{ticker} / Platform Deviation from Moving Averages")
        ax.set_xlabel("Date")
        ax.set_ylabel("Deviation Rate (%)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        st.pyplot(fig)

st.subheader("Latest Readings")

summary_rows = []

for ticker in available_infra:
    idx_col = f"{ticker}_PLATFORM_IDX"
    ma21_col = f"{ticker}_MA21"
    ma60_col = f"{ticker}_MA60"
    dev21_col = f"{ticker}_DEV21_PCT"
    dev60_col = f"{ticker}_DEV60_PCT"

    latest_dev21 = result[dev21_col].dropna().iloc[-1] if not result[dev21_col].dropna().empty else None
    latest_dev60 = result[dev60_col].dropna().iloc[-1] if not result[dev60_col].dropna().empty else None

    summary_rows.append({
        "Ticker": ticker,
        "Relative Strength Index": format_num(result[idx_col].dropna().iloc[-1]),
        "21-Day MA": format_num(result[ma21_col].dropna().iloc[-1]) if not result[ma21_col].dropna().empty else "N/A",
        "60-Day MA": format_num(result[ma60_col].dropna().iloc[-1]) if not result[ma60_col].dropna().empty else "N/A",
        "Deviation vs 21-Day MA": format_pct(latest_dev21),
        "Deviation vs 60-Day MA": format_pct(latest_dev60),
        "Signal vs 21-Day MA": dev_signal(latest_dev21),
        "Signal vs 60-Day MA": dev_signal(latest_dev60),
    })

summary_df = pd.DataFrame(summary_rows)
st.dataframe(summary_df, use_container_width=True, hide_index=True)

st.subheader("How to Read This Dashboard")

st.markdown("""
### Relative Strength Index
- The relative strength index compares each selected infrastructure ticker against the selected platform basket.
- If the line rises, the infrastructure ticker is outperforming the platform basket.
- If the line falls, the infrastructure ticker is underperforming the platform basket.

### Moving Averages
- The 21-day moving average shows the shorter-term trend.
- The 60-day moving average shows the medium-term trend.

### Deviation Rate
- Formula: `(Relative Strength Index / Moving Average - 1) × 100`
- A positive deviation means the relative strength index is above its moving average.
- A negative deviation means the relative strength index is below its moving average.
- The +10% and -10% lines are reference levels for unusually large deviations.
""")

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
