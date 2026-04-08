from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
INDICATOR_JSON = ROOT / "data" / "processed" / "indicator.json"
PROCESSED_SUMMARY_JSON = ROOT / "data" / "processed" / "summary.json"
DOCS_SUMMARY_JSON = ROOT / "docs" / "data" / "summary.json"

def load_indicator() -> dict:
    with INDICATOR_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

def slice_recent(series: list[dict], n: int) -> list[dict]:
    return series[-n:] if len(series) >= n else series

def fallback_summary(meta: dict, series: list[dict]) -> dict:
    latest = series[-1]
    recent_7 = slice_recent(series, 7)
    recent_30 = slice_recent(series, 30)

    latest_premium = safe_float(latest.get("premium_to_nav"))
    latest_mnav = safe_float(latest.get("mnav"))
    latest_btc = safe_float(latest.get("btc_close"))
    latest_stock = safe_float(latest.get("stock_close"))
    if latest_stock is None:
        latest_stock = safe_float(latest.get("mstr_close"))

    avg7 = mean([safe_float(x["premium_to_nav"]) for x in recent_7 if safe_float(x.get("premium_to_nav")) is not None])
    avg30 = mean([safe_float(x["premium_to_nav"]) for x in recent_30 if safe_float(x.get("premium_to_nav")) is not None])

    if latest_premium is None:
        sentence1 = "The latest premium to NAV could not be computed from the available data."
    elif latest_premium > 0.5:
        sentence1 = f"{meta.get('ticker', 'The stock')} is trading at a high premium to its Bitcoin-backed NAV proxy."
    elif latest_premium > 0:
        sentence1 = f"{meta.get('ticker', 'The stock')} is trading at a moderate premium to its Bitcoin-backed NAV proxy."
    else:
        sentence1 = f"{meta.get('ticker', 'The stock')} is trading at or below its Bitcoin-backed NAV proxy."

    if avg7 > avg30:
        sentence2 = "The short-run premium has been stronger than the recent monthly average, suggesting rising enthusiasm."
    elif avg7 < avg30:
        sentence2 = "The short-run premium has softened relative to the recent monthly average, suggesting cooling sentiment."
    else:
        sentence2 = "The short-run premium is roughly in line with the recent monthly average."

    sentence3 = (
        f"Latest values: premium to NAV = {latest_premium:.2%}, "
        f"mNAV = {latest_mnav:.2f}, BTC = ${latest_btc:,.2f}, "
        f"{meta.get('ticker', 'stock')} = ${latest_stock:,.2f}."
        if None not in (latest_premium, latest_mnav, latest_btc, latest_stock)
        else "Latest market values are available in the dashboard."
    )

    return {
        "backend": "rule_based",
        "model": "rule-based-fallback",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": " ".join([sentence1, sentence2, sentence3]).strip(),
    }

def build_prompt(meta: dict, series: list[dict]) -> str:
    latest = series[-1]
    recent_7 = slice_recent(series, 7)
    recent_30 = slice_recent(series, 30)

    latest_premium = safe_float(latest.get("premium_to_nav"))
    latest_mnav = safe_float(latest.get("mnav"))
    latest_btc = safe_float(latest.get("btc_close"))
    latest_stock = safe_float(latest.get("stock_close"))
    if latest_stock is None:
        latest_stock = safe_float(latest.get("mstr_close"))

    avg7 = mean([safe_float(x["premium_to_nav"]) for x in recent_7 if safe_float(x.get("premium_to_nav")) is not None])
    avg30 = mean([safe_float(x["premium_to_nav"]) for x in recent_30 if safe_float(x.get("premium_to_nav")) is not None])

    latest_premium_str = "NA" if latest_premium is None else f"{latest_premium:.6f}"
    latest_mnav_str = "NA" if latest_mnav is None else f"{latest_mnav:.6f}"
    latest_btc_str = "NA" if latest_btc is None else f"{latest_btc:.2f}"
    latest_stock_str = "NA" if latest_stock is None else f"{latest_stock:.2f}"
    avg7_str = "NA" if avg7 is None else f"{avg7:.6f}"
    avg30_str = "NA" if avg30 is None else f"{avg30:.6f}"

    return f"""You are writing a short dashboard summary for a finance website.
Write exactly 2 to 4 sentences.
Keep it factual and concise.
Do not mention that you are an AI model.
Do not use bullet points.
Do not output headings.

Context:
- Company: {meta.get('company_name', 'Unknown')}
- Ticker: {meta.get('ticker', 'Unknown')}
- Indicator: premium_to_nav
- Interpretation: positive means premium to Bitcoin-backed NAV proxy; negative means discount.
- Latest premium_to_nav: {latest_premium_str}
- Latest mNAV: {latest_mnav_str}
- Latest BTC price: {latest_btc_str}
- Latest stock price: {latest_stock_str}
- Mean premium_to_nav over last 7 observations: {avg7_str}
- Mean premium_to_nav over last 30 observations: {avg30_str}
- Latest date: {latest.get('date')}

Task:
Write a brief market commentary summarizing the latest premium level and whether short-run sentiment appears stronger or weaker than the recent monthly average.
"""

def run_llama_cli(prompt: str) -> str:
    llama_cli = os.environ["LLAMA_CLI_PATH"]
    model_path = os.environ["GGUF_MODEL_PATH"]

    cmd = [
        llama_cli,
        "-m", model_path,
        "-n", "16",
        "-c", "1024",
        "-t", "4",
        "--temp", "0.1",
        "--top-p", "0.8",
        "-p", prompt,
        "--no-display-prompt",
    ]
    print("About to run llama-cli...", flush=True)
    print("Command:", " ".join(cmd), flush=True)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )
    except subprocess.CalledProcessError as e:
        print("llama-cli return code:", e.returncode, flush=True)
        print("llama-cli stdout:", (e.stdout or "")[-4000:], flush=True)
        print("llama-cli stderr:", (e.stderr or "")[-4000:], flush=True)
        raise
    except subprocess.TimeoutExpired as e:
        print("llama-cli timed out", flush=True)
        print("llama-cli stdout:", ((e.stdout or "") if isinstance(e.stdout, str) else "")[-4000:], flush=True)
        print("llama-cli stderr:", ((e.stderr or "") if isinstance(e.stderr, str) else "")[-4000:], flush=True)
        raise

    text = (result.stdout or "").strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text

def save_summary(payload: dict) -> None:
    PROCESSED_SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    DOCS_SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)

    for target in [PROCESSED_SUMMARY_JSON, DOCS_SUMMARY_JSON]:
        with target.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

def main() -> None:
    data = load_indicator()
    meta = data.get("meta", {})
    series = data.get("series", [])
    if not series:
        payload = {
            "backend": "rule_based",
            "model": "rule-based-fallback",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": "No indicator data is available yet.",
        }
        save_summary(payload)
        return

    enable_ai = os.environ.get("ENABLE_AI_SUMMARY", "0") == "1"
    llama_cli = os.environ.get("LLAMA_CLI_PATH")
    gguf_model = os.environ.get("GGUF_MODEL_PATH")

    if enable_ai and llama_cli and gguf_model and Path(llama_cli).exists() and Path(gguf_model).exists():
        try:
            prompt = build_prompt(meta, series)
            summary = run_llama_cli(prompt)
            payload = {
                "backend": "llama.cpp",
                "model": Path(gguf_model).name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
            }
            save_summary(payload)
            print("Generated summary with llama.cpp.")
            return
        except Exception as e:
            print(f"llama.cpp summary failed, falling back to rule-based summary: {e}")

    payload = fallback_summary(meta, series)
    save_summary(payload)
    print("Generated fallback summary.")

if __name__ == "__main__":
    main()
