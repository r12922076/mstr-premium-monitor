from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CONFIG_DIR = DATA_DIR / "config"
DOCS_DIR = ROOT / "docs"
DOCS_DATA_DIR = DOCS_DIR / "data"


def ensure_directories() -> None:
    for path in [RAW_DIR, PROCESSED_DIR, CONFIG_DIR, DOCS_DATA_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"])


def to_iso_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.strftime("%Y-%m-%d")
