# Multi-Vertical Product Positioning

**Date:** 2026-04-18  
**Decision:** Sell AgentNexLiFy as vertical-specific packs on one shared platform, not as a generic AI chatbot.

## Positioning Rule

The product can support multiple verticals, but each buyer must see a product that sounds built for their world. The shared engine stays the same: widget, lead capture, qualification, booking, follow-up, reviews, invoices, and dashboard. The packaging changes by vertical.

## First Vertical Packs

### 1. Contractors and Home Services

**Best for:** pressure washing, HVAC, plumbing, roofing, cleaning, landscaping, remodeling.

**Promise:** turn website visitors and missed calls into qualified quote requests.

**90-second setup fields:**
- Service area
- Services offered
- Emergency availability
- Estimate policy
- License/insurance language
- Financing or deposit rules

**Lead fields:**
- Service needed
- Property type
- Address or ZIP
- Urgency
- Photos available
- Budget range

**Default automations:**
- New quote request text-back
- No-response follow-up after 2 hours
- Estimate reminder
- Review request after job completion

**Proof metric:** quote requests captured per 100 site visitors.

### 2. Salons, Spas, and Beauty

**Best for:** hair salons, med spas, nail salons, barbers, massage, esthetics.

**Promise:** answer service questions and move visitors into booked appointments.

**90-second setup fields:**
- Service menu
- Hours
- Booking link
- Cancellation policy
- Stylist/provider preferences
- New-client offers

**Lead fields:**
- Desired service
- Preferred date/time
- Provider preference
- First visit or returning
- Contact preference

**Default automations:**
- Booking nudge
- Appointment reminder
- No-show recovery
- Rebooking follow-up

**Proof metric:** appointment requests and bookings from widget conversations.

### 3. Dental and Local Health Offices

**Best for:** dental, orthodontics, chiropractors, physical therapy, wellness clinics.

**Promise:** qualify new-patient interest without making clinical claims.

**90-second setup fields:**
- Services accepted for online inquiry
- Insurance accepted
- New-patient process
- Emergency policy
- Office hours
- Booking link

**Lead fields:**
- Reason for visit
- Insurance status
- New or existing patient
- Preferred appointment window
- Phone number

**Default automations:**
- New-patient intake follow-up
- Missed-call text-back
- Appointment reminder
- Review request after visit

**Guardrail:** never diagnose, prescribe, or imply emergency medical advice. Escalate urgent symptoms to phone/human.

**Proof metric:** new-patient inquiries captured and routed.

### 4. Auto Detailers and Local Auto Services

**Best for:** detailing, tinting, wraps, repair shops, mobile mechanics, tire shops.

**Promise:** capture vehicle-specific service requests and quote-ready leads.

**90-second setup fields:**
- Services offered
- Mobile or shop-based
- Vehicle types served
- Starting prices
- Booking link
- Photo request preference

**Lead fields:**
- Vehicle year/make/model
- Service needed
- Condition/photos
- Location
- Desired date

**Default automations:**
- Photo request follow-up
- Quote reminder
- Appointment confirmation
- Review request

**Proof metric:** quote-ready leads with vehicle details.

## Product Copy Pattern

Use this frame everywhere:

`AI lead capture for <vertical> that <specific outcome>.`

Examples:
- `AI lead capture for contractors that turns website visitors into quote requests.`
- `AI booking support for salons that answers service questions and fills the calendar.`
- `AI intake for dental offices that routes new-patient interest safely.`
- `AI quote capture for auto detailers that gathers vehicle details before you reply.`

## Implementation Pattern

Each vertical pack should have:
- Dashboard onboarding preset
- Widget default greeting
- FAQ seed set
- Lead field preset
- Automation preset
- Landing-page section or dedicated route
- Demo conversation transcript

## What Not To Do

- Do not claim the platform is equally perfect for every small business.
- Do not sell "AI automation" as the main noun.
- Do not make one landing page carry all vertical detail.
- Do not add vertical-specific code branches until presets prove the need.

## Next Build Order

1. Contractors/Home Services pack, because MTOptions already validates message volume.
2. Salons/Spas pack, because booking intent is simple and high-frequency.
3. Dental/Local Health pack, because it creates a useful safety-aware wedge.
4. Auto Detailers pack, because quote capture is structured and demo-friendly.

## Success Gate

A vertical pack is ready when a partner can show a prospect:
- one vertical landing message
- one matching widget demo
- one 90-second onboarding flow
- one proof metric that would matter to that buyer
