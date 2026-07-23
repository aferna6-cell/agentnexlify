---
source_url: https://releasebot.io/updates/anthropic/claude-developer-platform
fetched_at: 2026-07-23T00:00:00Z
category: ai-llm
---

# Claude Developer Platform Release Notes: June-July 2026

## July 22, 2026 — Claude Managed Agents Capabilities Expansion

New features include model effort level configuration via the `effort` parameter, expanded webhook coverage for environment and memory store lifecycle events (four `environment.*` and three `memory_store.*` event types), session seeding with up to 50 initial `user.message` and `user.define_outcome` events, optional `version` field for agent updates, and event delta support on thread streams via `GET /v1/sessions/{session_id}/threads/{thread_id}/stream`.

## July 17, 2026 — Legacy Workbench and Prompt Tools API Sunset

"The legacy **Workbench** (platform.claude.com/workbench) in the Claude Console is being sunset with access ending on August 17, 2026." Saved prompts, variables, and evals lack support in the updated version. Users may export data from banners and Organizational Settings. The experimental prompt tools APIs (`/v1/experimental/generate_prompt`, `/v1/experimental/improve_prompt`, `/v1/experimental/templatize_prompt`) are retiring simultaneously; post-removal requests return errors.

## July 15, 2026 — Mid-Conversation System Messages General Availability

"Mid-conversation system messages are available on Claude Fable 5, Claude Mythos 5, and Claude Opus 4.8, on the Claude API, Claude in Amazon Bedrock, and Google Cloud. No beta header is required."

## July 14, 2026 — Admin API Beta for Claude Enterprise

New user management capabilities enable admins to list/lookup members by email, modify roles, remove members, manage invites and groups, and read custom roles. Group and custom-role requests require the `anthropic-beta: ce-user-management-2026-07-13` header; member and invite requests require none. Keys with `read:org_audit` scope access all user-management `GET` endpoints.

## July 10, 2026 — Dreams Model Support and Access Transparency Expansion

Dreams (research preview) now supports Claude Fable 5 and Claude Sonnet 5. Access Transparency documentation expanded with `cmek_preserve` filter examples, event payload details, and two new preservation reason codes: `policy_violation_investigation` and `csae_report`.

## July 8, 2026 — API Key Expiration Settings

"You can now set an expiration when you create an API key or an Admin API key in the Claude Console." Options include preset durations, custom duration, or **Never**. Keys with 7+ day lifetimes trigger pre-expiration emails. The Admin API reports expiration via the `expires_at` field.

## July 2, 2026 — Agent Memory Beta Header Update

The `agent-memory-2026-07-22` beta header changes memory listing (`GET /v1/memory_stores/{memory_store_id}/memories`) behavior: results appear in stable server-defined order (ignoring `order_by` and `order` parameters), `depth` accepts only `0`, `1`, or omission, and `path_prefix` requires trailing `/` with whole-segment matching. This header replaces `managed-agents-2026-04-01` on memory store endpoints; sending both returns a 400 error. On July 22, 2026, `managed-agents-2026-04-01` adopts identical list behavior.

All SDKs (Python 0.116.0, TypeScript 0.110.0, Go 1.56.0, Java 2.48.0, Ruby 1.55.0, PHP 0.36.0, C# 12.35.0, CLI 1.16.0) now send `agent-memory-2026-07-22` by default.

## July 1, 2026 — Claude Fable 5 and Mythos 5 Access Restoration

Access restored to Claude Fable 5 and Claude Mythos 5 models.

## June 30, 2026 — Claude Sonnet 5 Launch and Managed Agents Expansion

**Claude Sonnet 5** (`claude-sonnet-5`) introduces 1M token context window, 128k max output tokens, and three behavior changes: adaptive thinking defaults to enabled, manual extended thinking (`thinking: {type: "enabled", budget_tokens: N}`) removed (returns 400 error), and non-default sampling parameters return 400 error. New tokenizer produces ~30% more tokens. Introductory pricing: $2/$10 per MTok through August 31, 2026 (standard $3/$15 thereafter).

Claude Managed Agents enhancements include event delta streaming via `event_deltas[]` query parameter on `GET /v1/sessions/{session_id}/events/stream`, backward pagination with `prev_page` cursor on `GET /v1/sessions`, session-level agent configuration overrides using `type: "agent_with_overrides"`, vault credential `injection_location` setting (request headers, body, or both), and webhooks covering agent, deployment, and deployment run lifecycle.

## June 29, 2026 — Fast Mode Removal for Claude Opus 4.6

"We've removed fast mode for Claude Opus 4.6. Requests to `claude-opus-4-6` with `speed: "fast"` no longer run at fast speed or premium pricing: they run at standard speed, are billed at standard rates, and do not return an error."

## June 26, 2026 — API Rate Limits Increase and Usage Tier Simplification

Rate limits increased across Claude API. Claude Sonnet and Haiku limits now match Claude Opus at all tiers. Usage tiers consolidated into three: Start, Build, and Scale. No organization receives lower limits than before; most advance to higher tiers.

## June 25, 2026 — Fast Mode Deprecation for Claude Opus 4.7

"We've deprecated fast mode for Claude Opus 4.7, with removal on July 24, 2026." Users directed to migrate to Claude Opus 4.8 fast mode.

## June 18, 2026 — Code Execution Tool SDK Support

Python, TypeScript, Go, Java, Ruby, PHP, and C# SDKs now support `code_execution_20260120`, adding REPL state persistence and programmatic tool calling requirements. Set `type` to `code_execution_20260120`; no beta header required. Compatible with Claude Fable 5, Mythos 5, Opus 4.5+, and Sonnet 4.5+.

## June 15, 2026 — Model Retirements

"We've retired the Claude Sonnet 4 model (`claude-sonnet-4-20250514`) and the Claude Opus 4 model (`claude-opus-4-20250514`). All requests to these models will now return an error." Migration recommended to Claude Sonnet 4.6 and Opus 4.8 respectively.

## June 11, 2026 — New Tool Versions with Response Inclusion

Code execution tool supports `code_execution_20260521`, disclosing 90-second per-cell execution time limits. Web search and web fetch tools support `web_search_20260318` and `web_fetch_20260318`, adding `response_inclusion` parameter to drop consumed result blocks from responses for agentic workflows. No beta headers required.

## Related July 2026 platform context (from search, 2026-07-23)

- Fast mode for Claude Opus 4.7 deprecated with removal July 24, 2026; migrate to Opus 4.8 fast mode.
- Claude Opus 4.1 deprecation announced; retirement on the Claude API August 5, 2026; migrate to Opus 4.8.
- Anthropic added self-serve HIPAA configuration for Enterprise and API organizations — eligible admins review the BAA and enable HIPAA configuration in a single flow.
