# Run 91 Winning Concept — 2026-07-13

## Winner: Pre-Answer GH #413 Referral Checklist Items 3/5/8 from Code

### Why This Won
GH #413 (Referral reward activation) has been open 2 days with zero human engagement after run 90's comment. The issue has 5 remaining UX checklist items blocking the human from flipping REFERRAL_REWARD_ENABLED=1. Three of those items are directly answered by `backend/services/referral_reward.py`, which was audited this session. Cost to post: zero. Impact: reduces human checklist burden by 60%, from 5 items to 2.

This is the highest-leverage autonomous action available: the subconscious already has the answer, the human already has the task, and bridging that gap is exactly what this loop is for.

### Code Evidence (from referral_reward.py, confirmed this session)

**Item 3 — What is the reward redemption path? How does the $20 reach the referrer?**
Answer: Stripe Customer Balance Transaction. `stripe.Customer.create_balance_transaction(customer.id, amount=-2000, currency="usd")` — a negative balance auto-deducts from the referrer's next invoice. The referrer never receives a direct payout; it silently reduces what they owe. Source: `referral_reward.py:212-225`, `_grant_sync()`.

**Item 5 — What prevents self-referral abuse?**
Answer: Built into `_resolve_referrer()`. Both promo-code and widget-watermark channels check `if referrer_tenant_id == str(referred_tenant_id): return None`. No separate validation needed — the attribution resolution function makes self-referrals impossible. Source: `referral_reward.py:75-104`.

**Item 8 — When does the referral qualify? Is there a waiting period?**
Answer: First paid invoice = the trigger. The module docstring states: "Fires when a tenant pays their FIRST invoice (subscription activation)." Stripe webhooks deliver this event; idempotency is guaranteed by `UNIQUE(referred_tenant_id)` in the `referral_rewards` table. No additional waiting period. Source: `referral_reward.py:9-10`, docstring.

### Implementation
Post comment on GH #413 via `mcp__github__add_issue_comment`. Comment summarizes answers to items 3, 5, 8 with code citations. Explicitly marks those items as code-verified so the human knows they don't need to research them.

### Confidence: HIGH
Code is the authoritative source. Answers are literal reads from the file. No inference required.

### Expected Impact
Human checklist goes from 5 open items to 2 (items 9 and 10 remain: user-facing copy and email notifications). Reduces activation work from "needs investigation" to "two concrete tasks." Increases probability human flips REFERRAL_REWARD_ENABLED=1 within 24-48h.

### Bonus A: Keys Koffee Dedicated GH Issue
Day 20 post-launch. Governance mandate: escalate at Day 21. File separate focused issue: "Keys Koffee: add business hours to booking config to enable bookings." Labels: human-action-required, revenue. Estimated fix: 5 minutes. Distinct from general diagnostic GH #412.
