---
source_url: https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/
fetched_at: 2026-04-30T22:19:03Z
category: ai-llm
---

# The 2026 MCP Roadmap

**Author:** David Soria Parra (Lead Maintainer)
**Date:** March 9, 2026

## Overview

The Model Context Protocol released its current specification in November 2025 and has matured from local tool integration to production deployments across enterprises. The 2026 roadmap organizes around priority areas rather than release milestones, with Working Groups driving protocol development.

## Key Priority Areas

### Transport Evolution and Scalability
The Streamable HTTP transport enables remote MCP servers but faces production challenges at scale. Two components:

1. **Transport & Session Model Evolution** — horizontal scaling without stateful session requirements; explicit session handling mechanisms
2. **Metadata Discovery** — `.well-known` standard format for server capability discovery without live connections

The team is "not adding more official transports this cycle but evolve the existing transport."

### Agent Communication
The Tasks primitive (SEP-1686) shipped experimentally and requires refinement based on real-world usage. Planned iterations:
- Retry semantics for transient failures
- Result retention expiry policies

### Governance Maturation
Current bottlenecks require Core Maintainer review for every SEP regardless of domain. Improvements:
- Documented contributor ladder for community-to-maintainer progression
- Delegation model — specialized Working Groups approve SEPs within their expertise
- Maintained strategic Core Maintainer oversight

### Enterprise Readiness
Production deployments surface consistent needs:
- Audit trails
- SSO-integrated authentication
- Gateway behavior
- Configuration portability

Roadmap notes this priority is "intentionally" least-defined, inviting enterprise infrastructure experts to shape requirements.

## SEP Prioritization
SEPs aligned with priority areas receive expedited review. Proposals outside these areas face longer timelines and higher justification standards. Contributors should:
1. Map proposals to priority areas
2. Engage relevant Working Groups before submission

## On the Horizon
Community interest, no active Core Maintainer support:
- Triggers and event-driven updates
- Streamed and reference-based result types
- Enhanced security and authorization frameworks
- Extensions ecosystem maturation

Active proposals: **SEP-1932 (DPoP)** and **SEP-1933 (Workload Identity Federation)**.

## Participation Pathways
- Join existing Working Groups
- Propose SEPs following established guidelines
- Develop extensions outside core specifications
