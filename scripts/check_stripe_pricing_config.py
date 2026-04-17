"""Validate Stripe pricing configuration for AgentNexLiFy.

Default mode checks env var presence/shape without contacting Stripe.
Use --live in a trusted deployment shell to verify the actual Stripe Price
objects match the expected amounts, currency, and monthly recurring interval.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PRICES: dict[str, tuple[str, int]] = {
    "STRIPE_PRICE_GROWTH_MONTHLY": ("Growth", 24900),
    "STRIPE_PRICE_AUTOPILOT_MONTHLY": ("Autopilot", 29900),
    "STRIPE_PRICE_PROFESSIONAL_MONTHLY": ("Professional", 49900),
    "STRIPE_PRICE_ENTERPRISE_MONTHLY": ("Enterprise", 89900),
    "STRIPE_PRICE_MARKETING_ADDON_MONTHLY": ("Marketing Suite Add-on", 4999),
}

REQUIRED_SECRETS: dict[str, tuple[str, tuple[str, ...]]] = {
    "STRIPE_SECRET_KEY": ("Stripe API secret key", ("sk_", "rk_", "sks_")),
    "STRIPE_WEBHOOK_SECRET": ("Stripe webhook signing secret", ("whsec_",)),
}


def _load_dotenv() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _check_env(require_live_env: bool) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    for env_name, (label, allowed_prefixes) in REQUIRED_SECRETS.items():
        value = os.environ.get(env_name, "").strip()
        if not value:
            message = f"{env_name} is not set ({label})"
            if require_live_env:
                failures.append(message)
            else:
                warnings.append(message)
            continue
        if not value.startswith(allowed_prefixes):
            failures.append(
                f"{env_name} has an unexpected format ({label})"
            )

    for env_name, (label, _) in EXPECTED_PRICES.items():
        price_id = os.environ.get(env_name, "").strip()
        if not price_id:
            message = f"{env_name} is not set ({label})"
            if require_live_env:
                failures.append(message)
            else:
                warnings.append(message)
            continue
        if not price_id.startswith("price_"):
            failures.append(f"{env_name} should look like price_... ({label})")

    return failures, warnings


def _check_live_prices(failures: list[str]) -> None:
    secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        failures.append("STRIPE_SECRET_KEY is required for --live")
        return

    try:
        import stripe
    except ImportError:
        failures.append("stripe package is not installed")
        return

    stripe.api_key = secret_key

    for env_name, (label, expected_amount) in EXPECTED_PRICES.items():
        price_id = os.environ.get(env_name, "").strip()
        if not price_id or not price_id.startswith("price_"):
            continue

        try:
            price = stripe.Price.retrieve(price_id)
        except Exception as exc:  # pragma: no cover - live Stripe only
            failures.append(f"{env_name} ({label}) could not be retrieved from Stripe: {type(exc).__name__}")
            continue

        unit_amount = _get(price, "unit_amount")
        currency = (_get(price, "currency") or "").lower()
        recurring = _get(price, "recurring") or {}
        interval = _get(recurring, "interval")
        active = _get(price, "active")

        if unit_amount != expected_amount:
            failures.append(f"{env_name} ({label}) amount is {unit_amount}, expected {expected_amount}")
        if currency != "usd":
            failures.append(f"{env_name} ({label}) currency is {currency or 'missing'}, expected usd")
        if interval != "month":
            failures.append(f"{env_name} ({label}) interval is {interval or 'missing'}, expected month")
        if active is not True:
            failures.append(f"{env_name} ({label}) is not active")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-live-env", action="store_true")
    parser.add_argument("--live", action="store_true", help="Retrieve configured prices from Stripe")
    args = parser.parse_args()

    _load_dotenv()
    failures, warnings = _check_env(require_live_env=args.require_live_env or args.live)
    if args.live:
        _check_live_prices(failures)

    for warning in warnings:
        print(f"WARN: {warning}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    if args.live:
        print("PASS: Stripe live price objects match expected monthly pricing.")
    elif warnings:
        print("PASS: Stripe pricing env checks completed with warnings.")
    else:
        print("PASS: Stripe pricing env checks are clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
