-- 202_leads_pipeline_stage.sql
--
-- Pipeline display names ("New Lead", "Qualified", "Won") are not legal
-- leads.status values. leads_status_check allows only:
--   new, contacted, appointment_booked, closed, lost.
--
-- Keep the stage label the board groups on in pipeline_stage, and keep
-- status canonical. Nullable so existing rows stay valid.

ALTER TABLE leads ADD COLUMN IF NOT EXISTS pipeline_stage TEXT;

CREATE INDEX IF NOT EXISTS idx_leads_client_pipeline_stage
  ON leads (client_id, pipeline_stage);
