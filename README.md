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
- Optionally generates a short build-time summary written to `docs/data/summary.json`

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
│  ├─ generate_summary.py
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

## Optional AI summary

This repo now supports an **optional build-time summary** path:

- Default behavior: a rule-based summary is generated every run.
- Optional Gemma behavior: if you enable repo variable `ENABLE_AI_SUMMARY=1`, set `SUMMARY_MODEL_ID=google/gemma-3-1b-it`, and provide a `HF_TOKEN`, the workflow will try to generate the summary with Gemma and fall back to the rule-based summary if that fails.

Recommended first pass:

1. Keep `ENABLE_AI_SUMMARY` unset or set to `0`.
2. Confirm the workflow succeeds with the rule-based summary.
3. Then turn on the optional Gemma path.

## Deployment assumption

This repo is structured so that:

- the website is served from `docs/`
- the chart reads `docs/data/indicator.json`
- the AI summary box reads `docs/data/summary.json`
- GitHub Actions refreshes indicator and summary outputs

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

## GitHub repo settings for optional Gemma summary

If you want to test the optional Gemma path, add these in **Settings → Secrets and variables → Actions**:

- **Repository variable** `ENABLE_AI_SUMMARY=1`
- **Repository variable** `SUMMARY_MODEL_ID=google/gemma-3-1b-it`
- **Repository secret** `HF_TOKEN=<your Hugging Face token>`

Leave `ENABLE_AI_SUMMARY=0` or unset if you only want the safe fallback summary.
