# Debate Log — Run 59 (2026-06-17)

Top 3 ideas ranked by urgency + leverage: Idea 1 (webhook bug), Idea 3 (AI handoff), Idea 4 (widget split).

---

## Idea 1: Fix GH #308 — Webhook Idempotency Retry-Drop Bug

### Round 1

**CHALLENGE:** How often does a Stripe webhook handler fail? If handlers are reliable (<0.1% failure rate), this is theoretical risk from a system that's worked fine for months. Is this high enough priority over items pending 60+ days?

**DEFEND:** The failure mode is real, not theoretical. PR #301 (47c7f8b, 3 days ago) shipped dunning recovery — `_handle_payment_succeeded` now recovers paused tenants. This handler calls Supabase to update `plan_status`. Any transient DB error (connection pool exhaustion under load, Supabase cold start) causes a 500 → Stripe retries → retry silently dropped. Tenant stays paused despite successful payment. The older items (60+ days) are M-effort human work; this is an S-effort autonomous fix.

### Round 2

**CHALLENGE:** The fix — changing `if not is_new` to `if not is_new and _cached is not None` — adds a new code path: "key exists but no cached response." What does this mean for concurrent redeliveries? Two simultaneous redeliveries could both see `_cached is None` and both process the event.

**DEFEND:** Concurrent Stripe redeliveries are extremely rare (Stripe sends one at a time, retries are sequential). The existing handlers (`_handle_payment_succeeded`, `_handle_subscription_updated`) are idempotent — setting `plan_status` to the same value twice is safe. The trade-off: occasional double-process (safe) vs. certain event drop (billing damage). Double-process is the right failure mode for payment recovery.

### Round 3

**CHALLENGE:** GH #308 was filed by the nightly review today. Has there been time to validate this is actually happening in production vs. a theoretical code review finding?

**DEFEND:** The bug is provable by code inspection — the control flow is clear: early-write → exception → no record_response → retry returns 200 without processing. The nightly review's MEDIUM classification is consistent with "real bug class, not yet observed in production." Better to fix before it manifests. The fix is 10 lines in 2 files with zero schema changes — the risk of the fix is negligible vs. the risk of the bug.

**VERDICT: SURVIVES** — real bug, surgical fix, AUTONOMOUS-EXECUTABLE, moratorium-exempt (code defect not new feature), directly relevant to just-shipped payment recovery.

---

## Idea 3: AI-to-Human Handoff v1

### Round 1

**CHALLENGE:** This idea has been recommended 4 times (runs 4, 21, 29, 38) over 62 days without implementation. The governance history shows 4 different framings (sprint, GH issue, Agent OS routing, day-62 escalation) and none triggered action. What new evidence justifies a 5th recommendation?

**DEFEND:** New evidence: Landing redesign (021e245, 3 days ago) repositioned the product as "AI Front Desk / AI Workforce." Handoff is now definitionally part of the core product. Agent OS outbound (os_outbound_mirror.py) is the implementation infrastructure — this was added post-run-38 and makes the scope ~1 day not 3 days.

**COUNTER-CHALLENGE (challenge wins):** The "Agent OS reduces scope" evidence is from run 38 (2026-05-28). That's 20 days ago. If that evidence were actionable it would have triggered implementation by now. The 4-recommendation-without-action pattern is the signal — the bottleneck is NOT information or scope, it's execution capacity (moratorium, M-effort, human required). Adding a 5th recommendation compounds the problem.

### Round 2

**CHALLENGE:** Moratorium still active (~9 human-required pending items, threshold=2). Adding AI-to-Human Handoff makes moratorium worse. And widget_chat.py is 1307L — implementing trigger detection in a 1307L file is high-blast-radius.

**DEFEND:** The moratorium is a governance mechanism for subconscious winners piling up, not a product development ban. This is the most critical customer gap.

**COUNTER-CHALLENGE (challenge wins):** The correct response to moratorium is: recommend implementing an existing pending item (S-effort) OR a moratorium-exempt autonomous fix. Recommending a new M-effort human item when pending count is ~9 is governance violation regardless of product importance.

### Round 3

**CHALLENGE:** Idea 4 (widget_chat split) identifies widget_chat.py at 1307L as a prerequisite risk. Should widget_chat be split before adding handoff trigger detection?

**DEFEND:** Split and handoff could be done in order — split first, then add trigger.

**COUNTER-CHALLENGE (challenge wins):** Correct ordering: split (run 60) → handoff (run 61+). Not this run.

**VERDICT: WEAKENED → parking lot.** Promote to winner in first run AFTER widget_chat split. Block: Idea 4 prerequisite not yet done. Do not re-recommend as standalone winner until moratorium pending ≤ 5 AND widget_chat split complete.

---

## Idea 4: widget_chat.py Split (1307L)

### Round 1

**CHALLENGE:** email_sequences.py split (runs 35/41) is the same idea applied to a 1143L file. It's been pending_approval for 20+ days without execution. What makes widget_chat different?

**DEFEND:** widget_chat.py is the LARGEST file (1307L vs 1143L), touches the most-active code path (widget), and is a prerequisite for AI-to-Human Handoff. email_sequences split sits in a lower-traffic path.

**COUNTER-CHALLENGE (challenge wins):** The activation energy problem is identical. /god-class-splitter exists, email split pending 20+ days, same tool. Pattern predicts same outcome: recommendation without implementation.

### Round 2

**CHALLENGE:** Three PRs touched the widget ecosystem in the last 3 days (#254, #301, #307). Active PR traffic is the WORST time to split a file — immediate merge conflicts.

**DEFEND:** PR activity will continue forever if we wait for a quiet window. But high-frequency files need splitting more, not less.

**COUNTER-CHALLENGE (challenge wins):** "High-frequency = needs splitting more" is correct in principle but wrong for timing. Merge conflicts on a 1307L file split during active development would cost more than the split saves in the short term. Right idea, wrong timing.

### Round 3

**CHALLENGE:** This is M-effort, human-required. Adding to pending worsens moratorium (currently ~9 pending).

**DEFEND:** It's a prerequisite for the oldest pending item (AI-to-Human Handoff). Doing it unlocks Idea 3.

**COUNTER-CHALLENGE (challenge wins):** Prerequisite logic works when prerequisites are achievable. If widget_chat split takes as long as email split (20+ days pending), AI-to-Human Handoff is pushed to 80+ days. Invalid chain.

**VERDICT: WEAKENED → parking lot.** Promote to winner when: (a) PR rate on widget ecosystem drops below 1 PR/week, (b) email_sequences split completes as proof-of-mechanism. Add parking lot note: `block: email_sequences split first as mechanism proof`.

---

## Winner Selection

| Idea | Verdict |
|------|---------|
| 1: GH #308 webhook idempotency | **SURVIVES → WINNER** |
| 3: AI-to-Human Handoff | WEAKENED → parking lot (block: widget split first) |
| 4: widget_chat.py split | WEAKENED → parking lot (block: email split first) |

Runner-up: Idea 2 (email N+1, GH #112) — valid, but run 41 split pending supersedes; fixing N+1 in a file slated for splitting could be wasted work. Parking lot promoted.

Runner-up: Idea 5 (kb-autopopulate.sh) — valid, ROI 1.8, low urgency. Parking lot.
