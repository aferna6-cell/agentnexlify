# Document Processor Agent — Sales Spec

## One-line Pitch
"Dump invoices, contracts, receipts, or forms in. Get structured data out. No manual entry."

## Problem Solved
Every SMB has SOMEONE doing 5-10 hrs/week of: typing invoice data into QB, filing contracts, coding receipts, transcribing form responses. Repetitive, error-prone, a talent drain.

## Target Customer
- SMB processing 100+ docs/month
- Contractors, legal, accounting, healthcare, real estate, logistics
- Currently using: manual entry, or broken OCR, or Rossum/Docsumo (too expensive)

## Pricing
| Tier | Setup | Monthly | Scope |
|------|-------|---------|-------|
| Basic | $2,000 | $500 | 1 doc type (invoices OR contracts OR receipts) |
| Standard | $3,000 | $500 | 3 doc types + CRM/accounting sync |
| Premium | $4,000 | $500 | 5+ doc types + approval workflow + audit trail |

## Deliverables
- Custom extraction schema per doc type
- Drop zone (email inbox OR Dropbox folder OR webhook endpoint)
- Structured output (JSON, CSV, direct API push to target system)
- Confidence score per field
- Low-confidence queue → human review
- Monthly accuracy report
- Re-training loop from human corrections

## Doc Types Supported
- **Invoices** — vendor, amount, date, line items, PO#, tax, terms
- **Contracts** — parties, effective/termination dates, key clauses, payment terms, auto-renew flag
- **Receipts** — merchant, amount, category, date, expense account
- **Forms** — structured schema match per form type
- **Insurance** — policy #, coverage, premium, renewal date, beneficiary
- **Medical intake** — demographics, history, meds (HIPAA tier available)
- **Real estate** — MLS, appraisal, disclosure, title — field extraction per state template

## Integrations Supported
- Accounting: QuickBooks, Xero, FreshBooks, NetSuite
- CRM: HubSpot, Salesforce, Pipedrive
- Storage: Google Drive, Dropbox, S3
- Email: Gmail, Outlook (as intake channel)
- DB: Supabase, Postgres direct

## Client Requirements
- 50+ sample docs per type (training data)
- Target system schema (where does extracted data go?)
- Confidence threshold (what needs human review?)
- Approval policy (dollar amount thresholds triggering review)

## Setup Timeline
| Day | Milestone |
|-----|-----------|
| 0 | Kickoff + sample docs |
| 1-5 | Schema definition + extraction tuning |
| 6-8 | Target system integration |
| 9-11 | Accuracy testing on 50 docs per type |
| 12-14 | Human-in-loop workflow + audit trail |
| 15 | Launch with 10% human review rate |
| 30 | Drop human review to <2% if accuracy holds |

## Success Metrics
- Extraction accuracy (field-level, target ≥97%)
- End-to-end processing time (target <5 min per doc)
- Cost per doc (target <$0.20)
- Human review rate over time (should drop)
- Processing volume (monthly)

## Why Managed Agent
- Multi-hour session = handles 100-doc batches without context loss
- Approval gates on high-$ extracted amounts
- Vision capability built-in (OCR + layout understanding)
- SOC 2 + HIPAA available
