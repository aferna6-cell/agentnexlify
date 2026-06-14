---
title: "Supabase Feb 12 2026 us-east-2 outage: VPC BPA blocked entire region for 3h42m"
category: technical
tags: [supabase, aws, vpc, incident, postmortem, infrastructure, scp, multigres]
sources:
  - url: https://supabase.com/blog/supabase-incident-on-february-12-2026
    title: "Supabase incident on February 12, 2026"
    fetched: 2026-05-05
created: 2026-05-05
updated: 2026-05-05
summary: "A monitoring stack deployment created a VpcBlockPublicAccessOptions resource in block-bidirectional mode, blocking all internet gateway traffic across us-east-2 for 3 hours 42 minutes."
---

Supabase lost the entire us-east-2 (Ohio) region for 3 hours 42 minutes on February 12, 2026, starting at 21:12 UTC. A new internal monitoring service deployment used a shared infrastructure construct that created a VpcBlockPublicAccessOptions resource in `block-bidirectional` mode at the regional level. AWS VPC Block Public Access is a compliance feature that blocks all internet gateway traffic in a region unless specific subnets are explicitly excluded. The deployment created exclusions only for the monitoring service's own subnets — production VPCs (20+ active subnets) received no exclusions and went dark. ALB request counts dropped to zero across the region within minutes. See [[supabase-overview]] for project context and [[aws-vpc-architecture-patterns]] for adjacent infra patterns.

Why detection and resolution took 3h42m: four contributing factors. First, the outage triggered alarms on shared services in a different region, redirecting initial investigation. Second, the `ModifyVpcBlockPublicAccessOptions` event appeared as a single line item in CloudTrail among more visually prominent networking changes in the same deployment. Third, the pre-production environment did not include us-east-2, so the same monitoring stack had run for a week without surfacing the regional BPA impact. Fourth, the right infrastructure teams were not on the incident channel at the start — the outage initially manifested as an API error spike, not a network connectivity loss, and team-paging was reactive. The correlation between the 21:12 deployment timestamp and the start of impact was not made until 00:25 UTC, three hours into the incident.

Mitigation was simple once the cause was identified: destroying the monitoring stack at 00:50 removed the BPA configuration and all dependent VPC resources. Services restored at 00:57. ALB request counts and NAT gateway inbound traffic returned to baseline within minutes. VPC peering, VPN connections, Direct Connect, and AWS PrivateLink were unaffected throughout — the BPA only blocks internet gateway paths, so customers using private networking saw no impact.

Supabase committed to five structural changes. Account isolation: all non-customer-facing services move to separate AWS accounts so auxiliary configuration cannot affect production. External connectivity probes: continuous health checks from outside the network detect complete connectivity loss in seconds rather than minutes. Production-pre-production parity: pre-production now spans every supported production region (the missing us-east-2 coverage is the proximate cause of the missed warning). Faster incident coordination: automated triggers and explicit escalation paths page the right infrastructure teams from the start. Cross-region resilience via Multigres: the future cross-region failover for customer Postgres workloads that can accept added latency, with interim guidance on multi-region patterns.

Already-completed actions: every Supabase region was audited and confirmed clear of VPC BPA, and all IaC stacks were checked for `VpcBlockPublicAccessOptions` references. AWS Organizations Service Control Policies were deployed across pre-production and production AWS organizations to prevent `VpcBlockPublicAccessOptions` and other account/region-scoped resources from being modified outside a dedicated controlled pipeline. The communication postmortem is unusually direct — the company conceded the status page was slow, the dashboard banner was missing, component-level degradation was misreported, social media response lagged, and a previously-scheduled unrelated post went out during the incident.

## Key Concepts

- **VPC Block Public Access (BPA)** — AWS regional security feature that blocks all internet gateway traffic unless specific subnets are excluded; intended for compliance-sensitive environments
- **block-bidirectional mode** — the strictest BPA mode, blocking both inbound and outbound internet gateway traffic at the region level
- **CloudTrail event prominence** — the actual root-cause event appeared as a single line among more visually prominent networking changes; postmortem cites this as a delay factor and motivates better deployment-event tagging
- **Pre-production parity gap** — the monitoring stack ran in pre-production for a week without exposing the BPA impact because pre-production lacked us-east-2; near-zero incremental cost to add, high cost when missing
- **AWS Organizations SCPs** — Service Control Policies that block resource modifications at the org level even when IAM permissions would otherwise allow it; the structural fix for keeping shared destructive resources out of application stacks
- **Multigres** — Supabase's planned cross-region failover capability for customer Postgres databases; interim guidance covers manual multi-region patterns

## Related Articles

- [[supabase-overview]] — Supabase as a platform
- [[supabase-security-2025-retro]] — adjacent infra-security retrospective
- [[aws-vpc-architecture-patterns]] — VPC and IGW architecture context
- [[infrastructure-postmortem-patterns]] — postmortem genre conventions
- [[anthropic-mcp-2026-roadmap]] — separate but adjacent MCP/integration context

## Relevance to AgentNexLiFy

AgentNexLiFy runs on Supabase. The project Supabase region needs verification — if any AgentNexLiFy production data lives in us-east-2, this 3h42m outage was a real customer-facing risk window. The structural lessons translate directly to AgentNexLiFy's own infra discipline. First, the `block-bidirectional` BPA pattern is the kind of "shared destructive resource" that should never live in an application IaC stack; AgentNexLiFy's `migrations/` directory and Railway/Vercel deploy pipelines should be audited for any analogous regional or org-scoped resource creation. Second, pre-production parity matters — staging environments that skip a production region or service are the same gap class. Third, the CloudTrail-prominence problem maps to AgentNexLiFy's own change-event logging — if a destructive migration showed up as one line in `migrations/log.md` next to a verbose schema rename, the same delay pattern would apply. Fourth, the "API error first, network connectivity loss actual" pattern is a reminder to build network-layer probes and not rely solely on application-error alerts. Action: confirm Supabase project region (`mcp__supabase__get_project`), confirm no VpcBlockPublicAccessOptions analog in AgentNexLiFy IaC, document multi-region failover plan even if the answer is "single-region for now."
