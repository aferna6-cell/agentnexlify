"""Public, customer-facing status page (rubric item 7.5).

Serves a no-auth, no-schema HTML page at GET /status that reflects live
service health by reusing the same Supabase connectivity check the JSON
/health endpoint already performs. This is the in-repo building block for a
status surface; a hosted product (Statuspage/BetterUptime) or a
status.agentnexlify.com CNAME can later point here or replace it.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
Never add 'from __future__ import annotations' to this file.
"""

import logging
import time

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from backend.config import is_production  # noqa: F401  (kept for future gating)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["status"])

_STATUS_STARTED = time.time()


def _supabase_status() -> str:
    """Return 'connected' / 'disconnected' without raising.

    Mirrors the connectivity probe in main.py:health() so the public page and
    the JSON health endpoint agree.
    """
    try:
        from backend.models.database import get_service_supabase

        db = get_service_supabase()
        db.table("tenants").select("id").limit(1).execute()
        return "connected"
    except Exception:
        logger.warning("Status page: supabase unreachable", exc_info=True)
        return "disconnected"


def _snapshot() -> dict:
    supabase = _supabase_status()
    overall = "operational" if supabase == "connected" else "degraded"
    return {
        "overall": overall,
        "components": [
            {"name": "API", "status": "operational"},
            {
                "name": "Database",
                "status": "operational" if supabase == "connected" else "degraded",
            },
        ],
    }


@router.api_route("/status.json", methods=["GET", "HEAD"])
def status_json():
    """Machine-readable status (for embeds / external monitors)."""
    snap = _snapshot()
    code = 200 if snap["overall"] == "operational" else 503
    return JSONResponse(status_code=code, content=snap)


@router.api_route("/status", methods=["GET", "HEAD"])
def status_page():
    """Public HTML status page. No auth, no tenant scope, no DB writes."""
    snap = _snapshot()
    operational = snap["overall"] == "operational"
    banner_color = "#16a34a" if operational else "#d97706"
    banner_text = (
        "All systems operational" if operational else "Degraded performance"
    )

    rows = []
    for comp in snap["components"]:
        ok = comp["status"] == "operational"
        dot = "#16a34a" if ok else "#d97706"
        label = "Operational" if ok else "Degraded"
        rows.append(
            f'<div class="row"><span class="name">{comp["name"]}</span>'
            f'<span class="state"><i style="background:{dot}"></i>{label}</span></div>'
        )
    rows_html = "\n".join(rows)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentNexLiFy Status</title>
<style>
  body {{ margin:0; background:#0b0f1a; color:#e5e7eb;
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
  .wrap {{ max-width:640px; margin:0 auto; padding:48px 20px; }}
  h1 {{ font-size:20px; font-weight:600; margin:0 0 24px; }}
  .banner {{ background:{banner_color}; color:#fff; border-radius:8px;
             padding:16px 20px; font-weight:600; margin-bottom:28px; }}
  .row {{ display:flex; justify-content:space-between; align-items:center;
          padding:14px 0; border-bottom:1px solid #1f2937; }}
  .name {{ color:#cbd5e1; }}
  .state {{ display:flex; align-items:center; gap:8px; color:#9ca3af; font-size:14px; }}
  .state i {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
  .foot {{ margin-top:32px; color:#6b7280; font-size:13px; }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>AgentNexLiFy Status</h1>
    <div class="banner">{banner_text}</div>
    {rows_html}
    <p class="foot">Live check against production health. Refresh to re-poll.
       Machine-readable: <a href="/status.json" style="color:#818cf8">/status.json</a></p>
  </div>
</body>
</html>"""
    code = 200 if operational else 503
    return HTMLResponse(content=html, status_code=code)
