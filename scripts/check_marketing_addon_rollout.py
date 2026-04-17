"""Static rollout checks for the Marketing Suite add-on.

This intentionally avoids Stripe, Railway, and Supabase credentials. Use
--require-live-env in a deployment shell to fail when the Stripe price env
var is missing or malformed.
"""

import argparse
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

GATED_ROUTERS = {
    "backend/routers/local_seo.py": "/api/v1/seo",
    "backend/routers/social_media.py": "/api/v1/social",
    "backend/routers/marketing_campaigns.py": "/api/v1/campaigns",
    "backend/routers/marketing_analytics.py": "/api/v1/marketing",
    "backend/routers/ab_tests.py": "/api/v1/ab-tests",
    "backend/routers/automation_rules.py": "/api/v1/automation-rules",
}

MIGRATION_COLUMNS = (
    "marketing_addon_active",
    "marketing_addon_stripe_sub_id",
    "marketing_addon_started_at",
    "marketing_addon_grandfathered",
)


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _check_contains(path: str, needles: tuple[str, ...], failures: list[str]) -> None:
    text = _read(path)
    for needle in needles:
        if needle not in text:
            failures.append(f"{path} missing {needle!r}")


def run(*, require_live_env: bool = False) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    migration = REPO_ROOT / "migrations" / "102_marketing_addon.sql"
    if not migration.exists():
        failures.append("migrations/102_marketing_addon.sql is missing")
    else:
        text = migration.read_text(encoding="utf-8")
        for column in MIGRATION_COLUMNS:
            if column not in text:
                failures.append(f"migration 102 missing {column}")
        if "marketing_addon_grandfathered = true" not in text:
            failures.append("migration 102 does not grandfather existing paid tenants")

    _check_contains(
        "backend/config.py",
        ("stripe_price_marketing_addon_monthly",),
        failures,
    )
    _check_contains(
        ".env.example",
        ("STRIPE_PRICE_MARKETING_ADDON_MONTHLY=",),
        failures,
    )
    _check_contains(
        "backend/models/schemas.py",
        ("marketing_addon_active", "marketing_addon_grandfathered"),
        failures,
    )
    _check_contains(
        "backend/routers/auth.py",
        ("marketing_addon_active", "marketing_addon_grandfathered"),
        failures,
    )
    _check_contains(
        "backend/routers/billing.py",
        (
            "/marketing-addon/checkout",
            "/marketing-addon/cancel",
            "_handle_addon_checkout_completed",
            "_handle_addon_subscription_updated",
            "_handle_addon_subscription_deleted",
            "STRIPE_ADDON_METADATA_KEY",
        ),
        failures,
    )
    _check_contains(
        "backend/routers/stripe_webhooks.py",
        (
            "_handle_addon_checkout_completed",
            "_handle_addon_subscription_updated",
            "_handle_addon_subscription_deleted",
            "_is_marketing_addon_subscription",
        ),
        failures,
    )

    for router_path, prefix in GATED_ROUTERS.items():
        text = _read(router_path)
        if "require_marketing_addon" not in text:
            failures.append(f"{router_path} does not import require_marketing_addon")
        if "dependencies=[Depends(require_marketing_addon)]" not in text:
            failures.append(f"{router_path} does not gate {prefix}")

    _check_contains(
        "frontend/src/components/App.jsx",
        ("MarketingAddonUpsell", "marketing_addon_active"),
        failures,
    )
    _check_contains(
        "frontend/src/components/Sidebar.jsx",
        ("marketing_addon_active",),
        failures,
    )
    _check_contains(
        "frontend/src/pages/BillingPage.jsx",
        ("marketing-addon/checkout", "marketing-addon/cancel"),
        failures,
    )

    price = os.environ.get("STRIPE_PRICE_MARKETING_ADDON_MONTHLY", "")
    if not price:
        message = "STRIPE_PRICE_MARKETING_ADDON_MONTHLY is not set in this shell"
        if require_live_env:
            failures.append(message)
        else:
            warnings.append(message)
    elif not price.startswith("price_"):
        failures.append("STRIPE_PRICE_MARKETING_ADDON_MONTHLY should look like price_...")

    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-live-env", action="store_true")
    args = parser.parse_args()

    failures, warnings = run(require_live_env=args.require_live_env)
    for warning in warnings:
        print(f"WARN: {warning}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: Marketing Suite add-on rollout checks are clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
