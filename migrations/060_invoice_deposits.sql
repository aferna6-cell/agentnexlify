-- Migration 060: Deposit/partial payments + recurring invoices
-- Adds deposit tracking and recurrence support to invoices

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS deposit_amount NUMERIC(10, 2) DEFAULT 0;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS amount_paid NUMERIC(10, 2) DEFAULT 0;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN DEFAULT FALSE;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS recurrence_interval TEXT CHECK (recurrence_interval IN ('weekly', 'biweekly', 'monthly', 'quarterly'));
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS next_invoice_date DATE;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS parent_invoice_id UUID REFERENCES invoices(id);
