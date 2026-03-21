/**
 * API barrel export — re-exports all domain modules.
 *
 * Components can import from either:
 *   import { fetchInvoices } from "../utils/api"      (legacy, still works)
 *   import { fetchInvoices } from "../utils/api/invoices"  (new, domain-specific)
 *
 * New features should add functions to domain modules, not the monolith.
 */

// Domain modules (extracted from api.js)
export * from "./invoices";
export * from "./documents";

// Shared client (for advanced usage)
export { request, BASE, ApiError } from "./_client";
