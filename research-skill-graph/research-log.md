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

## 2026-04-18 — how-have-historical-document-automation-waves-fax-

**Question:** How have historical document-automation waves (fax, email, workflow SaaS) priced and distributed to SMBs, and what applies now?
**Depth:** standard
**Folder:** [[projects/how-have-historical-document-automation-waves-fax-]]
**Model:** claude-sonnet-4-6

### Headline
**What historical document-automation waves teach about pricing and distributing AI tools to SMBs — and what applies now**
Three prior waves of document automation — fax (1984–1995), email/internet (1995–2005), and workflow SaaS (2010–2024) — share a durable pattern: the technology that wins SMBs does so not through direct enterprise-style sales but through **channel embedding, price compression t

---

## 2026-04-18 — what-is-the-real-defensibility-of-a-widget-first-a

**Question:** What is the real defensibility of a widget-first AI product once foundation models become commodity?
**Depth:** deep
**Folder:** [[projects/what-is-the-real-defensibility-of-a-widget-first-a]]
**Model:** claude-sonnet-4-6

### Headline
## What Is the Real Defensibility of a Widget-First AI Product Once Foundation Models Become Commodity?
**The short answer: a widget-first AI product has weak structural defensibility against model commoditization, but the moat is not gone — it has migrated. The question is whether the company has built what survives the migration.**
Foundation model commoditization is not a future risk — it is al

---

## 2026-04-18 — which-smb-verticals-have-the-highest-willingness-t

**Question:** Which SMB verticals have the highest willingness to pay for AI appointment booking and why?
**Depth:** standard
**Folder:** [[projects/which-smb-verticals-have-the-highest-willingness-t]]
**Model:** claude-sonnet-4-6

### Headline
**Which SMB verticals have the highest willingness to pay for AI appointment booking — and why?**
After running six research lenses against available market data, practitioner evidence, and structural analysis, three SMB verticals emerge with reliably high willingness to pay (WTP) for AI appointment booking: **home services/field trades** (HVAC, plumbing, electrical, roofing), **healthcare-adjacen

---

## 2026-04-18 — what-regulatory-risks-tcpa-state-ai-laws-can-spam-

**Question:** What regulatory risks (TCPA, state AI laws, CAN-SPAM) most threaten AgentNexLiFy's outbound automation?
**Depth:** standard
**Folder:** [[projects/what-regulatory-risks-tcpa-state-ai-laws-can-spam-]]
**Model:** claude-sonnet-4-6

### Headline
**What We Learned**
AgentNexLiFy's outbound automation faces three distinct but converging regulatory threat vectors — TCPA, a patchwork of state AI/privacy laws, and CAN-SPAM — that collectively create existential liability exposure if not structurally addressed in the next 6–12 months.
**The TCPA is the dominant near-term threat.** The 2024–2025 FCC rule changes (effective January 27, 2025) elim

---

## 2026-04-19 — is-white-label-reseller-distribution-gohighlevel-m

**Question:** Is white-label reseller distribution (GoHighLevel model) a viable growth lever for AgentNexLiFy?
**Depth:** standard
**Folder:** [[projects/is-white-label-reseller-distribution-gohighlevel-m]]
**Model:** claude-sonnet-4-6

### Headline
**Is white-label reseller distribution (GoHighLevel model) a viable growth lever for AgentNexLiFy?**
**The short answer: viable in architecture, premature in execution — with a conditional path to readiness in 6–9 months.**
The GoHighLevel reseller model is one of the most capital-efficient distribution mechanisms in SMB SaaS history. GHL grew from zero to $200M+ ARR in roughly six years with near

---

## 2026-04-20 — what-is-agentnexlify-s-current-telemetry-coverage-

**Question:** What is AgentNexLiFy's current telemetry coverage? Are agent task completions, session data, and workflow activations already logged at the tenant level — or does a Health Score Dashboard require backend instrumentation work first?
**Depth:** standard
**Folder:** [[projects/what-is-agentnexlify-s-current-telemetry-coverage-]]
**Model:** claude-sonnet-4-6

### Headline
## What Did We Learn?
The prior research log establishes that AgentNexLiFy is an early-stage agentic SaaS platform targeting SMB tenants, with known churn problems driven by low value visibility — and a previously recommended Health Score Dashboard as the highest-leverage churn intervention. This research attempts to answer whether that dashboard can be built from existing telemetry or requires ne

---

## 2026-04-20 — is-the-smb-segment-primarily-self-serve-no-sales-c

**Question:** Is the SMB segment primarily self-serve (no sales/CS touch) or sales-assisted? This determines whether the intervention channel should be in-product, automated email, or CSM alert.
**Depth:** standard
**Folder:** [[projects/is-the-smb-segment-primarily-self-serve-no-sales-c]]
**Model:** claude-sonnet-4-6

### Headline
**The SMB segment is not primarily self-serve OR sales-assisted — it is a bimodal distribution that most companies misread as a single segment, and that misreading is the root cause of mis-channeled interventions.**
**What the research shows:**
The SMB label covers two structurally different buyer types that behave like different segments:
1. **"Small" SMB (1–20 employees, sub-$200/month ACV):** A

---

## 2026-04-20 — what-does-the-actual-agentnexlify-churn-data-show-

**Question:** What does the actual AgentNexLiFy churn data show — is the dominant churn signal engagement decay (supporting the dashboard recommendation) or stated product-fit complaints (supporting a different roadmap priority)?
**Depth:** standard
**Folder:** [[projects/what-does-the-actual-agentnexlify-churn-data-show-]]
**Model:** claude-sonnet-4-6

### Headline
**The question cannot be definitively answered with external data alone — but the weight of evidence strongly favors engagement decay as the dominant churn signal, while product-fit complaints likely function as a rationalization layer rather than a root cause.**
**What the prior research log establishes (compound mode):** Two prior projects are directly load-bearing here. The 2026-04-13 highest-l

---
