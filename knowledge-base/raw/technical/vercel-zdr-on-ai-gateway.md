---
source_url: https://vercel.com/blog/zdr-on-ai-gateway
fetched_at: 2026-04-17T22:04:19Z
category: technical
title: Zero Data Retention on AI Gateway - Vercel
---

# Zero Data Retention on AI Gateway - Vercel

## Zero Data Retention on AI Gateway

Building with multiple AI models means wrestling with fragmented data policies. With many different model providers, it's not just fragmented, it's just too much time spent on the wrong things.

You have to read through different terms of service, track which providers comply with your security requirements, and hope developers remember to configure opt-outs correctly on every request. What should be a straightforward policy becomes a manual, error-prone process because many providers do not offer Zero Data Retention (ZDR) by default.

AI Gateway changes this by handling the negotiation and enforcement for you. Instead of managing policies provider by provider, you get the freedom to just build. AI Gateway ensures your data requirements are met automatically by only routing to providers where we have negotiated Zero Data Retention agreements. Models from OpenAI, Anthropic, Google, and more have ZDR providers available.

Today, we are expanding AI Gateway's compliance capabilities with team-wide Zero Data Retention (ZDR), letting you enforce strict data policies across your entire team without touching any code. Gateway compliance features now include team-wide ZDR from the dashboard, per-request ZDR for specific sensitive workflows, and explicit controls to disallow prompt training.

Toggle on in the AI Gateway Dashboard Settings, and all subsequent requests via AI Gateway will only route through ZDR-compliant providers.

## Link to headingTeam-wide Zero Data Retention

Team-wide ZDR is available for Pro and Enterprise teams. It applies to every request your team makes, requiring no code changes. This is ideal for teams that want controls with complete assurance that no one can modify or misapply restrictions.

## Link to headingRequest-level controls

Per-request ZDR lets you enforce data deletion on specific requests when only certain workflows handle sensitive data. This is useful when your app has proprietary information in certain queries but other requests are not as protected. You can enable request-level ZDR in all API formats supported by AI Gateway in the provider options.

import type { GatewayProviderOptions } from '@ai-sdk/gateway';

prompt: 'Analyze this sensitive business data and provide insights.',

Team-wide and per-request settings work together. If either is enabled, ZDR is enforced.

## Link to headingDisallow Prompt Training

Disallow Prompt Training prevents providers from using your prompt data to train their models. This is a good default for any team sending proprietary code, internal documents, or business strategy through an LLM. This filter is available on the request-level.

ZDR is a superset of this control. If you enable ZDR, training opt-out is already covered.

import type { GatewayProviderOptions } from '@ai-sdk/gateway';

prompt: 'Analyze this proprietary business strategy.',

Each response includes metadata showing which providers were considered and which were filtered out. This gives you an audit trail of how your data policies were enforced.

"planningReasoning": "ZDR requested: 5 attempts → 2 ZDR attempts. ZDR execution order: anthropic(system) → bedrock(system)"

All of these filters work with the AI SDK, Chat Completions API, Responses API, Anthropic Messages API, and OpenResponses API.

Protecting data no longer requires custom logic in every route. By moving these rules to the gateway, compliance becomes infrastructure instead of application busywork. You get your control back, and your team gets to keep shipping.

For pricing details, see Zero Data Retention pricing. View the models and providers that support Zero Data Retention and Disallow Prompt Training on the model subpages. Enable Zero Data Retention in your dashboard settings today, or read the documentation for full setup details.

Ready to deploy? Start building with a free account. Speak to an expert for your Pro or Enterprise needs.

Explore Vercel Enterprise with an interactive product tour, trial, or a personalized demo.
