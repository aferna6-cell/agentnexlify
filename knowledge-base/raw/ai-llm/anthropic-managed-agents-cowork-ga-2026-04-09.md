---
source_url: https://pasqualepillitteri.it/en/news/755/anthropic-managed-agents-cowork-ga-april-9-2026
fetched_at: 2026-04-27T22:15:12Z
category: ai-llm
title: 'Anthropic Launches Managed Agents and Claude Cowork GA: April 9, 2026'
---

# Anthropic Launches Managed Agents and Claude Cowork GA: April 9, 2026

Skip to content
news
P. Pillitteri
Anthropic Launches Managed Agents and Claude Cowork GA: The Triple Announcement of April 9, 2026
Anthropic announces Claude Managed Agents in public beta, Claude Cowork in general availability with 6 enterprise features (RBAC, OpenTelemetry, Zoom MCP) and Claude Code update. Early adopters Notion, Asana, Sentry.
Pasquale Pillitteri
11/04/2026
Claude Code & Anthropic
8 min read
claude code
ai tools
anthropic
claude managed agents
claude cowork
claude cowork ga
opentelemetry
rbac
notion asana sentry
Table of Contents
April 11, 2026 Update: pricing, credential vault, and first usage data
1.
Claude Managed Agents: Public Beta
What it Includes
Early Adopters: Notion, Asana, Sentry
2.
Claude Cowork: Generally Available (GA)
The 6 New Enterprise Features
3.
Claude Code: The New Update
Reinforced Policy Controls
Setup Wizard for Amazon Bedrock
Detailed Cost Insights
Performance: Large File Writes
Advanced Hooks for Prompt Cache
Interactive Release Notes Picker
4.
The Context: Why This Announcement Now
Competitive Pressure from OpenAI
Enterprise Differentiation
Ecosystem vs Model
5.
What It Means for Developers
What You Can Do From Today
6.
Useful Links and Sources
7.
Other Related Articles on the Blog
8.
Frequently Asked Questions (FAQ)
9.
Conclusions
The Triple Announcement in 5 Points
10.
Rate this article
11.
Related Articles
12.
Looking for a Software Engineer?
On April 9, 2026 Anthropic launched three major updates in a single move that redesign how developers and enterprises use Claude.
Claude Managed Agents
enters public beta,
Claude Cowork
becomes generally available (GA) with six new enterprise features, and
Claude Code
receives a substantial update with policy controls and a Bedrock setup wizard.
The move is strategic: while OpenAI attacks Anthropic in its investor memo claiming infrastructure advantage, Anthropic responds by accelerating on the developer-focused product ecosystem. Let us see in detail what changes.
The triple Anthropic announcement of April 9, 2026
April 11, 2026 Update: pricing, credential vault, and first usage data
Three days after launch, Anthropic has clarified the economic and technical details of
Managed Agents
, currently in public beta on the Claude Platform. Pricing is more structured than expected:
Standard API tokens
: Sonnet 4.6 at $3/$15 per million input/output tokens, Opus 4.6 at $5/$25 per million.
Active session
: $0.08 per hour of active runtime, measured in milliseconds. If the agent stays idle, you don't pay.
Integrated web search
: $10 per 1,000 searches via native tool.
On the security front, the
credential vault
is a key component I didn't highlight in the original article: Managed Agents stores secrets encrypted and makes them available to the agent at runtime without exposing them in code or logs. The vault supports
native OAuth for ClickUp, Slack, and Notion
, with automatic authentication flows, and for custom tools it accepts OAuth tokens stored via MCP (Model Context Protocol).
The official endpoints are two:
POST /v1/agents
to create a persistent agent with system prompt, tools, and permissions, and
POST /v1/sessions
to start an execution session. The
Claude Agent SDK Python
abstracts both via
ClaudeSDKClient
as an async context manager.
For the practical side with code examples and comparison with OpenAI's Responses API
, I wrote a dedicated technical guide.
Claude Managed Agents: Public Beta
Claude Managed Agents
is a suite of composable APIs for building and deploying cloud-hosted agents at enterprise scale. In short, Anthropic now offers a managed harness to run Claude as an autonomous agent, without worrying about infrastructure, sandboxing or permission management.
What it Includes
Production infrastructure:
Anthropic handles runtime, scaling and monitoring
Secure sandboxes:
isolated containers for each agent session
Built-in tools:
access to tools like code execution, web browsing, file operations
Server-Sent Event streaming:
real-time responses via API
Composable APIs:
you can combine primitives to create custom workflows
State and permission management:
natively handled by the service
Anthropic key promise:
go from prototype to production in 'days rather than months', eliminating manual work on secure infrastructure, state management and permissioning.
Early Adopters: Notion, Asana, Sentry
Among the first to adopt Managed Agents are
Notion
,
Asana
and
Sentry
. Three very different companies but all sharing the need to integrate deep agentic capabilities into their products:
Notion:
presumably for workspace AI features (document generation, page automation, database analysis)
Asana:
likely for automatic task planning, smart assignment and project summaries
Sentry:
for automatic stack trace analysis, bug diagnosis and incident prioritization
The service is available today on the
Claude Platform
for all builders, not just selected enterprise partners.
Claude Cowork: Generally Available (GA)
Claude Cowork
moves from research preview to general availability. It is now available for all paying subscribers on
macOS and Windows
in the Claude Desktop app. For those unfamiliar, Cowork is Anthropic autonomous AI assistant that works in the background while you do other things.
The 6 New Enterprise Features
With GA come six features designed specifically for the business world:
Role-Based Access Controls (RBAC):
admins can configure access by team and department
Group Spend Limits:
spending limits for user groups, useful for budget control
Expanded Usage Analytics:
detailed dashboards on usage, costs and interaction patterns
OpenTelemetry Support:
native integration with enterprise observability systems
Zoom MCP Connector:
new integration for meetings and transcriptions
Per-Tool Connector Controls:
granular controls on which tools and connectors each user can use
Feature
Plan
Target
RBAC
Enterprise
IT Admin
Group Spend Limits
Enterprise
Finance Ops
Usage Analytics
Team/Enterprise
Admin
OpenTelemetry
Enterprise
DevOps
Zoom MCP Connector
All paid plans
End user
Per-Tool Controls
Team/Enterprise
Security admin
If you don't know Cowork, read my
complete guide to Claude Cowork
with the 5 most useful use cases.
Claude Code: The New Update
Along with the two main launches,
Claude Code
receives a substantial update that improves several aspects for enterprise developers and advanced use cases.
Reinforced Policy Controls
The new policy controls allow defining more granular rules on:
Which shell commands Claude can execute
Which files it can read or modify
Which MCP tools are authorized
Rate limiting for expensive operations
A long-awaited feature in enterprise contexts where permission control is critical.
Setup Wizard for Amazon Bedrock
Configuring Claude Code with
Amazon Bedrock
was historically a complicated step. Now Anthropic includes an interactive wizard that guides step-by-step through AWS credentials, region, profile and model selection. Essential for companies using Bedrock for compliance and data residency reasons.
Detailed Cost Insights
The
/cost
command has been enhanced with even more granular metrics:
Cost per task type
Input vs output token breakdown
Comparison between models used in the session
Monthly cost projection based on current usage
Cost hit of the most used tools
Performance: Large File Writes
Write operations on large files (over 10k lines) have been optimized. According to Anthropic tests, times have dropped by 40-60% thanks to a new buffering algorithm and batching of disk operations.
Advanced Hooks for Prompt Cache
New hints for prompt caching that allow Claude Code to be more efficient in context reuse between consecutive calls, reducing costs and increasing response speed. If you don't know hooks, read my
complete guide to Claude Code Hooks
.
Interactive Release Notes Picker
A small but useful detail: the new interactive picker to view release notes directly in the terminal. You can now navigate between versions, filter by change type (feature, bugfix, breaking) and see only what interests you.
The Context: Why This Announcement Now
Anthropic does not announce three updates in one day by chance. There are three strategic factors:
1. Competitive Pressure from OpenAI
On April 9 itself, OpenAI sent a memo to investors attacking Anthropic, claiming it plans
30 gigawatts of compute by 2030
against Anthropic's
7-8 gigawatts
expected by end of 2027. An attempt to position itself as the only real frontier lab with industrial scale.
Anthropic responds not on compute quantity but on
product quality
: Managed Agents, Cowork GA and Claude Code updates are the demonstration that the company builds developer-first infrastructure, not just raw models.
2. Enterprise Differentiation
The six Cowork features (RBAC, spend limits, OpenTelemetry, etc.) are all enterprise-oriented. Anthropic is betting ever more decisively on the business segment, where margins are high and retention is superior to consumer.
3. Ecosystem vs Model
While others focus on 'the biggest model', Anthropic is building an
ecosystem
: Claude Code for developers, Cowork for knowledge workers, Managed Agents for platforms wanting to integrate Claude, and Mythos for cybersecurity. A more distributed and defensive strategy.
What It Means for Developers
For those working with Claude every day, today announcements open three new scenarios:
What You Can Do From Today
Build cloud-hosted agents
without managing infrastructure thanks to Managed Agents
Deploy Claude as a service
in your products with automatic scaling
Control enterprise permissions
on Cowork with RBAC and group spend limits
Monitor usage
with native OpenTelemetry
Configure Bedrock
in minutes thanks to the new setup wizard
Useful Links and Sources
Claude Platform
Anthropic Documentation
9to5Mac: Anthropic Scales Up Enterprise Features
Startup Fortune: Anthropic Unveils Managed Agents
Releasebot: Claude Code Release Notes
Other Related Articles on the Blog
Claude Code: The Definitive Guide with 45+ Articles
- the pillar with all Claude articles
Claude Code Hooks: Complete Guide
Claude Cowork: The Autonomous AI Assistant
Superpowers for Claude Code
Frequently Asked Questions (FAQ)
1. Is Claude Managed Agents available to everyone?
Yes, Managed Agents is in public beta and available to all builders on the Claude Platform.
No special invitation needed, you can start right away using the service composable APIs.
2. Who are the Managed Agents early adopters?
The first to adopt it are Notion, Asana and Sentry.
Three companies that have already integrated Managed Agents into their production workflows before public launch.
3. Is Claude Cowork GA free?
No, Cowork is available for all paying subscribers (Pro, Team, Enterprise).
The six new enterprise features are included in Team and Enterprise plans depending on the specific feature.
4. How do I configure Claude Code with Amazon Bedrock after the update?
Run the claude bedrock setup command and follow the interactive wizard.
The wizard guides step-by-step through AWS credentials, region and model configuration.
5. Is Cowork OpenTelemetry support compatible with Datadog/Grafana?
Yes, OpenTelemetry is an open standard supported by Datadog, Grafana, New Relic, Honeycomb and all major observability systems.
Just configure the OTLP endpoint in Cowork enterprise settings.
6. Are Managed Agents safer than DIY agents?
Yes, because Anthropic directly manages isolated sandboxes, permission management and rate limiting.
Each agent session runs in a dedicated container with security controls that would be complex to implement independently.
7. Does updated Claude Code still work with existing projects?
Yes, the update is backward compatible.
Policy controls are opt-in and do not change the behavior of already configured workflows. The update installs automatically with npm update -g @anthropic-ai/claude-code.
Conclusions
The Triple Announcement in 5 Points
Managed Agents
in public beta: managed agentic infrastructure for all
Cowork GA
with 6 enterprise-first features (RBAC, spend limits, OpenTelemetry)
Claude Code
updated with policy controls, Bedrock wizard and cost insights
Prestigious early adopters
like Notion, Asana and Sentry validate the strategy
Anthropic responds to OpenAI
betting on developer ecosystem, not compute quantity
For personalized consulting on how to integrate Claude Managed Agents, Cowork or Claude Code into your business workflows, fill out the contact form at the bottom of the page. I update this guide every time Anthropic releases relevant news.
Share
Rate this article
★
★
★
★
★
Thanks for your rating!
Related Articles
Claude Code & Anthropic
10 Advanced Prompts for Claude Design: The Senior UX Designer Workflow
Tool AI & Recensioni
10 Open-Source AI Agent Frameworks to Automate Your Work in 2026
Claude Code & Anthropic
Anthropic Retires the 1M Context Beta: Migrate Before April 30, 2026
✉
Stay updated
Looking for a Software Engineer?
Do you have an application, management system or software to develop?
Have you suffered a cyber attack?
Looking for a qualified Innovation Manager?
Fill out the form
×
✉
Stay updated
Subscribe to the newsletter to receive new articles directly in your inbox.