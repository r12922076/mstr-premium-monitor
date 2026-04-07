from __future__ import annotations

import argparse
import importlib.util
import os
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from utils import DOCS_DATA_DIR, PROCESSED_DIR, load_json, save_json

DEFAULT_MODEL_ID = "google/gemma-3-1b-it"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an optional AI summary for the dashboard.")
    parser.add_argument(
        "--backend",
        choices=["auto", "rule_based", "transformers"],
        default=os.getenv("SUMMARY_BACKEND", "auto"),
        help="Summary backend. 'auto' tries transformers first when enabled and available, then falls back.",
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("SUMMARY_MODEL_ID", DEFAULT_MODEL_ID),
        help="Hugging Face model id used when backend=transformers.",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=int(os.getenv("SUMMARY_WINDOW_DAYS", "30")),
        help="Number of recent observations to summarize.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail instead of falling back to a rule-based summary.",
    )
    return parser.parse_args()


def tail(series: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    return series[-n:] if len(series) > n else series


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def compute_context(payload: dict[str, Any], window_days: int) -> dict[str, Any]:
    series = payload["series"]
    latest = series[-1]
    recent = tail(series, window_days)
    first = recent[0]

    premium_values = [row["premium_to_nav"] for row in recent]
    btc_values = [row["btc_close"] for row in recent]
    stock_values = [row["mstr_close"] for row in recent]

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


def build_prompt(ctx: dict[str, Any]) -> str:
    return (
        "Write a concise 2-3 sentence dashboard summary for a student project about a DAT.co indicator. "
        "Focus only on the recent data below. Avoid investment advice. Mention whether the premium is high, moderate, or negative; "
        "note whether it widened or narrowed; and relate it briefly to BTC behavior.\n\n"
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


def classify_premium(value: float) -> str:
    if value < 0:
        return "negative"
    if value < 0.25:
        return "modest"
    if value < 0.75:
        return "moderate"
    return "substantial"


def trend_word(delta: float) -> str:
    if delta > 0.02:
        return "widened"
    if delta < -0.02:
        return "narrowed"
    return "been relatively stable"


def rule_based_summary(ctx: dict[str, Any]) -> str:
    premium_class = classify_premium(ctx["latest_premium"])
    movement = trend_word(ctx["premium_change"])

    if ctx["latest_premium"] < 0:
        opening = (
            f"As of {ctx['latest_date']}, {ctx['ticker']} is trading at a discount to the Bitcoin-backed NAV proxy, "
            f"with premium to NAV at {pct(ctx['latest_premium'])} and mNAV at {ctx['latest_mnav']:.2f}x."
        )
    else:
        opening = (
            f"As of {ctx['latest_date']}, {ctx['ticker']} is trading at a {premium_class} premium to the Bitcoin-backed NAV proxy, "
            f"with premium to NAV at {pct(ctx['latest_premium'])} and mNAV at {ctx['latest_mnav']:.2f}x."
        )

    if movement == "been relatively stable":
        movement_clause = f"Over the last {ctx['window_days']} observations, the premium has been relatively stable around {pct(ctx['premium_avg'])}."
    else:
        movement_clause = f"Over the last {ctx['window_days']} observations, the premium has {movement} by {pct(abs(ctx['premium_change']))}, compared with an average premium of {pct(ctx['premium_avg'])}."

    btc_clause = (
        f"During the same window, BTC moved {pct(ctx['btc_change'])} while MSTR moved {pct(ctx['stock_change'])}, "
        "suggesting that the equity valuation may be reflecting more than spot Bitcoin exposure alone."
    )
    return " ".join([opening, movement_clause, btc_clause])


def transformers_available() -> bool:
    return importlib.util.find_spec("transformers") is not None and importlib.util.find_spec("torch") is not None


def generate_with_transformers(prompt: str, model_id: str) -> str:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    token = os.getenv("HF_TOKEN")
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        token=token,
        torch_dtype=torch.float32,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You write concise, neutral market summaries for a dashboard. "
                "Use 2-3 sentences. Avoid hype and avoid investment advice."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    if hasattr(tokenizer, "apply_chat_template"):
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
            tokenize=True,
        )
    else:
        text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages) + "\nASSISTANT:"
        inputs = tokenizer(text, return_tensors="pt").input_ids

    output = model.generate(
        inputs,
        max_new_tokens=140,
        do_sample=False,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id,
    )
    generated_tokens = output[0][inputs.shape[-1]:]
    text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    return text


def build_payload(summary: str, backend_used: str, model_id: str, fallback_used: bool, prompt: str) -> dict[str, Any]:
    return {
        "model_family": "gemma" if backend_used == "transformers" else "rule_based",
        "backend": backend_used,
        "model_id": model_id if backend_used == "transformers" else None,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fallback_used": fallback_used,
        "summary": summary,
        "prompt_preview": prompt[:500],
    }


def main() -> None:
    args = parse_args()
    payload = load_json(PROCESSED_DIR / "indicator.json")
    ctx = compute_context(payload, args.window_days)
    prompt = build_prompt(ctx)

    enable_ai_summary = os.getenv("ENABLE_AI_SUMMARY", "0") == "1"
    backend = args.backend
    if backend == "auto":
        backend = "transformers" if enable_ai_summary and transformers_available() else "rule_based"

    fallback_used = False
    summary: str
    backend_used = backend
    try:
        if backend == "transformers":
            summary = generate_with_transformers(prompt, args.model_id)
            if not summary:
                raise RuntimeError("Model returned an empty summary.")
        else:
            summary = rule_based_summary(ctx)
            backend_used = "rule_based"
    except Exception as exc:
        if args.strict:
            raise
        summary = rule_based_summary(ctx)
        backend_used = "rule_based"
        fallback_used = True
        summary = summary + f" [Fallback activated: {type(exc).__name__}]"

    summary_payload = build_payload(summary, backend_used, args.model_id, fallback_used, prompt)
    save_json(PROCESSED_DIR / "summary.json", summary_payload)
    save_json(DOCS_DATA_DIR / "summary.json", summary_payload)
    print(f"Saved summary using backend={backend_used}, fallback_used={fallback_used}")


if __name__ == "__main__":
    main()
