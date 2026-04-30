# Run 9 Ideas — 2026-04-27

## Evidence Summary

**22+ commits in 3 days.** Idempotency service (migrations 114-116), rate-limit middleware, fraud guard, auth-helpers refactor (34 routers), contextual reindex script, cost-optimization rules. Two PRs merged via feature/steal-list-1-6.

**5 new issues from nightly reviews:**
- #93 HIGH: fraud_guard.py pauses coupon/trial users (`payment_status != "paid"` catches `no_payment_required`)
- #94 MEDIUM: IndexError crash on empty `charges.data` in fraud_guard.py — 500 on Stripe retries
- #97 MEDIUM: widget_chat.py:295 bare `except Exception: plan = "free"` — paid tenants silently rate-limited at free tier, zero logs
- #98 MEDIUM: O(N) full table scan in twilio_webhooks.py:69 — in-Python phone normalization across ≤50 tenants, silently drops >50
- #99 MEDIUM: Stripe `except (SignatureVerificationError, Exception)` collapses to `except Exception` — bad signatures may return 500

**KEY GOVERNANCE FIX FOUND:** `AnalyticsPage.jsx` has full Lead Source Analytics (fetchLeadSources, BarChart with per-source colors). Run 2 winner is already implemented. Governance shows it as "pending" — this run corrects that. Real pending count: 4 (runs 3, 4, 7, 8).

**Moratorium:** Active. 4 pending_approval items. Lift condition: ≤3 (need 1 implementation). No items implemented since run 8 triggered moratorium.

**Unwired scripts:** `check_project_invariants.py` exists but not wired. `check-widget-sync.sh` never created.

---

## Idea 1: JS + Python Silent Catch Guard (Run 3 escalation)

**Evidence:** Run 3 winner (2026-04-11, 16+ days pending). JS violations confirmed: `MarketingDashboardPage.jsx:96` `.catch(() => null)`. Python equivalent now live: `widget_chat.py:295` bare `except Exception: plan = "free"` — issue #97 explicitly deferred by developer. Pre-commit hook blocks Python bare-except (`except:`) but not empty-body `except Exception:` with no log, and zero JS catch coverage.

**Action:** (a) Add Check 9 to `scripts/hooks/pre-commit` blocking JS files with `.catch(() => null)` or `.catch(() => {})` patterns. (b) Add `logger.warning("_chat_rate_limit fallback to free tier for key=%s: %s", key, exc)` to `widget_chat.py:295` except block.

**Impact:** Paid tenants silently downgraded to free rate-limit tier stop happening silently. JS swallowed errors surface in tests. Pre-commit prevents new silent catches from landing.

**Category:** code_health

---

## Idea 2: Fix Billing Bugs #93 + #94

**Evidence:** `fraud_guard.py` introduced in `164d21b` (2026-04-25). Issue #93 HIGH: `payment_status != "paid"` check at line 121-123 also catches `no_payment_required`, pausing coupon/trial signups. Issue #94 MEDIUM: `(charges_data[0])` at lines 135-147 crashes with IndexError when `data = []` — outside try/except, propagates 500 to Stripe webhook handler.

**Action:** Line 121-123: return `None` early when `payment_status == "no_payment_required"`. Lines 135-147: guard indexing with `charges_data[0] if charges_data else {}` pattern.

**Impact:** Stops legitimate coupon users being blocked. Stops 500 crash on Stripe retries. Both 2-line fixes in same function cluster.

**Category:** code_health / customer_value

---

## Idea 3: Widget 3-Copy Sync Guard (Run 7 escalation)

**Evidence:** Run 7 winner (2026-04-24, 3+ days). `scripts/check-widget-sync.sh` never created. Three widget copies: `widget/agentnexlify-widget.js`, `frontend/public/widget/agentnexlify-widget.js`, `landing-page-v2/widget/`. CLAUDE.md Invariant #4 says "must stay byte-identical" — currently unguarded in CI and pre-push.

**Action:** Create `scripts/check-widget-sync.sh` comparing MD5 hashes of all 3 copies. Wire as pre-push check. CLAUDE.md update: "3 copies (not 2)" clarification.

**Impact:** Prevents tenant embed breaks from out-of-sync widget JS. S-effort. Zero deps.

**Category:** code_health

---

## Idea 4: Wire check_project_invariants.py into pre-commit (Run 8 escalation)

**Evidence:** Run 8 winner (2026-04-25, 2 days). Script at `scripts/check_project_invariants.py` — stdlib-only, designed for CI. Pre-commit hook (232 lines) has Python checks but no call to invariants script. 3+ production bugs from `tenant_id`/`client_id` confusion per CLAUDE.md.

**Action:** Append call to `scripts/check_project_invariants.py` in `scripts/hooks/pre-commit` after existing Python checks.

**Impact:** Blocks naming-invariant violations at commit time. S-effort, zero new infrastructure.

**Category:** code_health

---

## Idea 5: Fix Stripe SignatureVerificationError catch (Issue #99)

**Evidence:** `backend/routers/stripe_webhooks.py ~line 46`. `except (stripe.SignatureVerificationError, Exception)` — since `SignatureVerificationError` subclasses `Exception`, the union collapses to `except Exception`. The specific branch (`if "SignatureVerification" in type(exc).__name__`) never fires. Bad webhook signatures return 500 instead of 400. Filed as issue #99 in nightly review 2026-04-27.

**Action:** Split into ordered except clauses: `except stripe.SignatureVerificationError:` first, then `except Exception:`. Add unit test asserting 400 on bad sig.

**Impact:** Correct HTTP response codes for invalid webhook signatures. Prevents Stripe retry storm on 500s.

**Category:** code_health / operational
