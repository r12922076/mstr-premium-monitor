# Deploy checklist

## 1. Push to GitHub

- Create a new GitHub repository.
- Upload this repo.
- Make sure the default branch is `main`.

## 2. Enable Pages

- Go to repository settings.
- Open the Pages section.
- Set the publishing source to the `docs/` folder on `main`.
- Save.

## 3. Test the data pipeline

- Open the Actions tab.
- Run `Update market data` manually once.
- Wait for the workflow to finish.
- Confirm these files were refreshed:
  - `data/raw/btc_price.csv`
  - `data/raw/mstr_price.csv`
  - `data/processed/indicator.csv`
  - `data/processed/indicator.json`
  - `docs/data/indicator.json`

## 4. Check the website

- Open the Pages URL.
- Confirm the summary cards load.
- Confirm the chart loads.
- Confirm the range buttons work.
- Confirm the last updated timestamp changes after a workflow run.

## 5. Before final submission

- Update `data/config/fundamentals.json` with the BTC holdings and shares outstanding values you want to use.
- Replace the temporary website URL placeholder in `report/report_draft.md`.
- Decide whether to keep the hourly test cron or switch to daily.
- Take one or two screenshots for the report.

## 6. Recommended final cron

Use hourly testing first. After verification, change the workflow to a daily schedule.

Suggested final version:

```yaml
on:
  schedule:
    - cron: '5 0 * * *'
  workflow_dispatch:
```

If you want a Taiwan morning refresh, adjust the cron to the UTC time you prefer.


## Optional Gemma summary checklist

- [ ] Keep the first workflow test on the default fallback summary path.
- [ ] If you want the Gemma path, accept the Gemma model terms on Hugging Face first.
- [ ] Add repository variable `ENABLE_AI_SUMMARY=1`.
- [ ] Add repository variable `SUMMARY_MODEL_ID=google/gemma-3-1b-it`.
- [ ] Add repository secret `HF_TOKEN`.
- [ ] Re-run the workflow and confirm `docs/data/summary.json` shows `backend: transformers` instead of `rule_based`.
