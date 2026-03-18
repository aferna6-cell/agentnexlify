-- Fix missing ON DELETE clause on conversations.lead_id FK
ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_lead_id_fkey;
ALTER TABLE conversations ADD CONSTRAINT conversations_lead_id_fkey 
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL;
