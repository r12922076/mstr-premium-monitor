from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yfinance as yf

from utils import RAW_DIR, ensure_directories, save_csv


@dataclass(frozen=True)
class DownloadSpec:
    ticker: str
    column_name: str
    output_name: str


SPECS: tuple[DownloadSpec, ...] = (
    DownloadSpec(ticker="BTC-USD", column_name="btc_close", output_name="btc_price.csv"),
    DownloadSpec(ticker="MSTR", column_name="mstr_close", output_name="mstr_price.csv"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch market data for BTC and MSTR.")
    parser.add_argument("--start-date", default="2024-01-01", help="YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="YYYY-MM-DD, exclusive. Defaults to tomorrow UTC.")
    parser.add_argument("--demo", action="store_true", help="Generate deterministic demo data without network access.")
    return parser.parse_args()


def default_end_date() -> str:
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    return tomorrow.isoformat()


def download_price_history(spec: DownloadSpec, start_date: str, end_date: str) -> pd.DataFrame:
    df = yf.download(
        spec.ticker,
        start=start_date,
        end=end_date,
        auto_adjust=False,
        progress=False,
        interval="1d",
        threads=False,
    )
    if df.empty:
        raise RuntimeError(f"No data returned for {spec.ticker}.")

    # yfinance can return a MultiIndex even for a single ticker depending on version.
    if isinstance(df.columns, pd.MultiIndex):
        close_series = df[("Close", spec.ticker)] if ("Close", spec.ticker) in df.columns else df["Close"].iloc[:, 0]
    else:
        close_series = df["Close"]

    out = close_series.reset_index()
    out.columns = ["date", spec.column_name]
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    out = out.dropna().sort_values("date").reset_index(drop=True)
    return out


def generate_demo_series(start_date: str, end_date: str, column_name: str, base: float, trend: float, amplitude: float) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=pd.Timestamp(end_date) - pd.Timedelta(days=1), freq="D")
    if len(dates) == 0:
        raise ValueError("Demo date range is empty.")
    idx = np.arange(len(dates), dtype=float)
    values = base + trend * idx + amplitude * np.sin(idx / 8.0)
    values = np.maximum(values, 1.0)
    return pd.DataFrame({"date": dates, column_name: np.round(values, 2)})


def write_frames(frames: Iterable[tuple[pd.DataFrame, Path]]) -> None:
    for df, path in frames:
        save_csv(df, path)
        print(f"Saved {len(df)} rows to {path}")


def main() -> None:
    args = parse_args()
    ensure_directories()
    end_date = args.end_date or default_end_date()

    if args.demo:
        btc = generate_demo_series(args.start_date, end_date, "btc_close", base=45000.0, trend=35.0, amplitude=2500.0)
        mstr = generate_demo_series(args.start_date, end_date, "mstr_close", base=250.0, trend=0.3, amplitude=18.0)
        write_frames(
            [
                (btc, RAW_DIR / "btc_price.csv"),
                (mstr, RAW_DIR / "mstr_price.csv"),
            ]
        )
        return

    frames: list[tuple[pd.DataFrame, Path]] = []
    for spec in SPECS:
        df = download_price_history(spec, args.start_date, end_date)
        frames.append((df, RAW_DIR / spec.output_name))
    write_frames(frames)


if __name__ == "__main__":
    main()
