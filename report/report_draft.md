# HW2 Report Draft

## Project Title

MSTR Premium to NAV Monitor

## 1. Selected Indicator

This project focuses on **Premium to NAV** for Strategy (ticker: MSTR), one of the most visible Bitcoin treasury companies.

The indicator is defined using a simple Bitcoin-backed NAV proxy. First, I estimate the Bitcoin-backed net asset value per share as:

```text
btc_nav_per_share = (btc_holdings × btc_price) / shares_outstanding
```

Then I compute:

```text
mnav = stock_price / btc_nav_per_share
premium_to_nav = mnav - 1
```

I chose this indicator for three reasons. First, it is directly related to the valuation logic of DAT.co firms because these companies are often discussed in relation to the digital assets they hold. Second, it is intuitive to visualize: positive values indicate that the stock trades above the BTC-backed proxy, while negative values indicate a discount. Third, it is simple enough to implement in a transparent way for a course assignment while still being financially meaningful.

## 2. Relationship with Bitcoin (BTC)

The indicator is closely connected to Bitcoin because the underlying proxy is built from the firm's Bitcoin holdings and the BTC market price. When BTC rises, the estimated BTC-backed NAV per share also tends to rise. However, the market price of MSTR may rise by more or less than that implied value.

This gap is exactly what Premium to NAV measures. A high premium suggests that the market is valuing more than the firm's current BTC backing alone. That extra valuation may reflect investor sentiment, expectations of future Bitcoin accumulation, financing flexibility, leverage-like exposure, or the market's willingness to treat MSTR as a listed proxy for Bitcoin exposure. A discount would indicate that the market values the stock below the simplified BTC-backed estimate.

Therefore, this indicator does not just reflect BTC itself. It also reflects how the stock market prices a Bitcoin treasury company relative to its Bitcoin exposure.

## 3. Data Collection and Methodology

The system uses two types of data.

The first type is market data:

- BTC-USD daily closing prices
- MSTR daily closing prices

These are collected by a Python script and stored in CSV files under `data/raw/`.

The second type is manually maintained fundamental inputs:

- BTC holdings
- shares outstanding
- the reference date of those values

These values are stored in `data/config/fundamentals.json`. After the raw data is downloaded, another Python script merges the time series and computes the indicator outputs. The processed results are written to:

- `data/processed/indicator.csv`
- `data/processed/indicator.json`
- `docs/data/indicator.json`

The website itself is static. It does not query a live backend. Instead, GitHub Actions is used as a batch update pipeline. During development, the workflow can run hourly for testing. After the system is verified, the schedule can be changed to daily frequency.

An important limitation is that this is a **Bitcoin-backed NAV proxy**, not a full corporate valuation model. It does not include all assets, liabilities, business operations, taxes, or capital structure adjustments. The goal is to build a transparent monitoring tool rather than a complete valuation engine.

## 4. Website Design

The deployed website is a single-page dashboard with the following components:

- summary cards for the latest Premium to NAV, mNAV, BTC price, MSTR price, and update time
- a daily time-series chart of Premium to NAV
- range buttons for 30D, 90D, 1Y, and ALL
- a short explanation of the indicator formula
- a brief interpretation box based on the latest value

This design keeps the site lightweight and easy to deploy while still satisfying the requirement of web-based visualization.

## 5. Deployed Website URL

Replace this line with your actual GitHub Pages URL after deployment:

```text
https://YOUR_USERNAME.github.io/YOUR_REPOSITORY_NAME/
```

## 6. Conclusion

This project builds a practical monitoring dashboard for a DAT.co-related valuation indicator. By combining data collection, indicator construction, and web visualization, the website provides a simple way to observe how MSTR trades relative to its BTC-backed valuation proxy over time. The final result is a low-cost and reproducible daily monitoring platform that fits the assignment requirements.
