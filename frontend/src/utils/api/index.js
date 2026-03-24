/**
 * API barrel export — re-exports all domain modules.
 * New features should add functions to domain modules, not the monolith api.js.
 */

export * from "./action-items";
export * from "./analytics";
export * from "./appointments";
export * from "./automations";
export * from "./bids";
export * from "./business-page";
export * from "./calls";
export * from "./campaigns";
export * from "./chat-flows";
export * from "./content";
export * from "./conversations";
export * from "./crm";
export * from "./dashboard";
export * from "./documents";
export * from "./faq";
export * from "./forms";
export * from "./inbox";
export * from "./integrations";
export * from "./invoices";
export * from "./jobs";
export * from "./leads";
export * from "./menu";
export * from "./misc";
export * from "./phone";
export * from "./pipeline";
export * from "./portal";
export * from "./reviews";
export * from "./seo";
export * from "./smart-lists";
export * from "./snippets";
export * from "./social";
export * from "./tags";
export * from "./team";
export * from "./waitlist";
export * from "./webhooks";
export * from "./widget-config";
export * from "./scoring";

export { request, BASE, ApiError } from "./_client";
