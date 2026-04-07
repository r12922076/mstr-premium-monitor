# MSTR Premium to NAV Monitor

A low-cost HW2 project for **CSIE5315 Bitcoin and Data Analysis**.

This repo builds a public GitHub Pages site that tracks **Strategy (MSTR)** relative to a simple **Bitcoin-backed NAV proxy**.

## What the project does

- Downloads daily market data for **BTC-USD** and **MSTR**
- Uses manually maintained fundamentals for:
  - BTC holdings
  - shares outstanding
- Computes:
  - `btc_nav_per_share`
  - `mnav`
  - `premium_to_nav`
- Publishes a static dashboard via **GitHub Pages**
- Uses **GitHub Actions** for scheduled refreshes

## Indicator definition

Let:

- `P_t` = MSTR closing price on day `t`
- `BTC_t` = BTC-USD closing price on day `t`
- `H` = BTC holdings
- `S` = shares outstanding

Then:

```text
btc_nav_per_share_t = (H * BTC_t) / S
mnav_t              = P_t / btc_nav_per_share_t
premium_to_nav_t    = mnav_t - 1
```

This is a **Bitcoin-backed NAV proxy**, not a full corporate NAV model.

## Repo structure

```text
mstr-premium-monitor/
├─ .github/workflows/update_data.yml
├─ scripts/
│  ├─ fetch_market_data.py
│  ├─ build_indicator.py
│  ├─ validate_output.py
│  └─ utils.py
├─ data/
│  ├─ config/fundamentals.json
│  ├─ raw/
│  └─ processed/
├─ docs/
│  ├─ index.html
│  ├─ style.css
│  ├─ app.js
│  ├─ .nojekyll
│  ├─ data/
│  └─ assets/
├─ report/
│  ├─ README.md
│  └─ report_draft.md
└─ DEPLOY_CHECKLIST.md
```

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

### Normal mode

```bash
python scripts/fetch_market_data.py
python scripts/build_indicator.py
python scripts/validate_output.py
```

### Demo mode (works without network)

```bash
python scripts/fetch_market_data.py --demo
python scripts/build_indicator.py
python scripts/validate_output.py --skip-recency-check
```

## Deployment assumption

This repo is structured so that:

- the website is served from `docs/`
- the chart reads `docs/data/indicator.json`
- GitHub Actions refreshes both `data/processed/indicator.json` and `docs/data/indicator.json`

## Workflow behavior

The included workflow supports both:

- scheduled runs
- manual runs via `workflow_dispatch`

Current default:

- hourly testing schedule at minute 17

Suggested final submission schedule:

- change to a daily run after the pipeline is stable

## Recommended workflow for you

1. Push the repo to GitHub.
2. Enable GitHub Pages using the `docs/` folder.
3. Open the Actions tab and run **Update market data** once manually.
4. Confirm that `docs/data/indicator.json` is updated.
5. Open the published site and check the chart.
6. After testing is stable, change the cron job to daily frequency.

## Important project assumptions

- The dashboard is intended for **daily monitoring**, not real-time trading execution.
- Fundamentals are **manually maintained** in `data/config/fundamentals.json`.
- The website is fully static; GitHub Actions acts as a **batch update pipeline**, not a live backend.
- The valuation measure is a **BTC-backed proxy**, not a full enterprise-value model.

## Files added for your submission workflow

- `DEPLOY_CHECKLIST.md`: practical GitHub setup and submission checklist
- `report/report_draft.md`: a report draft you can edit and submit
- `.github/workflows/update_data.yml`: hourly test schedule with comments for switching to daily

## Notes before submission

Please re-check and update these values before final submission:

- `btc_holdings`
- `shares_outstanding`
- `holdings_as_of`
- the public website URL inside the report draft
