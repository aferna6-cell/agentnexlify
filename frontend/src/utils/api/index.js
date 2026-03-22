/**
 * API barrel export — re-exports all domain modules.
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
export * from "./jobs";
export * from "./bids";
export * from "./forms";
export * from "./conversations";
export * from "./analytics";
export * from "./automations";
export * from "./menu";
export * from "./seo";
export * from "./calls";
export * from "./portal";
export * from "./smart-lists";
export * from "./dashboard";
export * from "./faq";
export * from "./widget-config";
export * from "./crm";
export * from "./action-items";
export * from "./inbox";
export * from "./snippets";

export { request, BASE, ApiError } from "./_client";
