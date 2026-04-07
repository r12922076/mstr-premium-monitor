from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from utils import CONFIG_DIR, DOCS_DATA_DIR, PROCESSED_DIR, RAW_DIR, ensure_directories, load_csv, load_json, save_csv, save_json


def build_indicator_frame() -> tuple[pd.DataFrame, dict]:
    fundamentals = load_json(CONFIG_DIR / "fundamentals.json")
    btc = load_csv(RAW_DIR / "btc_price.csv")
    mstr = load_csv(RAW_DIR / "mstr_price.csv")

    df = pd.merge(btc, mstr, on="date", how="inner").sort_values("date").dropna().reset_index(drop=True)
    if df.empty:
        raise RuntimeError("Merged market data is empty.")

    btc_holdings = float(fundamentals["btc_holdings"])
    shares_outstanding = float(fundamentals["shares_outstanding"])
    if btc_holdings <= 0 or shares_outstanding <= 0:
        raise ValueError("btc_holdings and shares_outstanding must be positive.")

    df["btc_nav_total"] = btc_holdings * df["btc_close"]
    df["btc_nav_per_share"] = df["btc_nav_total"] / shares_outstanding
    df["mnav"] = df["mstr_close"] / df["btc_nav_per_share"]
    df["premium_to_nav"] = df["mnav"] - 1.0

    # Optional lightweight signal helpers for the UI.
    df["premium_to_nav_pct"] = df["premium_to_nav"] * 100.0
    df["mnav_30d_ma"] = df["mnav"].rolling(window=30, min_periods=1).mean()
    df["premium_30d_ma"] = df["premium_to_nav"].rolling(window=30, min_periods=1).mean()

    numeric_cols = [
        "btc_close",
        "mstr_close",
        "btc_nav_total",
        "btc_nav_per_share",
        "mnav",
        "premium_to_nav",
        "premium_to_nav_pct",
        "mnav_30d_ma",
        "premium_30d_ma",
    ]
    df[numeric_cols] = df[numeric_cols].round(6)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    latest = df.iloc[-1].to_dict()
    metadata = {
        "indicator": "premium_to_nav",
        "company_name": fundamentals["company_name"],
        "ticker": fundamentals["ticker"],
        "btc_ticker": fundamentals.get("btc_ticker", "BTC-USD"),
        "currency": fundamentals.get("currency", "USD"),
        "last_updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "methodology_version": "v1",
        "holdings_as_of": fundamentals.get("holdings_as_of"),
        "btc_holdings": btc_holdings,
        "shares_outstanding": shares_outstanding,
        "notes": fundamentals.get("notes", ""),
        "source_note": fundamentals.get("source_note", ""),
        "latest_observation": latest,
    }
    return df, metadata


def write_outputs(df: pd.DataFrame, metadata: dict) -> None:
    processed_csv = PROCESSED_DIR / "indicator.csv"
    processed_json = PROCESSED_DIR / "indicator.json"
    docs_json = DOCS_DATA_DIR / "indicator.json"

    save_csv(df, processed_csv)
    payload = {"meta": metadata, "series": df.to_dict(orient="records")}
    save_json(processed_json, payload)
    save_json(docs_json, payload)
    print(f"Saved {len(df)} rows to {processed_csv}")
    print(f"Saved JSON to {processed_json} and {docs_json}")


def main() -> None:
    ensure_directories()
    df, metadata = build_indicator_frame()
    write_outputs(df, metadata)


if __name__ == "__main__":
    main()
