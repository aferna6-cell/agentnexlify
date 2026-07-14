"""Lead attribution sanitization.

Pure helper — no I/O, no DB. Widget sends an optional `attribution` dict on
lead submit (`{source, utm_source, utm_medium, utm_campaign, referrer,
landing_path}`) that gets stored on `leads.attribution` (jsonb, migration
172). This module strips anything that isn't a known string key so a
malformed or hostile payload can never corrupt the row or blow up storage.
"""

ATTRIBUTION_KEYS: frozenset[str] = frozenset({
    "source",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "referrer",
    "landing_path",
})

_MAX_VALUE_LENGTH = 300


def _sanitize_attribution(raw: dict | None) -> dict | None:
    """Keep only known string keys, truncate each value to 300 chars.

    Returns None for anything that isn't a dict, and for a dict that yields
    no usable keys after filtering (nothing worth storing). Never raises —
    callers wrap this in try/except anyway, but the function itself is
    defensive so a bad `raw` (wrong type, non-string values, unknown keys)
    degrades to None instead of throwing.
    """
    if not isinstance(raw, dict):
        return None

    cleaned: dict[str, str] = {}
    for key in ATTRIBUTION_KEYS:
        value = raw.get(key)
        if isinstance(value, str) and value:
            cleaned[key] = value[:_MAX_VALUE_LENGTH]

    return cleaned or None
