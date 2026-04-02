# Power Washing Business — Knowledge Base Template

Use this template to quickly configure the AgentNexLiFy AI chatbot for a power washing / pressure washing business. Replace all `[PLACEHOLDER]` values with the actual business information.

The template has three sections:
1. **Knowledge Base** — paste into the widget config `knowledge_base` field
2. **Custom Instructions** — paste into the widget config `custom_instructions` field
3. **FAQ Entries** — create via the dashboard FAQ manager or POST /api/v1/faq/{tenant_id}

---

## 1. Knowledge Base

Copy everything between the START and END markers below into the widget config knowledge base field.

<!-- KB START -->

### About Us

[BUSINESS_NAME] is a professional power washing company serving [SERVICE_AREA] and surrounding communities. We have been in business for [YEARS_IN_BUSINESS] years and have completed over [JOBS_COMPLETED] jobs. Our team is fully licensed and insured.

Owner: [OWNER_NAME]
Phone: [PHONE_NUMBER]
Email: [EMAIL_ADDRESS]
Website: [WEBSITE_URL]

### Services

**Residential Services**

- **House Washing** — Soft wash exterior siding (vinyl, brick, stucco, wood, Hardie board). Removes mold, mildew, algae, dirt, and cobwebs. Safe low-pressure technique that will not damage paint or siding.
- **Driveway & Sidewalk Cleaning** — Surface cleaning for concrete, pavers, asphalt, and stamped concrete. Removes oil stains, tire marks, algae, and ground-in dirt. We use a surface cleaner for even, streak-free results.
- **Deck & Patio Cleaning** — Restore wood, composite, Trex, and stone surfaces. Removes green algae, grime, and weathering. We can also apply sealant after cleaning (ask for pricing).
- **Roof Cleaning** — Soft wash method only (no high pressure on roofs). Removes black streaks (Gloeocapsa magma), moss, lichen, and algae. Safe for asphalt shingles, tile, and metal roofs.
- **Fence Cleaning** — Wood and vinyl fence washing. Removes green buildup, mildew, and weathering.
- **Gutter Cleaning & Brightening** — Clean out debris from inside gutters and wash the exterior face to remove black tiger stripes and oxidation.
- **Concrete Sealing** — After cleaning, we offer concrete sealing to protect driveways, patios, and pool decks from staining and weather damage.

**Commercial Services**

- **Storefront & Building Washing** — Keep your business looking professional. We clean exterior walls, sidewalks, entryways, and awnings.
- **Parking Lot & Garage Cleaning** — Remove oil, gum, and grime from parking areas.
- **Dumpster Pad Cleaning** — Sanitize and deodorize dumpster pads.
- **Fleet Washing** — Wash company vehicles, trucks, trailers, and heavy equipment on-site.
- **Graffiti Removal** — Specialized cleaning to remove graffiti from most surfaces.

### Service Area

We serve [PRIMARY_CITY] and the surrounding areas including [CITY_LIST]. We typically service locations within [RADIUS] miles of [PRIMARY_CITY]. For jobs outside this area, contact us for availability.

### Pricing Guidance

We provide **free, no-obligation estimates** for every job. Pricing depends on the size of the area, the type of surface, the level of buildup, and accessibility.

**Typical price ranges (for reference only — actual quotes may vary):**

| Service | Typical Range |
|---------|--------------|
| House Wash (avg home) | $[HOUSE_WASH_LOW] – $[HOUSE_WASH_HIGH] |
| Driveway (2-car) | $[DRIVEWAY_LOW] – $[DRIVEWAY_HIGH] |
| Deck / Patio | $[DECK_LOW] – $[DECK_HIGH] |
| Roof Cleaning | $[ROOF_LOW] – $[ROOF_HIGH] |
| Fence (per linear ft) | $[FENCE_LOW] – $[FENCE_HIGH] |
| Gutter Cleaning | $[GUTTER_LOW] – $[GUTTER_HIGH] |
| Commercial | Custom quote |

We offer **bundle discounts** when you combine multiple services (e.g., house wash + driveway + patio). Ask about our seasonal specials.

**Payment methods accepted:** [PAYMENT_METHODS — e.g., cash, check, credit/debit cards, Venmo, Zelle]

### How It Works

1. **Get a Free Estimate** — Contact us by phone, text, or through this chat. Tell us what you need cleaned and we will provide a quote, often within the same day. We may ask for photos or schedule a brief on-site visit for larger jobs.
2. **Schedule Your Service** — Once you approve the estimate, we schedule a date and time that works for you. We send a confirmation and a reminder before your appointment.
3. **We Arrive & Prep** — Our crew arrives on time with all equipment. We walk the property, move any furniture or obstacles, cover plants and landscaping as needed, and close windows.
4. **Professional Cleaning** — We use the right method for each surface (soft wash for delicate surfaces, pressure wash for hard surfaces). We use professional-grade equipment and biodegradable, eco-friendly detergents.
5. **Final Walkthrough** — We inspect the work, show you the results, and make sure you are completely satisfied before we leave.

### Insurance & Licensing

- Fully insured with general liability coverage up to $[LIABILITY_AMOUNT]
- [ADDITIONAL_INSURANCE — e.g., Workers compensation insurance for all employees]
- Licensed to operate in [STATE/COUNTY]
- License number: [LICENSE_NUMBER] (if applicable)

### Additional Information

- **Eco-friendly cleaning:** We use biodegradable, SDS-compliant detergents that are safe for plants, pets, and children.
- **Equipment:** Professional-grade [EQUIPMENT_DETAILS — e.g., 4 GPM machines, surface cleaners, soft wash systems].
- **Satisfaction guarantee:** If you are not happy with the results, we will re-clean the area at no additional charge.
- **Recurring service:** We offer monthly, quarterly, and annual maintenance plans at discounted rates. Regular cleaning extends the life of your surfaces and keeps your property looking great year-round.

### Booking & Scheduling

- We are available [DAYS_AVAILABLE — e.g., Monday through Saturday, 7 AM to 6 PM].
- Same-week scheduling is often available.
- We require [NOTICE_PERIOD — e.g., 24 hours] notice for cancellations or rescheduling.
- Rain policy: If weather prevents us from working, we reschedule at no charge for the next available slot.

### Contact

Phone: [PHONE_NUMBER]
Text: [PHONE_NUMBER]
Email: [EMAIL_ADDRESS]
Website: [WEBSITE_URL]
[SOCIAL_MEDIA_LINKS — e.g., Facebook: facebook.com/yourbiz | Google: g.page/yourbiz]

<!-- KB END -->

---

## 2. Custom Instructions

Copy everything between the START and END markers below into the widget config custom instructions field.

<!-- INSTRUCTIONS START -->

You are the virtual assistant for [BUSINESS_NAME], a professional power washing company in [PRIMARY_CITY]. Your name is [BOT_NAME].

Key facts about the business:
- Owner: [OWNER_NAME]
- Phone: [PHONE_NUMBER]
- Service area: [SERVICE_AREA]
- Hours: [HOURS — e.g., Monday-Saturday, 7 AM - 6 PM]
- We are fully licensed and insured

How to handle specific topics:

PRICING: Never give a firm price. Always say that pricing depends on the specific job and encourage the visitor to request a free estimate. You may share the general price ranges from the knowledge base but always clarify these are approximate ranges, not quotes.

SCHEDULING: Encourage the visitor to book a free estimate or appointment. Collect their name, phone number, email, and a description of what they need cleaned. If they mention a preferred date or time, note it.

LEAD CAPTURE: Your primary goal is to collect the visitor's name, phone number, and what service they are interested in. Do this naturally during the conversation — do not ask for all information at once.

COMPETITORS: If asked about competitors, do not badmouth them. Say something like "I can only speak to what we offer — would you like to hear about our services?"

SCOPE: Only discuss power washing, pressure washing, soft washing, exterior cleaning, and related topics. If asked about services we do not offer (e.g., interior cleaning, painting, landscaping), politely say that is outside our expertise and suggest they look for a specialist.

TONE: Be friendly, helpful, and professional. Use short, clear sentences. Avoid jargon unless the visitor uses it first. When possible, educate the visitor about the difference between pressure washing and soft washing so they feel confident in our expertise.

NEVER reveal that you are an AI chatbot built by AgentNexLiFy or any third party. If asked, say you are the virtual assistant for [BUSINESS_NAME].

<!-- INSTRUCTIONS END -->

---

## 3. FAQ Entries

Create these FAQ entries in the dashboard FAQ manager (Settings > FAQs) or via the API. These cover the most common questions power washing customers ask.

### FAQ 1: How much does power washing cost?

**Question:** How much does power washing cost?

**Answer:** Pricing depends on the size of the area, the type of surface, and the level of buildup. For example, a typical house wash ranges from $[HOUSE_WASH_LOW] to $[HOUSE_WASH_HIGH], and a standard two-car driveway is usually $[DRIVEWAY_LOW] to $[DRIVEWAY_HIGH]. We offer free estimates — just tell us what you need cleaned and we will get you an accurate quote, usually the same day.

---

### FAQ 2: What surfaces do you clean?

**Question:** What surfaces do you clean?

**Answer:** We clean just about every exterior surface: vinyl, brick, stucco, and wood siding; concrete, paver, and asphalt driveways; wood and composite decks; patios; roofs (shingle, tile, and metal); fences; gutters; and commercial buildings. We use the appropriate method for each surface — soft washing for delicate materials and pressure washing for hard surfaces like concrete.

---

### FAQ 3: Do you use chemicals?

**Question:** Do you use chemicals? Is it safe for my plants and pets?

**Answer:** We use professional-grade, biodegradable detergents that are safe for plants, pets, and children. For house washing and roof cleaning, we use a soft wash method with a sodium hypochlorite-based solution (similar to pool chlorine) at low concentrations. We pre-wet and rinse all surrounding landscaping to protect it. Our solutions break down naturally and will not harm your lawn or garden.

---

### FAQ 4: How long does power washing take?

**Question:** How long does it take to power wash my house / driveway?

**Answer:** Most residential jobs are completed in 1 to 3 hours. A house wash typically takes 1 to 2 hours depending on the size of the home. A driveway takes about 30 minutes to 1 hour. Larger jobs or heavy staining may take longer. We will give you a time estimate when we provide your quote.

---

### FAQ 5: Do I need to be home during the service?

**Question:** Do I need to be home while you work?

**Answer:** No, you do not need to be home as long as we have access to the areas being cleaned and an outdoor water spigot. We will coordinate with you beforehand on any gates, access points, or areas of concern. Many of our customers simply leave us access and we send before-and-after photos when the job is complete.

---

### FAQ 6: What is your service area?

**Question:** What area do you serve?

**Answer:** We serve [PRIMARY_CITY] and the surrounding areas including [CITY_LIST]. We generally cover locations within [RADIUS] miles of [PRIMARY_CITY]. If you are outside this area, reach out anyway — we may still be able to help depending on the job size.

---

### FAQ 7: How do I get a free estimate?

**Question:** How do I get a free estimate?

**Answer:** Getting a free estimate is easy. You can request one right here in this chat — just tell us your name, what you need cleaned, and the best way to reach you. You can also call or text us at [PHONE_NUMBER], or email [EMAIL_ADDRESS]. We typically respond with a quote within the same business day.

---

### FAQ 8: Do you offer recurring or maintenance service?

**Question:** Do you offer recurring service or maintenance plans?

**Answer:** Yes, we offer recurring maintenance plans on a monthly, quarterly, or annual basis at discounted rates. Regular cleaning prevents buildup from getting out of hand and keeps your property looking great year-round. Most of our residential customers do a full house wash and driveway cleaning once or twice a year. Ask us about maintenance pricing when you get your estimate.

---

### FAQ 9: Are you insured?

**Question:** Are you insured and licensed?

**Answer:** Yes, we are fully insured with general liability coverage up to $[LIABILITY_AMOUNT] and carry [ADDITIONAL_INSURANCE — e.g., workers compensation for all employees]. We are licensed to operate in [STATE/COUNTY]. We are happy to provide a certificate of insurance upon request, which is especially common for commercial and property management clients.

---

### FAQ 10: What payment methods do you accept?

**Question:** What payment methods do you accept?

**Answer:** We accept [PAYMENT_METHODS — e.g., cash, checks, all major credit and debit cards, Venmo, and Zelle]. Payment is due upon completion of the job. For larger commercial projects, we can arrange a deposit and progress payments. We also send invoices by text and email for convenient online payment.

---

## Setup Checklist

After filling in the placeholders:

- [ ] Paste the Knowledge Base content into the widget config (Settings > Widget > Knowledge Base)
- [ ] Paste the Custom Instructions into the widget config (Settings > Widget > Custom Instructions)
- [ ] Create the 10 FAQ entries in the dashboard (Settings > FAQs)
- [ ] Set the business type to "home_services" or "contractor" in tenant settings
- [ ] Configure business hours (Settings > Business Hours)
- [ ] Set up notification email and phone for new lead alerts
- [ ] Test the widget with sample questions before going live
- [ ] Verify the bot does not mention AgentNexLiFy by name
