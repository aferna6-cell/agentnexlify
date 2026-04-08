/**
 * Invoice API functions — invoicing, payments, item templates.
 */
import { request } from "./_client";

export function fetchInvoices(tenantId, token, filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.lead_id) params.set("lead_id", filters.lead_id);
  const qs = params.toString();
  return request(`/api/v1/invoices/${tenantId}${qs ? "?" + qs : ""}`, { token });
}
export function createInvoice(tenantId, token, data) {
  return request(`/api/v1/invoices/${tenantId}`, { method: "POST", token, body: data });
}
export function updateInvoice(tenantId, token, invoiceId, data) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}`, { method: "PUT", token, body: data });
}
export function deleteInvoice(tenantId, token, invoiceId) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}`, { method: "DELETE", token });
}
export function sendInvoice(tenantId, token, invoiceId, data) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}/send`, { method: "POST", token, body: data });
}
export function markInvoicePaid(tenantId, token, invoiceId) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}/mark-paid`, { method: "POST", token, body: {} });
}
export function fetchInvoiceStats(tenantId, token) {
  return request(`/api/v1/invoices/${tenantId}/stats`, { token });
}
export function createInvoiceFromBid(tenantId, token, bidId) {
  return request(`/api/v1/invoices/${tenantId}/from-bid/${bidId}`, { method: "POST", token });
}
export function recordPayment(tenantId, token, invoiceId, data) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}/record-payment`, { method: "POST", token, body: data });
}

// Item Templates
export function fetchItemTemplates(tenantId, token) {
  return request(`/api/v1/invoices/${tenantId}/item-templates`, { token });
}
export function createItemTemplate(tenantId, token, data) {
  return request(`/api/v1/invoices/${tenantId}/item-templates`, { method: "POST", token, body: data });
}

export function bulkSendInvoices(tenantId, token, invoiceIds, channel = "email") {
  return request(`/api/v1/invoices/${tenantId}/bulk-send`, {
    method: "POST", token,
    body: { invoice_ids: invoiceIds, channel },
  });
}
