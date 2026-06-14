/**
 * API barrel export - re-exports all domain modules.
 * New features should add functions to domain modules, not the monolith api.js.
 */

export * from "./action-items";
export * from "./analytics";
export * from "./appointments";
export * from "./automations";
export * from "./bids";
export * from "./business-page";
export * from "./campaigns";
export * from "./conversations";
export * from "./crm";
export * from "./dashboard";
export * from "./documents";
export * from "./faq";
export * from "./inbox";
export * from "./integrations";
export * from "./invoices";
export * from "./leads";
export * from "./misc";
export * from "./phone";
export * from "./pipeline";
export * from "./portal";
export * from "./seo";
export * from "./snippets";
export * from "./social";
export * from "./tags";
export * from "./team";
export * from "./webhooks";
export * from "./widget-config";

export { request, BASE, ApiError } from "./_client";
export * from "./auth";
export * from "./onboarding";
export * from "./os";
