/**
 * API barrel export — re-exports all domain modules.
 *
 * New features should add functions to domain modules, not the monolith api.js.
 */

export * from "./leads";
export * from "./invoices";
export * from "./documents";
export * from "./pipeline";
export * from "./reviews";
export * from "./content";
export * from "./appointments";
export * from "./webhooks";
export * from "./team";
export * from "./social";
export * from "./campaigns";

export { request, BASE, ApiError } from "./_client";
