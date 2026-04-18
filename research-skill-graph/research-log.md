# Research Log

Chronological log of every research project run through the graph. Each entry links to its project folder and captures headline findings. The 10th project doesn't start from zero — it starts from everything already learned here.

## Format

```
## YYYY-MM-DD — Project Slug

**Question:** [original question from queue]
**Depth:** quick | standard | deep
**Folder:** [[projects/slug]]
**Model:** claude-sonnet-4-6

### Headline findings
- finding 1
- finding 2
- finding 3

### Strongest tension
[one sentence on the most interesting contradiction between lenses]

### Connects to
- [[projects/prior-slug]] — why they connect
```

---

<!-- entries appended below -->

## 2026-04-13 — what-is-the-single-highest-leverage-feature-agentn

**Question:** What is the single highest-leverage feature AgentNexLiFy could ship this quarter to reduce churn for SMB tenants?
**Depth:** quick
**Folder:** [[projects/what-is-the-single-highest-leverage-feature-agentn]]
**Model:** claude-sonnet-4-6

### Headline
**The single highest-leverage feature AgentNexLiFy should ship this quarter to reduce SMB churn is a proactive Health Score Dashboard with automated intervention triggers — essentially making the product's own value visible to the operator before they decide to cancel.**
**What the research shows:**
SMB SaaS churn is structurally different from enterprise churn. The dominant driver is not price, c

---

## 2026-04-13 — what-is-the-fastest-path-for-agentnexlify-to-hit-1

**Question:** What is the fastest path for AgentNexLiFy to hit 1M ARR in 12 months?
**Depth:** quick
**Folder:** [[projects/what-is-the-fastest-path-for-agentnexlify-to-hit-1]]
**Model:** claude-sonnet-4-6

### Headline
**What we learned:** AgentNexLiFy hitting $1M ARR in 12 months is arithmetically achievable but requires near-perfect execution on three interdependent bets: price point selection, channel concentration, and churn control. The fastest path is not "more customers" — it's "fewer, better-monetized customers retained longer."
**The core math:** $1M ARR = $83,333 MRR. At a mid-market price point of $50

---

## 2026-04-13 — should-agentnexlify-build-sms-deliverability-monit

**Question:** Should AgentNexLiFy build SMS deliverability monitoring in-house or outsource to Twilio MessagingService?
**Depth:** quick
**Folder:** [[projects/should-agentnexlify-build-sms-deliverability-monit]]
**Model:** claude-sonnet-4-6

### Headline
**The question is slightly mis-framed — and the right answer is: buy now, revisit at scale.**
Twilio MessagingService is a managed transport layer, not a deliverability monitoring product. The real build/buy decision is between (a) building a custom monitoring layer on top of Twilio vs. (b) using Twilio Insights, a third-party SMS observability tool, or a lightweight internal webhook logger. That 

---

## 2026-04-13 — is-gohighlevel-beatable-at-the-widget-layer-for-th

**Question:** Is GoHighLevel beatable at the widget layer for the SMB contractor segment?
**Depth:** standard
**Folder:** [[projects/is-gohighlevel-beatable-at-the-widget-layer-for-th]]
**Model:** claude-sonnet-4-6

### Headline
**Is GoHighLevel beatable at the widget layer for the SMB contractor segment? Yes — selectively, conditionally, and with an 18-month window.**
GHL is a $200M+ ARR platform built for marketing agencies, not for field-service contractors. Its widget layer (booking, review, chat, forms) is broad but shallow — optimized for agency setup speed, not for the daily workflow of an HVAC technician, plumber,

---

## 2026-04-14 — what-is-the-true-12-month-cac-and-churn-profile-of

**Question:** What is the true 12-month CAC and churn profile of SMB AI widget products under $500/mo?
**Depth:** standard
**Folder:** [[projects/what-is-the-true-12-month-cac-and-churn-profile-of]]
**Model:** claude-sonnet-4-6

### Headline
**What we learned:** The true 12-month CAC and churn profile of SMB AI widget products under $500/month is substantially worse than published SaaS benchmarks suggest — and the gap is widening as the 2025–2026 AI vendor fatigue cycle matures.
**The core numbers:** Blended CAC for SMB AI widget products in the sub-$500/month tier ranges from **$300–$900** depending on channel mix, with self-serve at

---

## 2026-04-14 — why-do-most-ai-chat-widget-companies-plateau-or-fa

**Question:** Why do most AI chat widget companies plateau or fail in months 6-18?
**Depth:** standard
**Folder:** [[projects/why-do-most-ai-chat-widget-companies-plateau-or-fa]]
**Model:** claude-sonnet-4-6

### Headline
**Why AI chat widget companies plateau or fail in months 6-18: the four-layer trap**
Most AI chat widget companies don't fail because their product stops working. They fail because four structural forces — each manageable alone, but lethal in combination — converge between month 6 and month 18, precisely when founders believe they've survived the early danger zone.
**What the research shows:**
The

---

## 2026-04-14 — what-happens-to-agentnexlify-unit-economics-if-ant

**Question:** What happens to AgentNexLiFy unit economics if Anthropic raises prices 3x in 12 months?
**Depth:** standard
**Folder:** [[projects/what-happens-to-agentnexlify-unit-economics-if-ant]]
**Model:** claude-sonnet-4-6

### Headline
**What happens to AgentNexLiFy unit economics if Anthropic raises prices 3x in 12 months?**
The short answer: a 3× Anthropic price increase is an existential stress test, not a manageable headwind — unless AgentNexLiFy has already built structural insulation it almost certainly does not yet have at its current stage.
**The math is brutal.** Prior research established AgentNexLiFy's gross margin at

---

<<<<<<< HEAD
## 2026-04-17 — should-agentnexlify-vertical-specialize-contractor
=======
## 2026-04-15 — should-agentnexlify-vertical-specialize-contractor
>>>>>>> 6662e74 (research: should-agentnexlify-vertical-specialize-contractor)

**Question:** Should AgentNexLiFy vertical-specialize (contractors only) or stay horizontal across SMBs?
**Depth:** deep
**Folder:** [[projects/should-agentnexlify-vertical-specialize-contractor]]
**Model:** claude-sonnet-4-6

### Headline
<<<<<<< HEAD
**The question:** Should AgentNexLiFy vertically specialize in contractors only, or stay horizontal across SMBs?
**The answer:** Vertical-specialize into contractors now — with a deliberate re-evaluation gate at $1.5M ARR.
Six research lenses converge on this conclusion with meaningful tension at only one point (the contrarian lens raises a legitimate risk about contractor market ceiling). Here is
=======
**Should AgentNexLiFy vertical-specialize into contractors or stay horizontal across SMBs?**
The research converges on a clear recommendation with one material qualification: **vertical-specialize into contractors, via the agency channel, with a defined 18-month review gate.**
**What 6 lenses found:**
Four of six lenses — Technical, Economic, Historical, and First-Principles — independently point 
>>>>>>> 6662e74 (research: should-agentnexlify-vertical-specialize-contractor)

---
