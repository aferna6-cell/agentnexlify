/**
 * API barrel export — re-exports all domain modules.
 *
 * Components can import from either:
 *   import { fetchLeads } from "../utils/api"           (legacy, still works)
 *   import { fetchLeads } from "../utils/api/leads"     (new, domain-specific)
 *
 * New features should add functions to domain modules, not the monolith.
 */

// Domain modules (extracted from api.js)
export * from "./leads";
export * from "./invoices";
export * from "./documents";
export * from "./pipeline";
export * from "./reviews";
export * from "./content";

// Shared client (for advanced usage)
export { request, BASE, ApiError } from "./_client";
