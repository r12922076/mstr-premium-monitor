from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from google import genai
from utils import DOCS_DATA_DIR, PROCESSED_DIR, load_json, save_json

DEFAULT_MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")


def tail(series: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    return series[-n:] if len(series) > n else series


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def compute_context(payload: dict[str, Any], window_days: int = 30) -> dict[str, Any]:
    series = payload["series"]
    latest = series[-1]
    recent = tail(series, window_days)
    first = recent[0]

    premium_values = [row["premium_to_nav"] for row in recent]
    return {
        "ticker": payload["meta"].get("ticker", "MSTR"),
        "company_name": payload["meta"].get("company_name", "Strategy"),
        "latest_date": latest["date"],
        "latest_premium": latest["premium_to_nav"],
        "latest_mnav": latest["mnav"],
        "latest_btc": latest["btc_close"],
        "latest_stock": latest["mstr_close"],
        "window_days": len(recent),
        "premium_start": first["premium_to_nav"],
        "premium_change": latest["premium_to_nav"] - first["premium_to_nav"],
        "premium_avg": mean(premium_values),
        "premium_min": min(premium_values),
        "premium_max": max(premium_values),
        "btc_change": latest["btc_close"] / first["btc_close"] - 1.0 if first["btc_close"] else 0.0,
        "stock_change": latest["mstr_close"] / first["mstr_close"] - 1.0 if first["mstr_close"] else 0.0,
    }


def rule_based_summary(ctx: dict[str, Any]) -> str:
    if ctx["latest_premium"] < 0:
        opening = (
            f"As of {ctx['latest_date']}, {ctx['ticker']} is trading at a discount to the Bitcoin-backed NAV proxy, "
            f"with premium to NAV at {pct(ctx['latest_premium'])} and mNAV at {ctx['latest_mnav']:.2f}x."
        )
    else:
        opening = (
            f"As of {ctx['latest_date']}, {ctx['ticker']} is trading at a premium to the Bitcoin-backed NAV proxy, "
            f"with premium to NAV at {pct(ctx['latest_premium'])} and mNAV at {ctx['latest_mnav']:.2f}x."
        )

    movement = "widened" if ctx["premium_change"] > 0.02 else "narrowed" if ctx["premium_change"] < -0.02 else "been relatively stable"
    if movement == "been relatively stable":
        movement_clause = f"Over the last {ctx['window_days']} observations, the premium has been relatively stable around {pct(ctx['premium_avg'])}."
    else:
        movement_clause = f"Over the last {ctx['window_days']} observations, the premium has {movement} by {pct(abs(ctx['premium_change']))}, compared with an average premium of {pct(ctx['premium_avg'])}."

    btc_clause = (
        f"During the same window, BTC moved {pct(ctx['btc_change'])} while MSTR moved {pct(ctx['stock_change'])}."
    )
    return " ".join([opening, movement_clause, btc_clause])


def build_prompt(ctx: dict[str, Any]) -> str:
    return (
        "Write a concise 2-3 sentence dashboard summary for a student DAT.co project. "
        "Be neutral. No investment advice. Mention whether the premium is negative, modest, or high; "
        "whether it widened, narrowed, or stayed similar; and relate it briefly to BTC.\n\n"
        f"Company: {ctx['company_name']} ({ctx['ticker']})\n"
        f"Latest date: {ctx['latest_date']}\n"
        f"Latest premium to NAV: {pct(ctx['latest_premium'])}\n"
        f"Latest mNAV: {ctx['latest_mnav']:.2f}x\n"
        f"Latest BTC price: ${ctx['latest_btc']:.2f}\n"
        f"Latest stock price: ${ctx['latest_stock']:.2f}\n"
        f"Recent window length: {ctx['window_days']} observations\n"
        f"Window start premium to NAV: {pct(ctx['premium_start'])}\n"
        f"Premium change over window: {pct(ctx['premium_change'])}\n"
        f"Average premium over window: {pct(ctx['premium_avg'])}\n"
        f"Window premium range: {pct(ctx['premium_min'])} to {pct(ctx['premium_max'])}\n"
        f"BTC return over window: {pct(ctx['btc_change'])}\n"
        f"Stock return over window: {pct(ctx['stock_change'])}\n"
    )


def generate_with_gemini(prompt: str, model_id: str) -> str:
    client = genai.Client()
    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
    )
    return (response.text or "").strip()


def build_payload(summary: str, backend_used: str, model_id: str | None, fallback_used: bool) -> dict[str, Any]:
    return {
        "backend": backend_used,
        "model_id": model_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fallback_used": fallback_used,
        "summary": summary,
    }


def main() -> None:
    payload = load_json(PROCESSED_DIR / "indicator.json")
    ctx = compute_context(payload, 30)
    prompt = build_prompt(ctx)

    enable_ai_summary = os.getenv("ENABLE_AI_SUMMARY", "1") == "1"
    model_id = DEFAULT_MODEL_ID

    fallback_used = False
    backend_used = "gemini"

    try:
        if enable_ai_summary:
            summary = generate_with_gemini(prompt, model_id)
            if not summary:
                raise RuntimeError("Gemini returned an empty summary.")
        else:
            raise RuntimeError("AI summary disabled.")
    except Exception as exc:
        summary = rule_based_summary(ctx) + f" [Fallback activated: {type(exc).__name__}]"
        backend_used = "rule_based"
        model_id = None
        fallback_used = True

    summary_payload = build_payload(summary, backend_used, model_id, fallback_used)
    save_json(PROCESSED_DIR / "summary.json", summary_payload)
    save_json(DOCS_DATA_DIR / "summary.json", summary_payload)
    print(f"Saved summary using backend={backend_used}, fallback_used={fallback_used}")


if __name__ == "__main__":
    main()
