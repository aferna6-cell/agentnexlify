# Customer Gaps — Consolidated Findings

Gaps discovered across all customer simulations. Prioritized by cross-industry impact.

## Resolved Gaps (Closed by Build Loop)

| Gap | Simulations | Cycle |
|-----|-------------|-------|
| Emergency/urgency detection | Plumber | 107 |
| Business hours in onboarding | Plumber | 108 |
| Service type booking | Plumber, Dental, Salon | 125 |
| Dental-aware reminders | Dental | 117 |
| Rebook automation (42-180 day) | Dental, Salon | 117 |
| Patient intake form preset | Dental | 118 |
| HIPAA-aware AI | Dental, Medical | 118 |
| Insurance fields on leads | Dental, Medical | 119 |
| Industry pipeline presets | All (6 types) | 121, 124 |
| Webhook schema complete | All | 122 |
| Lead source tracking | All | 122 |
| AI conversation summary | All | 123 |
| Birthday automation | Salon | 129 |
| Legal intake form preset | Lawyer | 132 |
| FAQ consistency (≥5 per type) | All | 132 |
| Lead source analytics | All | Cycle 2 (run 2, AnalyticsPage.jsx BarChart by source) |

## Open Gaps — Cross-Industry (High Priority)

| Gap | Simulations | Impact | Effort |
|-----|-------------|--------|--------|
| **AI-to-human handoff** | All | Critical for complex queries | Medium |
| **Custom automation templates** | All | Custom birthday messages, post-service follow-ups | Medium |

## Open Gaps — Industry-Specific

### Real Estate
| Gap | Impact | Effort |
|-----|--------|--------|
| Buyer qualification AI (budget, pre-approval) | High | Medium |
| Property-level tracking in appointments | High | High |
| Post-showing follow-up template | Medium | Low |
| MLS integration | Low | Very High (external API) |

### Dental / Medical
| Gap | Impact | Effort |
|-----|--------|--------|
| Provider-specific availability | Medium | High |
| Post-appointment care instructions | Medium | Low |
| Treatment plan tracking | Medium | High |

### Salon
| Gap | Impact | Effort |
|-----|--------|--------|
| Waitlist for fully booked days | Medium | Medium |
| Before/after photo gallery | Low | Medium |
| Tipping integration | Low | Medium |

### Lawyer
| Gap | Impact | Effort |
|-----|--------|--------|
| Conflict check (opposing party lookup) | High | Medium |
| Billable hours tracking | Medium | High |
| Retainer balance tracking | Medium | Medium |
| Matter/case number generation | Low | Low |

### Fitness
| Gap | Impact | Effort |
|-----|--------|--------|
| Class schedule integration | Medium | High |
| Member retention tracking (30-day inactive alert) | Medium | Medium |
| Trial-to-member conversion tracking | Medium | Low |

### Restaurant
| Gap | Impact | Effort |
|-----|--------|--------|
| Table/reservation management (not just time slots) | Medium | High |
| Post-dining aftercare ("Thank you, leave a review") | Low | Low |
| POS integration | Low | Very High (external API) |

## Product-Market Fit by Industry

| Industry | Fit Score | Key Strength | Missing Piece |
|----------|-----------|--------------|---------------|
| Salon/Spa | 9/10 | Service types + rebook + reminders | Waitlist |
| Plumber/HVAC | 8/10 | Emergency detection + bids + invoices | Before/after photos |
| Dental | 8/10 | Intake forms + insurance + HIPAA AI | Provider scheduling |
| Restaurant | 8/10 | Menu + orders + chat ordering | POS integration |
| Fitness | 7/10 | Waiver form + rebook + pipeline | Class scheduling |
| Lawyer | 7/10 | Intake forms + documents + pipeline | Billable hours |
| Real Estate | 6/10 | Pipeline + documents | Property tracking |

_Updated: 2026-03-22. Review after each new simulation._
