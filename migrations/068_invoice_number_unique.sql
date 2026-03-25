-- 068: Add unique constraint on invoice_number per tenant
-- Prevents duplicate invoice numbers under concurrent creation
CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_tenant_number
ON invoices(tenant_id, invoice_number);
