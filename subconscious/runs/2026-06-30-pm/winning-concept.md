# Winning Concept — Run 74
# SMS Compliance Dashboard (Final Human Delivery — Escalation)

**Winner:** Idea 1
**Category:** Customer Value / Operational
**Effort:** S — 30–60 min paste-execute (all code below is paste-ready)
**Run 73 status:** MISSING implementation after 10+ days
**Moratorium:** Zero impact — updates run 73 existing active_directions entry, no new queue item

---

## Why This Run Re-Delivers the Same Winner

Run 73 produced architecture + file list. No code. Human activation energy = 2–4 hours.
This run delivers complete, paste-ready code blocks. Human reviews, pastes, runs `npm run build` + manual API test, commits. Activation energy = ~30 min.

Precedent: run 68 em-dash one-liner (ffefe61) worked because copy-paste was zero friction. Same principle applied at feature scale.

---

## Invariants Applied (Pre-verified)

- `client_id` not `tenant_id` on `sms_opt_outs` (matches migration 160)
- No `from __future__ import annotations` in any FastAPI file
- Phone numbers masked to last 4 digits in all API responses
- Uses `_get_current_tenant` dependency (existing auth pattern)
- `request` utility from `frontend/src/utils/api/_client.js` (existing pattern)
- Dark theme, flat, no gradients, no emoji in UI chrome (frontend-patterns.md)

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `backend/routers/sms_compliance.py` |
| MODIFY | `backend/main.py` (2 lines — import + include_router) |
| CREATE | `frontend/src/pages/SmsCompliance.jsx` |
| MODIFY | `frontend/src/components/App.jsx` (3 lines — lazy import + pages entry + PAGE_TO_PATH entry) |
| MODIFY | `frontend/src/components/Sidebar.jsx` (1 nav entry) |

No migration needed — `sms_opt_outs` table already exists (migration 160, applied).

---

## 1. CREATE `backend/routers/sms_compliance.py`

```python
"""SMS compliance dashboard — view and manage opt-outs."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.sms_compliance import last10, record_opt_out, record_opt_in

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sms-compliance", tags=["sms-compliance"])


class OptOutRow(BaseModel):
    id: str
    phone_masked: str
    source: str | None
    created_at: str


class OptOutListResponse(BaseModel):
    items: list[OptOutRow]
    total: int


class ManualOptOutRequest(BaseModel):
    phone: str


class ManualOptInRequest(BaseModel):
    phone: str


@router.get("/opt-outs", response_model=OptOutListResponse)
async def list_opt_outs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    claims: dict = Depends(_get_current_tenant),
):
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    offset = (page - 1) * per_page
    result = (
        db.table("sms_opt_outs")
        .select("id, phone_last10, source, created_at", count="exact")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )

    items = []
    for row in result.data or []:
        p = row.get("phone_last10", "")
        items.append(
            OptOutRow(
                id=row["id"],
                phone_masked=f"***-***-{p[-4:]}" if len(p) >= 4 else "****",
                source=row.get("source"),
                created_at=row.get("created_at", ""),
            )
        )

    return OptOutListResponse(items=items, total=result.count or 0)


@router.get("/stats")
async def opt_out_stats(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    result = (
        db.table("sms_opt_outs")
        .select("id", count="exact")
        .eq("client_id", client_id)
        .execute()
    )
    total_opt_outs = result.count or 0

    return {"total_opt_outs": total_opt_outs}


@router.post("/opt-out")
async def manual_opt_out(
    req: ManualOptOutRequest,
    claims: dict = Depends(_get_current_tenant),
):
    client_id = claims["tenant_id"]
    p = last10(req.phone)
    if not p:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    db = get_service_supabase()
    record_opt_out(db, client_id, req.phone, source="manual_dashboard")
    return {"success": True, "detail": "Opt-out recorded"}


@router.post("/opt-in")
async def manual_opt_in(
    req: ManualOptInRequest,
    claims: dict = Depends(_get_current_tenant),
):
    client_id = claims["tenant_id"]
    p = last10(req.phone)
    if not p:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    db = get_service_supabase()
    record_opt_in(db, client_id, req.phone)
    return {"success": True, "detail": "Opt-in recorded (opt-out removed)"}
```

---

## 2. MODIFY `backend/main.py`

**Line ~84 — add import alongside existing sms import:**
```python
    sms_compliance as sms_compliance_router,
```
*(in the same import block as `sms` — look for `from backend.routers import` block)*

**After `app.include_router(sms.router)` (line ~877):**
```python
app.include_router(sms_compliance_router.router)
```

---

## 3. CREATE `frontend/src/pages/SmsCompliance.jsx`

```jsx
import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { request } from "../utils/api/_client";

export default function SmsCompliance() {
  const { token } = useAuth();
  const [stats, setStats] = useState(null);
  const [optOuts, setOptOuts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [manualPhone, setManualPhone] = useState("");
  const [actionMsg, setActionMsg] = useState(null);

  const PER_PAGE = 50;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [statsData, listData] = await Promise.all([
        request("/api/v1/sms-compliance/stats", { token }),
        request(`/api/v1/sms-compliance/opt-outs?page=${page}&per_page=${PER_PAGE}`, { token }),
      ]);
      setStats(statsData);
      setOptOuts(listData.items);
      setTotal(listData.total);
    } catch (e) {
      setError(e.message || "Failed to load compliance data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [page]);

  async function handleOptOut() {
    if (!manualPhone.trim()) return;
    try {
      await request("/api/v1/sms-compliance/opt-out", {
        method: "POST",
        token,
        body: { phone: manualPhone.trim() },
      });
      setActionMsg(`Opt-out recorded for ${manualPhone}`);
      setManualPhone("");
      load();
    } catch (e) {
      setActionMsg(`Error: ${e.message}`);
    }
  }

  async function handleOptIn() {
    if (!manualPhone.trim()) return;
    try {
      await request("/api/v1/sms-compliance/opt-in", {
        method: "POST",
        token,
        body: { phone: manualPhone.trim() },
      });
      setActionMsg(`Opt-in recorded (opt-out removed) for ${manualPhone}`);
      setManualPhone("");
      load();
    } catch (e) {
      setActionMsg(`Error: ${e.message}`);
    }
  }

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div style={{ padding: "24px", maxWidth: 900, color: "var(--text)" }}>
      <h1 style={{ marginBottom: 4 }}>SMS Compliance</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: 24 }}>
        TCPA opt-out ledger. Every number here is suppressed from all outbound SMS.
      </p>

      {stats && (
        <div
          style={{
            background: "var(--card-bg)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "16px 20px",
            marginBottom: 24,
            display: "inline-block",
          }}
        >
          <div style={{ fontSize: 28, fontWeight: 700 }}>{stats.total_opt_outs}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Total opt-outs</div>
        </div>
      )}

      <div
        style={{
          background: "var(--card-bg)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "16px 20px",
          marginBottom: 24,
        }}
      >
        <h3 style={{ marginTop: 0, marginBottom: 12 }}>Manual override</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input
            type="tel"
            placeholder="Phone number"
            value={manualPhone}
            onChange={(e) => setManualPhone(e.target.value)}
            style={{
              background: "var(--input-bg, #1a1a2e)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "8px 12px",
              color: "var(--text)",
              width: 200,
            }}
          />
          <button
            onClick={handleOptOut}
            style={{
              background: "var(--danger, #c0392b)",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "8px 16px",
              cursor: "pointer",
            }}
          >
            Record opt-out
          </button>
          <button
            onClick={handleOptIn}
            style={{
              background: "var(--accent)",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "8px 16px",
              cursor: "pointer",
            }}
          >
            Remove opt-out
          </button>
        </div>
        {actionMsg && (
          <div style={{ marginTop: 8, fontSize: 13, color: "var(--text-muted)" }}>
            {actionMsg}
          </div>
        )}
      </div>

      {loading && <p style={{ color: "var(--text-muted)" }}>Loading…</p>}
      {error && <p style={{ color: "var(--danger, #c0392b)" }}>{error}</p>}

      {!loading && !error && (
        <>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)" }}>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>Phone</th>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>Source</th>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>Recorded</th>
              </tr>
            </thead>
            <tbody>
              {optOuts.length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ padding: "24px 12px", color: "var(--text-muted)" }}>
                    No opt-outs recorded. Contacts who reply STOP will appear here automatically.
                  </td>
                </tr>
              ) : (
                optOuts.map((row) => (
                  <tr key={row.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 12px", fontFamily: "monospace" }}>
                      {row.phone_masked}
                    </td>
                    <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>
                      {row.source || "—"}
                    </td>
                    <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>
                      {new Date(row.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div style={{ display: "flex", gap: 8, marginTop: 16, alignItems: "center" }}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{
                  padding: "6px 12px",
                  background: "var(--card-bg)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  color: "var(--text)",
                  cursor: page === 1 ? "default" : "pointer",
                  opacity: page === 1 ? 0.4 : 1,
                }}
              >
                Prev
              </button>
              <span style={{ color: "var(--text-muted)", fontSize: 13 }}>
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                style={{
                  padding: "6px 12px",
                  background: "var(--card-bg)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  color: "var(--text)",
                  cursor: page === totalPages ? "default" : "pointer",
                  opacity: page === totalPages ? 0.4 : 1,
                }}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

---

## 4. MODIFY `frontend/src/components/App.jsx`

**After line 112 (`const ReferralPage = lazy(...)`):**
```jsx
const SmsCompliancePage = lazy(() => import("../pages/SmsCompliance"));
```

**In `const pages = { ... }` block, after `referral: ReferralPage,`:**
```jsx
  sms_compliance: SmsCompliancePage,
```

**In `const PAGE_TO_PATH = { ... }` block, after `referral: "/dashboard/referral",`:**
```jsx
  sms_compliance: "/dashboard/sms-compliance",
```

---

## 5. MODIFY `frontend/src/components/Sidebar.jsx`

Find the settings/integrations nav group and add after the "Integrations" entry (or in the compliance/settings section):

```jsx
{ key: "sms_compliance", label: "SMS Compliance", icon: "M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" },
```

Place it near "Automation Rules" or "Settings" — wherever SMS-adjacent nav items live.

---

## Human Execution Steps (30 min)

1. Paste `backend/routers/sms_compliance.py` (copy block above)
2. Edit `backend/main.py` — add import + include_router (2 lines, see §2)
3. Paste `frontend/src/pages/SmsCompliance.jsx` (copy block above)
4. Edit `frontend/src/components/App.jsx` — 3 additions (see §4)
5. Edit `frontend/src/components/Sidebar.jsx` — 1 nav entry (see §5)
6. Run `cd frontend && npm run build` — confirm zero errors
7. Test endpoint: `curl -H "Authorization: Bearer <token>" https://localhost:8000/api/v1/sms-compliance/stats`
8. Navigate to `/dashboard/sms-compliance` — confirm table loads
9. Commit: `feat: add SMS compliance dashboard (run 73/74 winner)`

---

## Run 75 Mandate

If still not shipped after run 75: de-scope to backend endpoint only. Drop `SmsCompliance.jsx` and App.jsx/Sidebar edits. Ship the API alone — unblocks future integrations and clears the active_direction.

---

## Evidence Digest (Run 74)

- `backend/routers/sms_compliance.py` MISSING (10+ days after run 73)
- `frontend/src/pages/SmsCompliance.jsx` MISSING
- `knowledge-base/log.md` last entry 2026-05-05 (56 days stale — cron not firing)
- `check_project_invariants.py` exits 1 (widget drift only — human-only, retired topic)
- Moratorium active, true_pending ~4
- Zero production code commits 3+ days (morning digest)
- Idea 3 (Zapier plan_status) killed — moratorium
- Idea 4 (AI-Human Handoff) parked — moratorium + M effort
- Idea 5 (Home.jsx split) parked — post-SMS-ships

---

## Bonus Action (run independently after commit)

Run `crontab -l` to check if KB autopopulate cron is registered. If missing:
```
0 6,18 * * * bash /home/user/agentnexlify/scripts/daily/kb-autopopulate.sh >> /home/user/agentnexlify/knowledge-base/log.md 2>&1
```
Add it, then run `bash scripts/daily/kb-autopopulate.sh` manually to close the 56-day gap.
