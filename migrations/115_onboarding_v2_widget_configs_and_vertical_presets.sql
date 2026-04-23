-- 115: Onboarding V2 — widget_configs additions + vertical_presets table + seed data
-- Applied: 2026-04-23

-- ============================================================
-- 1. widget_configs — add v2 onboarding columns (all IF NOT EXISTS)
-- ============================================================
ALTER TABLE widget_configs
    ADD COLUMN IF NOT EXISTS onboarding_version TEXT DEFAULT 'v1'
        CHECK (onboarding_version IN ('v1', 'v2')),
    ADD COLUMN IF NOT EXISTS ready_to_launch BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS readiness_criteria JSONB DEFAULT
        '{"services_count": 0, "hours_filled": false, "faqs_count": 0, "logo_uploaded": false}'::jsonb,
    ADD COLUMN IF NOT EXISTS vertical_preset TEXT
        CHECK (vertical_preset IS NULL OR vertical_preset IN (
            'plumbing', 'hvac', 'cleaning', 'power_washing', 'landscaping', 'electrical'
        )),
    ADD COLUMN IF NOT EXISTS last_health_check_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_health_check_status TEXT
        CHECK (last_health_check_status IS NULL OR last_health_check_status IN (
            'green', 'yellow', 'red'
        ));

-- NOTE: allowed_domains TEXT[] already exists on widget_configs — not re-added.

-- ============================================================
-- 2. vertical_presets table
-- ============================================================
CREATE TABLE IF NOT EXISTS vertical_presets (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vertical               TEXT NOT NULL UNIQUE CHECK (vertical IN (
                               'plumbing', 'hvac', 'cleaning', 'power_washing', 'landscaping', 'electrical'
                           )),
    display_name           TEXT NOT NULL,
    default_services       JSONB NOT NULL DEFAULT '[]'::jsonb,
    default_faqs           JSONB NOT NULL DEFAULT '[]'::jsonb,
    default_hours          JSONB NOT NULL DEFAULT '{}'::jsonb,
    avg_ticket_amount      NUMERIC(10, 2),
    avg_hours_saved_per_lead NUMERIC(4, 2),
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at             TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE vertical_presets ENABLE ROW LEVEL SECURITY;

CREATE POLICY vertical_presets_read_all ON vertical_presets
    FOR SELECT USING (true);

CREATE POLICY vertical_presets_service_write ON vertical_presets
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- 3. Seed data for all 6 verticals
-- ============================================================
INSERT INTO vertical_presets (
    vertical, display_name, default_services, default_faqs, default_hours,
    avg_ticket_amount, avg_hours_saved_per_lead
) VALUES

-- PLUMBING
(
    'plumbing',
    'Plumbing',
    '["Drain Cleaning", "Water Heater Installation", "Leak Detection & Repair", "Toilet Repair & Replacement", "Faucet & Fixture Installation", "Pipe Repair & Replacement", "Sewer Line Services", "Water Softener Installation"]'::jsonb,
    '[
        {"q": "Do you offer emergency plumbing services?", "a": "Yes, we provide 24/7 emergency plumbing services for urgent issues like burst pipes, sewer backups, and major leaks. Call us any time and we will dispatch a technician promptly."},
        {"q": "How quickly can you get to my home?", "a": "For standard appointments we typically arrive within 1-2 hours. Emergency calls are prioritized and we aim to reach you within 60 minutes."},
        {"q": "Do you provide upfront pricing?", "a": "Yes, we give you a written estimate before any work begins. You only pay what was agreed — no surprises."},
        {"q": "Are your plumbers licensed and insured?", "a": "All of our plumbers are fully licensed, bonded, and insured. We carry full liability coverage on every job."},
        {"q": "Do you warranty your work?", "a": "We stand behind our work with a 1-year parts and labor warranty on all plumbing repairs and installations."},
        {"q": "What payment methods do you accept?", "a": "We accept cash, check, and all major credit cards. Financing options are available for larger jobs."}
    ]'::jsonb,
    '{"monday": {"open": "08:00", "close": "18:00"}, "tuesday": {"open": "08:00", "close": "18:00"}, "wednesday": {"open": "08:00", "close": "18:00"}, "thursday": {"open": "08:00", "close": "18:00"}, "friday": {"open": "08:00", "close": "18:00"}, "saturday": {"open": "09:00", "close": "14:00"}, "sunday": null, "emergency": "24/7 emergency service available — call our main number at any time."}'::jsonb,
    350.00,
    0.5
),

-- HVAC
(
    'hvac',
    'HVAC',
    '["AC Repair & Maintenance", "Furnace Repair & Replacement", "HVAC System Installation", "Air Duct Cleaning", "Thermostat Installation", "Heat Pump Services", "Indoor Air Quality Testing", "Seasonal Tune-Up & Inspection"]'::jsonb,
    '[
        {"q": "Do you offer emergency HVAC repair?", "a": "Yes, we offer 24/7 emergency HVAC service. Whether your AC goes out in summer or your heat fails in winter, our technicians are on call."},
        {"q": "How often should I service my HVAC system?", "a": "We recommend a professional tune-up twice a year — once in spring before cooling season and once in fall before heating season. Regular maintenance extends system life and lowers energy bills."},
        {"q": "What brands do you service?", "a": "We service all major brands including Carrier, Trane, Lennox, Rheem, and many more. Our technicians are trained and certified across brands."},
        {"q": "How long does an AC installation take?", "a": "A standard residential AC installation typically takes 4-8 hours depending on the size of the system and any required ductwork modifications."},
        {"q": "Do you offer financing?", "a": "Yes, we offer flexible financing options for system replacements and major repairs. Ask about our 0% interest plans for qualified customers."},
        {"q": "What is your warranty policy?", "a": "We offer a 1-year labor warranty on all repairs and pass through full manufacturer warranties on new equipment, which typically range from 5-10 years."}
    ]'::jsonb,
    '{"monday": {"open": "08:00", "close": "18:00"}, "tuesday": {"open": "08:00", "close": "18:00"}, "wednesday": {"open": "08:00", "close": "18:00"}, "thursday": {"open": "08:00", "close": "18:00"}, "friday": {"open": "08:00", "close": "18:00"}, "saturday": {"open": "09:00", "close": "14:00"}, "sunday": null, "emergency": "24/7 emergency service available — call our main number at any time."}'::jsonb,
    450.00,
    0.5
),

-- CLEANING
(
    'cleaning',
    'Cleaning Services',
    '["Standard House Cleaning", "Deep Cleaning", "Move-In / Move-Out Cleaning", "Post-Construction Cleaning", "Office & Commercial Cleaning", "Carpet & Upholstery Cleaning", "Window Cleaning", "Recurring Maid Service"]'::jsonb,
    '[
        {"q": "Do I need to be home during the cleaning?", "a": "No, many of our clients provide a key or door code so our team can clean while you are at work. All staff are background-checked and insured."},
        {"q": "What is included in a standard cleaning?", "a": "Our standard cleaning covers dusting, vacuuming, mopping, bathroom sanitizing, kitchen surfaces, and trash removal. Deep cleans include inside appliances, baseboards, and detailed scrubbing."},
        {"q": "Do you bring your own supplies?", "a": "Yes, we bring all cleaning products and equipment. If you prefer specific eco-friendly or fragrance-free products, just let us know and we will accommodate."},
        {"q": "How do I get a quote?", "a": "We can give you an instant quote right here in this chat based on your home size and cleaning type. Most quotes take under 2 minutes."},
        {"q": "What is your cancellation policy?", "a": "We ask for 24 hours notice to cancel or reschedule at no charge. Late cancellations may incur a small fee."},
        {"q": "Are your cleaners insured and background-checked?", "a": "Yes, every team member passes a background check and is fully insured. We are bonded for your protection."}
    ]'::jsonb,
    '{"monday": {"open": "08:00", "close": "18:00"}, "tuesday": {"open": "08:00", "close": "18:00"}, "wednesday": {"open": "08:00", "close": "18:00"}, "thursday": {"open": "08:00", "close": "18:00"}, "friday": {"open": "08:00", "close": "18:00"}, "saturday": {"open": "09:00", "close": "14:00"}, "sunday": null}'::jsonb,
    150.00,
    0.5
),

-- POWER WASHING
(
    'power_washing',
    'Power Washing',
    '["Driveway & Sidewalk Washing", "House Exterior Washing", "Deck & Patio Cleaning", "Roof Soft Washing", "Fence Cleaning", "Commercial Pressure Washing", "Gutter Cleaning & Flushing", "Graffiti Removal"]'::jsonb,
    '[
        {"q": "How often should I get my house power washed?", "a": "For most homes we recommend once a year. Homes near trees or in humid climates may benefit from washing every 6 months to prevent mold and mildew buildup."},
        {"q": "Will pressure washing damage my siding?", "a": "We use the appropriate pressure and technique for each surface. Vinyl siding, painted wood, and brick all receive different treatment. Delicate surfaces get soft washing instead of high pressure."},
        {"q": "Do you treat for mold and mildew?", "a": "Yes, our cleaning solutions include EPA-approved mold and mildew treatments that kill growth at the root, not just wash it away."},
        {"q": "How long does it take to wash a house?", "a": "An average single-story home takes 2-3 hours. Two-story homes typically take 3-5 hours. We will give you a specific estimate when you book."},
        {"q": "Do I need to be home during service?", "a": "You do not need to be home as long as we have access to an outdoor water spigot. We will send photos when the job is complete."},
        {"q": "What is your pricing based on?", "a": "Pricing is based on square footage and the surface type. We offer free instant quotes — just let us know the size of what you need washed."}
    ]'::jsonb,
    '{"monday": {"open": "08:00", "close": "18:00"}, "tuesday": {"open": "08:00", "close": "18:00"}, "wednesday": {"open": "08:00", "close": "18:00"}, "thursday": {"open": "08:00", "close": "18:00"}, "friday": {"open": "08:00", "close": "18:00"}, "saturday": {"open": "09:00", "close": "14:00"}, "sunday": null}'::jsonb,
    200.00,
    0.5
),

-- LANDSCAPING
(
    'landscaping',
    'Landscaping',
    '["Lawn Mowing & Edging", "Landscaping Design & Installation", "Mulching & Ground Cover", "Tree Trimming & Removal", "Shrub & Hedge Trimming", "Fertilization & Weed Control", "Irrigation System Installation", "Seasonal Cleanups"]'::jsonb,
    '[
        {"q": "Do you offer recurring lawn maintenance?", "a": "Yes, we offer weekly, biweekly, and monthly maintenance plans. Recurring clients receive priority scheduling and discounted rates."},
        {"q": "Can you design a new landscape for my yard?", "a": "Absolutely. We offer full design consultations and can transform your yard from concept to completion. We handle everything from layout to plant selection to installation."},
        {"q": "When is the best time to plant?", "a": "Spring and fall are ideal for most plantings in our climate. We will advise you on the best timing based on the plants you want and your local conditions."},
        {"q": "Do you provide free estimates?", "a": "Yes, we offer free on-site estimates for all landscaping projects. For lawn maintenance quotes we can often provide pricing right here in chat."},
        {"q": "Are you licensed and insured?", "a": "Yes, we are fully licensed and carry general liability and workers compensation insurance on all crew members."},
        {"q": "Do you handle large tree removal?", "a": "Yes, our certified arborists handle trees of all sizes including large hazardous trees. We also offer stump grinding."}
    ]'::jsonb,
    '{"monday": {"open": "08:00", "close": "18:00"}, "tuesday": {"open": "08:00", "close": "18:00"}, "wednesday": {"open": "08:00", "close": "18:00"}, "thursday": {"open": "08:00", "close": "18:00"}, "friday": {"open": "08:00", "close": "18:00"}, "saturday": {"open": "09:00", "close": "14:00"}, "sunday": null}'::jsonb,
    250.00,
    0.5
),

-- ELECTRICAL
(
    'electrical',
    'Electrical Services',
    '["Panel Upgrade & Replacement", "Outlet & Switch Installation", "Ceiling Fan Installation", "Lighting Installation", "EV Charger Installation", "Safety Inspection", "Generator Installation", "Smoke & CO Detector Installation"]'::jsonb,
    '[
        {"q": "Is your work up to code?", "a": "All of our electrical work meets or exceeds local building codes. We pull permits where required and our work passes inspection."},
        {"q": "When should I upgrade my electrical panel?", "a": "Consider an upgrade if your panel is over 25 years old, you are adding major appliances, have breakers that frequently trip, or are adding an EV charger or home addition."},
        {"q": "Do you install EV chargers?", "a": "Yes, we install Level 2 home EV charging stations for all major car brands. We handle the permitting and inspection process from start to finish."},
        {"q": "What is a safety inspection and do I need one?", "a": "A safety inspection checks your panel, wiring, outlets, and grounding for hazards. We recommend one for homes over 20 years old or before buying a home."},
        {"q": "Are your electricians licensed?", "a": "All of our electricians are licensed master or journeyman electricians. We carry full liability and workers compensation insurance."},
        {"q": "How do I know if I have an electrical emergency?", "a": "Call us immediately if you smell burning near outlets, see flickering lights throughout the home, have a breaker that will not reset, or notice scorch marks on outlets or panels."}
    ]'::jsonb,
    '{"monday": {"open": "08:00", "close": "18:00"}, "tuesday": {"open": "08:00", "close": "18:00"}, "wednesday": {"open": "08:00", "close": "18:00"}, "thursday": {"open": "08:00", "close": "18:00"}, "friday": {"open": "08:00", "close": "18:00"}, "saturday": {"open": "09:00", "close": "14:00"}, "sunday": null}'::jsonb,
    400.00,
    0.5
)

ON CONFLICT (vertical) DO NOTHING;
