---
title: AI in Dentistry — What Are the HIPAA Violation Risks?
date: 2025-08-27
source_url: https://www.cda.org/newsroom/endorsed-services/ai-in-dentistry-what-are-the-hipaa-violation-risks/
fetched_at: 2026-08-26
category: verticals
tags: [dental, hipaa, phi, business-associate-agreement, baa, ai-vendor, compliance, checklist]
---

# AI in Dentistry: What Are the HIPAA Violation Risks?

*California Dental Association. Aug 27, 2025.*

## Core points

- There is **no AI-specific healthcare law**; HIPAA applies to AI exactly as to any other technology that touches protected health information (PHI).
- An AI vendor that receives, stores, or processes PHI on a practice's behalf is a **business associate** → a signed **Business Associate Agreement (BAA)** is required *before* use. Avoid any vendor that refuses to sign one.
- Free public ChatGPT is **not safe** for PHI — inputs may be used to train the model and there is no BAA. OpenAI offers a BAA for paid API customers under specific terms.
- Apply **de-identification** and the **minimum-necessary** standard: strip identifiers before sending text to an AI where possible.
- A clinician must **review AI outputs**; AI does not shift liability.
- HHS OCR guidance on AI is anticipated; until then, existing Privacy and Security Rules govern.

## Pre-adoption checklist

1. Review the vendor's technical and administrative safeguards.
2. Verify the vendor's HIPAA policies and breach-notification procedures.
3. Analyze the intended use — treatment, payment, operations, research, or **marketing** (marketing use generally needs patient authorization).
4. Obtain patient authorization when the use falls outside TPO.
5. Sign the BAA before deployment.

## Notes for AgentNexLiFy

- Dental tenants using our widget: appointment requests with name + phone + reason for visit are PHI once linked to the practice. We are a business associate → we need a BAA template and Anthropic's BAA coverage on the API path (verify current Anthropic BAA eligibility for our account tier).
- Marketing follow-up automations (review requests, promos) to dental patients need authorization handling — different from plumbing.
- Minimum-necessary: don't send full conversation history to the lead-qualifier for dental tenants; pass structured fields only.
- Pairs with `raw/verticals/hipaa-compliant-ai-dental-receptionist-checklist-2026.md`.
