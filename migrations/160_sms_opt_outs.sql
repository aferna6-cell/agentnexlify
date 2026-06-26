-- 160_sms_opt_outs.sql
--
-- TCPA compliance: durable per-tenant SMS opt-out ledger. Inbound STOP already
-- flips leads.unsubscribed (os_inbound.py), and scheduled automation gates on
-- that flag — but the Agent OS sms.send action and the missed-call text-back
-- did NOT check any opt-out before sending, and opt-outs for phone numbers that
-- aren't lead rows were never stored. This table is the durable, phone-keyed
-- opt-out signal checked before every outbound SMS (see sms_compliance.py).
--
-- client_id (not tenant_id) to match leads/conversations customer-data tables.
-- phone_last10 = last 10 digits, normalized so E.164 inbound matches any stored
-- format.

CREATE TABLE IF NOT EXISTS sms_opt_outs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id    uuid NOT NULL,
  phone_last10 text NOT NULL,
  source       text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, phone_last10)
);

CREATE INDEX IF NOT EXISTS idx_sms_opt_outs_lookup
  ON sms_opt_outs (client_id, phone_last10);
