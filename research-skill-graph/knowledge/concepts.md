# Concepts

Accumulated definitions, terms, and mental models that span multiple research projects. Each entry should be precise enough that a future research run can cite it directly.

## Format

```
## Term
**Definition:** one-sentence precise definition
**Source:** project or external source
**Seen in:** [[projects/x]], [[projects/y]]
```

---

<!-- entries appended below -->

<!-- from projects/what-is-the-single-highest-leverage-feature-agentn on 2026-04-13 -->
- Value Visibility Coefficient :: The ratio of perceived value to actual value delivered by a product; in agentic SaaS this coefficient is structurally low because agents execute tasks invisibly, making the user experience value as zero even when work is being done
- Health Score Dashboard :: A product feature that surfaces a tenant's engagement metrics, agent output summaries, and risk signals in a single view, enabling both operator self-service awareness and automated churn-prevention triggers
- Time-to-First-Value (TTFV) :: The elapsed time between a new customer's account creation and their first measurable experience of the product's core value; a key predictor of 60- and 90-day churn rates in SMB SaaS
- Involuntary Churn :: Churn caused by payment failure (expired card, failed charge) rather than deliberate cancellation; accounts for an estimated 20–30% of SMB SaaS churn and is addressable through dunning flows rather than product features
- Activation Gate :: A required or strongly incentivized step in onboarding that a user must complete before accessing full product functionality; used to ensure TTFV is achieved before the customer forms a negative first impression
- Net Revenue Retention (NRR) :: The percentage of recurring revenue retained from an existing customer cohort over a period, including expansions and contractions; the primary SaaS health metric for subscription businesses

<!-- from projects/what-is-the-fastest-path-for-agentnexlify-to-hit-1 on 2026-04-13 -->
- Annual Contract Value (ACV) :: The annualized revenue value of a single customer contract; used to model LTV/CAC ratios and set acquisition spend ceilings; distinct from ARR (which is the sum of all ACVs)
- LTV/CAC Ratio :: The ratio of customer lifetime value to customer acquisition cost; minimum viable ratio for sustainable SaaS is 3:1; below 2:1 the business is structurally destroying capital
- Net MRR Growth :: Monthly Recurring Revenue increase calculated as (new MRR + expansion MRR) minus (churned MRR + contraction MRR); the primary operational metric for tracking progress toward ARR targets
- Churn Tax :: The implicit cost of customer attrition on growth efficiency; at 4.7% monthly churn, approximately 44% of MRR is lost annually, requiring that acquisition simply replace lost revenue before generating net growth
- Design-Partner Customer :: An early customer acquired with partial pricing concessions in exchange for deep product feedback and co-development participation; used to validate product-market fit and generate case studies before scaling acquisition
- Agency/Reseller Channel :: A go-to-market motion in which third-party agencies or consultants sell and implement a vendor's product to their own clients; characterized by lower CAC, higher close rates, and lower churn vs. self-serve, but requiring relationship investment and revenue share
- Vertical SaaS :: A software product designed for a specific industry vertical rather than a horizontal use case; historically associated with faster initial ARR growth due to concentrated buyer communities and word-of-mouth within tight industry networks
- AI Vendor Fatigue :: The 2025–2026 phenomenon in which SMB buyers are overwhelmed by competing AI product claims and default to incumbent add-ons rather than net-new vendors; increases CAC and sales cycle length for pure-play AI startups

<!-- from projects/should-agentnexlify-build-sms-deliverability-monit on 2026-04-13 -->
- SMS Deliverability Monitoring :: The operational practice of tracking the end-to-end success rate of SMS messages from send to carrier acknowledgment, including DLR parsing, error code normalization, throughput tracking, and alerting; distinct from SMS transport (which carriers the message) and SMS compliance (whether you had consent to send it)
- Delivery Receipt (DLR) :: A carrier-generated status callback confirming whether an SMS was accepted, delivered, failed, or is in an intermediate state; the primary data source for deliverability monitoring; exposed by Twilio as webhook events
- 10DLC (10-Digit Long Code) :: The standard US business SMS sending format (standard 10-digit phone numbers) subject to A2P (Application-to-Person) registration requirements mandated by US carriers since 2021; non-registered campaigns are filtered at the carrier level
- A2P (Application-to-Person) Messaging :: SMS sent from software applications to individual recipients (as opposed to P2P: person-to-person); subject to carrier registration requirements, throughput limits, and filtering rules distinct from consumer SMS
- The Campaign Registry (TCR) :: The US carrier-mandated centralized registry for A2P 10DLC brand and campaign registration; all business SMS senders in the US must register through TCR or a registered CSP (Campaign Service Provider) like Twilio
- MessagingService (Twilio) :: Twilio's abstraction layer that manages a pool of phone numbers, handles sticky-sender logic (routing messages from the same conversation through the same number), and provides throughput scaling; a transport-layer feature, not a monitoring product
- Phantom Delivery :: The failure mode where a carrier returns a "delivered" DLR but the message never reaches the recipient's handset; undetectable via any standard API; requires test-probe networks to identify
- RCS (Rich Communication Services) :: The successor protocol to SMS; supports read receipts, typing indicators, rich media, and verified sender identities; now supported on Android (Google Messages) and iOS 18+; relevant to SMS channel investment decisions with a 2–5 year horizon
- CSP (Campaign Service Provider) :: A registered entity authorized to submit A2P 10DLC campaign registrations to The Campaign Registry on behalf of brands; Twilio is a CSP; becoming a CSP independently requires multi-month process and significant fees
- TCPA (Telephone Consumer Protection Act) :: US federal law governing commercial SMS and phone communications; violations carry statutory damages of $500–$1,500 per message; the primary legal risk in business SMS, often more material than technical deliverability failures

<!-- from projects/is-gohighlevel-beatable-at-the-widget-layer-for-th on 2026-04-13 -->
- Widget Layer :: The set of customer-facing UI components (booking, chat, review display, forms, payment) that sit between an SMB business and its end customers; distinct from the back-end automation and CRM layer; can be owned by a different vendor than the back-end platform
- Agency-Mediated SMB :: An SMB that does not directly select or manage its own software stack but instead uses tools selected and configured by a third-party marketing agency; creates a two-buyer dynamic where the agency is the economic buyer and the SMB is the end user
- FSM Platform (Field Service Management) :: Software category that manages the operational workflow of field service businesses: job scheduling, dispatch, technician routing, invoicing, and customer history; examples include Jobber, ServiceTitan, Housecall Pro; distinct from CRM/marketing-focused platforms like GHL
- Middleware-to-Primary-Interface Model :: A product growth pattern in which a tool begins as an integration/complement between two incumbent platforms, establishes daily workflow habit with end users, and then expands to become the primary interface through which users interact with both underlying platforms; analogous to how Intercom became primary customer communication interface while Zendesk remained the back-end
- Agency Channel Conflict :: The situation in which a software vendor's product is perceived by its agency distribution partners as competitive with, rather than complementary to, the agency's existing platform investment; triggers agency resistance to adoption even when the product has superior end-user quality
- Beachhead Widget :: A single, high-value, frequently-used widget function chosen as the initial product focus for a widget-layer competitor; should be the function where the incumbent is weakest, the contractor's daily use is highest, and the switching cost to adopt the new widget is lowest; analogous to the "landing zone" concept in enterprise sales
- FSM Integration Depth :: The degree to which a widget layer product is integrated with an FSM platform's job data (job type, technician assignment, invoice amount, customer history); determines the quality ceiling for booking, chat, and review widgets that benefit from knowing real-time job context
- GHL SaaS Mode :: GoHighLevel's $497/mo tier that enables agencies to white-label GHL and resell sub-accounts to clients; the economic model through which agencies capture 2–5× markup on GHL's cost; the primary mechanism for GHL's agency channel lock-in
