### Idea 2: Activate AI-to-Human Handoff v1 (Explicit Trigger)

**Evidence:**
- customer-gaps.md: Critical rating, all 7 industries affected.
- Run 4 original recommendation (65+ days pending) — oldest active_direction not resolved.
- Both moratorium-override bugs now resolved (GH #308 + GH #292/#293). Context shift: moratorium
  penalty items are gone; product feature work is now unblocked.
- os_outbound_mirror.py handles SMS/email/Facebook (152 tests). Delivery layer exists.
- Scope reduced from ~3 days (pre-Agent OS) to ~1 day (routing + trigger detection).
- GoHighLevel's "AI Employee" feature is the competitor moat. This closes the key gap.

**Action:**
1. Add explicit trigger detection in `widget_chat.py` (phrases like "speak to a human", "real person")
2. Write to `handoff_requests` table (or existing `leads` with status = "needs_human")
3. Notify owner via `os_outbound_mirror.send_sms()` / `.send_email()`
4. Set conversation status to "handoff_pending"

**Impact:**
- Closes most critical cross-industry customer gap
- Directly competitive with GoHighLevel AI Employee (our primary competitor)
- Estimated 1–1.5 day human implementation effort

**Category:** customer_value
