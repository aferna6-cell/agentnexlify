-- Migration 158: Fix wizard_events step range constraint
-- The original migration 079 created CHECK (step >= 1 AND step <= 6).
-- Step 0 = express-setup chooser, which is a valid funnel entry point.
-- The backend Pydantic model (wizard_analytics.py) already accepted 0–7
-- but DB rejected step-0 rows silently, so the express-chooser entry is
-- invisible in the admin funnel drop-off readout.
-- Admin funnel labels (admin_funnel.py) also define step 7 = "embed" for
-- future use, so extend the upper bound to 7 as well.

ALTER TABLE wizard_events
    DROP CONSTRAINT IF EXISTS wizard_events_step_check;

ALTER TABLE wizard_events
    ADD CONSTRAINT wizard_events_step_check CHECK (step >= 0 AND step <= 7);

-- Also widen the action set to include demo_referral, which the backend
-- already emits (wizard_analytics.py action pattern includes it) but the
-- original DB constraint did not allow.
ALTER TABLE wizard_events
    DROP CONSTRAINT IF EXISTS wizard_events_action_check;

ALTER TABLE wizard_events
    ADD CONSTRAINT wizard_events_action_check
    CHECK (action IN ('enter', 'complete', 'skip', 'abandon', 'demo_referral'));
