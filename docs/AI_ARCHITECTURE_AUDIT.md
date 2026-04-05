# AI Architecture Audit

_Last updated: 2026-04-05_

## Purpose
This document maps the current production AI surfaces in AgentNexLiFy, with emphasis on:
- model call sites
- context sources available to AI
- structured/model-driven side effects
- trust boundaries and tenant isolation
- what is deterministic vs model-driven
- hardening priorities

## Executive Summary
AgentNexLiFy uses AI in multiple layers:
1. **Customer-facing runtime AI** — widget chat, action-item extraction, categorization, tagging, AI email generation, content repurposing, intelligence briefs
2. **Knowledge and retrieval helpers** — website crawl ingestion, FAQ/business knowledge, embeddings utilities
3. **External assistant tool surface** — MCP server exposing tenant business data as tools
4. **Developer agent system** — separate from runtime product AI; documented in `CLAUDE.md`, `.ai/manifest.json`, `.claude/*`, and `.codex/*`

The core runtime widget path is reasonably centralized around `backend/services/llm_runtime.py`, but several Anthropic call sites still bypass the shared wrapper.

## Core Runtime AI Surfaces

### 1. Widget Chat
**Primary files:**
- `backend/routers/widget_chat.py`
- `backend/routers/widget_helpers.py`
- `backend/services/llm_runtime.py`

**Role:**
Customer-facing assistant embedded on tenant websites.

**Primary context sources:**
- tenant metadata (`tenants`)
- widget config (`widget_configs`)
- FAQ entries (`faq_entries`)
- business hours (`business_hours`)
- owner corrections (`ai_feedback`)
- crawled website content (`website_content`)
- explicit knowledge base/custom instructions (`widget_configs` fields)
- menu items (`menu_items`)
- job listings (`jobs`)
- bid templates (`bid_templates`)
- lead field definitions
- active chat flow (`chat_flows`)
- recent conversation history (`chat_messages`)

**Current shape:**
Mostly prompt assembly / prompt stuffing rather than retrieval from embeddings.

### 2. Widget Post-Processing AI
**Primary files:**
- `backend/routers/widget_helpers.py`

**Capabilities:**
- tag extraction
- conversation categorization
- action item extraction

**Notes:**
These use Claude through the shared `llm_runtime` wrapper and operate on recent transcript windows.

### 3. Automation AI
**Primary file:**
- `backend/services/automation_engine.py`

**Capabilities:**
- AI-generated follow-up emails
- AI-generated weekly intelligence briefs

**Context sources:**
- recent conversation history
- FAQ entries
- tenant metadata
- campaign/lead/appointment/invoice/review metrics

**Current issue:**
Some of these call Anthropic directly instead of routing through the shared runtime wrapper.

### 4. Content Repurposer
**Primary file:**
- `backend/services/content_repurposer.py`

**Capabilities:**
- repurpose raw text / URL / YouTube transcript into:
  - X threads
  - LinkedIn carousel outlines
  - email sequences
  - TikTok scripts
  - platform-specific social posts

**Current issue:**
Direct Anthropic call instead of shared runtime wrapper.

### 5. Embeddings Utilities
**Primary file:**
- `backend/services/embeddings.py`

**Provider:**
- Voyage AI (`voyage-3-lite`)

**Current state:**
Embeddings helpers exist, but they are not in the hot path for widget chat.

### 6. Website Crawl Ingestion
**Primary file:**
- `backend/services/website_crawler.py`

**Role:**
Collect public website content and store extracted text for use in prompt context.

**Risk:**
Website text is business-owned but still effectively untrusted content from a prompt-injection perspective.

### 7. MCP Server
**Primary file:**
- `backend/mcp_server.py`

**Role:**
Expose tenant business data as tools for external AI assistants.

**Current state (after safety pass):**
- dedicated MCP keys only
- widget/embed API keys are no longer accepted for MCP auth

## Model / Embedding Call Inventory

### Shared runtime wrapper
- `backend/services/llm_runtime.py`
  - `call_claude_messages_sync`
  - `call_claude_messages`

### Runtime wrapper users
- widget tagging / categorization / action items (`widget_helpers.py`)
- other wrapped widget/chat paths through `widget_chat.py`

### Direct Anthropic users (technical debt)
- `backend/services/content_repurposer.py`
- parts of `backend/services/automation_engine.py`

### Embeddings
- `backend/services/embeddings.py`
  - Voyage API calls for document/query embeddings

## Model-Driven Side Effects

### Directly structured side effects from model output
**Primary file:** `backend/routers/widget_booking.py`

The widget model can emit structured markers embedded in response text:
- `HANDOFF_REQUESTED`
- `<!--ORDER_JSON:...-->`
- `<!--BID_REQUEST:...-->`

These markers can trigger downstream actions such as:
- human handoff routing
- order creation
- bid/action-item creation

### Hardening status
After the safety-first pass:
- order payloads are schema-validated more strictly
- bid request payloads are schema-validated more strictly
- malformed or suspicious payloads are rejected before side effects occur

### Remaining risk
The system still relies on model-emitted control markers. This is acceptable only if:
- payloads remain tightly validated
- untrusted prompt sources are clearly delimited
- downstream side effects remain narrowly scoped

## Tenant Isolation / Trust Boundaries

### Stronger boundaries now in place
- MCP access requires dedicated MCP keys, not widget keys

### Still-sensitive boundaries
- widget prompt context is assembled from many tenant-owned sources
- crawled website text can carry prompt-injection-like content
- feedback corrections are inserted into instruction space and should be treated as high-trust but still auditable
- caches are per-worker and not globally authoritative

### Important schema discipline
- `leads` uses `client_id`
- `conversations` uses `client_id`
- `chat_messages` uses `tenant_id`

Misunderstanding those boundaries remains a major operational risk.

## Deterministic vs Model-Driven

### Deterministic
- lead scoring (`backend/services/lead_scoring.py`)
- website crawl orchestration and storage
- most automation sequencing / scheduling logic
- MCP tool data retrieval
- order/bid persistence after parsed payload acceptance

### Model-driven
- widget responses
- tagging / categorization / action-item extraction
- AI email generation
- content repurposing
- weekly intelligence summaries

### Hybrid
- model suggests structured actions; deterministic code validates and executes them

## Main Risks

### High
1. Model-output control markers can still influence side effects
2. Prompt injection via crawled website content and freeform knowledge/correction text
3. Multiple direct Anthropic call sites bypass shared control/logging policy

### Medium
1. Drift between docs and live AI architecture
2. Embeddings exist but are not wired into main retrieval path, which may create false assumptions about RAG quality
3. Worker-local cache/state can cause uneven behavior across processes

## Hardening Priorities
1. Route all Anthropic calls through `backend/services/llm_runtime.py`
2. Delimit untrusted prompt sources explicitly as reference material, not instructions
3. Keep structured side-effect payload validators strict and add tests around them
4. Add explicit audit logging when model-driven side effects are accepted or rejected
5. Document model-role boundaries clearly in the agent system plan

## Recommended Next Implementation Steps
1. Centralize remaining direct Anthropic call sites
2. Add prompt sanitization/delimiting for website content and corrections
3. Add tests for order/bid payload validation
4. Add a dedicated doc for runtime prompt assembly and control flow if widget complexity keeps growing
