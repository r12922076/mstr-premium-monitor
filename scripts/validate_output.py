from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import pandas as pd

from utils import PROCESSED_DIR, load_csv, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate processed indicator output.")
    parser.add_argument(
        "--max-staleness-days",
        type=int,
        default=7,
        help="Maximum age of the latest observation before failing.",
    )
    parser.add_argument(
        "--skip-recency-check",
        action="store_true",
        help="Skip latest-date freshness validation.",
    )
    return parser.parse_args()


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    args = parse_args()
    df = load_csv(PROCESSED_DIR / "indicator.csv")
    payload = load_json(PROCESSED_DIR / "indicator.json")

    assert_true(not df.empty, "indicator.csv is empty.")
    assert_true(df["date"].is_monotonic_increasing, "Dates must be sorted ascending.")
    assert_true(df["date"].duplicated().sum() == 0, "Duplicate dates found.")

    required_columns = [
        "btc_close",
        "mstr_close",
        "btc_nav_total",
        "btc_nav_per_share",
        "mnav",
        "premium_to_nav",
        "premium_to_nav_pct",
    ]
    missing = [col for col in required_columns if col not in df.columns]
    assert_true(len(missing) == 0, f"Missing columns: {missing}")
    assert_true(df[required_columns].notna().all().all(), "NaN values found in required numeric columns.")
    assert_true((df[["btc_close", "mstr_close", "btc_nav_total", "btc_nav_per_share", "mnav"]] > 0).all().all(), "Positive-value constraint failed.")

    delta = (df["mnav"] - (1.0 + df["premium_to_nav"]))
    assert_true((delta.abs() < 1e-6).all(), "mnav != 1 + premium_to_nav")

    assert_true(payload["meta"]["indicator"] == "premium_to_nav", "Unexpected indicator name in JSON payload.")
    assert_true(len(payload["series"]) == len(df), "JSON series length does not match CSV length.")

    if not args.skip_recency_check:
        latest_date = pd.to_datetime(df["date"].iloc[-1]).date()
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=args.max_staleness_days)
        assert_true(latest_date >= cutoff, f"Latest observation is stale: {latest_date} < {cutoff}")

    print(f"Validation passed for {len(df)} rows.")


if __name__ == "__main__":
    main()
