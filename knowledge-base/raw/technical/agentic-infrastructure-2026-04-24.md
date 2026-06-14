---
source_url: https://vercel.com/blog/agentic-infrastructure
fetched_at: 2026-04-24T22:06:47Z
category: technical
title: Agentic Infrastructure - Vercel
---

# Agentic Infrastructure - Vercel

4 min read

Every generation of software eventually demands a new generation of infrastructure.

- First, we configured servers by hand.
First, we configured servers by hand.

- Next, the cloud turned infrastructure into APIs.
Next, the cloud turned infrastructure into APIs.

- Then, a more important shift: infrastructure derived from the application itself.
Then, a more important shift: infrastructure derived from the application itself.

LLMs and coding agents are driving the next transition, and it's happening fast.

In just three months, weekly deployments on Vercel have doubled, and agents are driving the growth. Today, over 30% of deployments are initiated by coding agents, up 1000% from six months ago. Claude Code accounts for 75%, Lovable and v0 for 6%, and Cursor for 1.5%.

### Link to heading Software is now agentic

Agents are building, testing, and shipping AI-native software, and they're doing it at a velocity that breaks traditional operations. Vercel projects deployed by coding agents are 20 times more likely to call AI inference providers than those deployed by humans. Agents are writing software that uses AI, and agents are building agents.

As the final actor shifts from human to machine, infrastructure has to adapt again. It has to work for software that acts on behalf of users, writes itself, and increasingly needs to understand its own behavior in production. This new generation of agentic software demands Agentic Infrastructure .

It’s not one evolution, but three:

- Infrastructure for coding agents to deploy to
Infrastructure for coding agents to deploy to

- Infrastructure for building and running agents
Infrastructure for building and running agents

- Infrastructure that itself is agentic
Infrastructure that itself is agentic

## Link to heading 1. Infrastructure for coding agents to deploy to

The bottleneck for agentic engineering is operational friction.

When a coding agent writes a feature, it requires a place to run, test, and verify the output, which ultimately means it needs a URL. If the path from code to running system involves manual Terraform state or clicks in a cloud console UI, the autonomous loop breaks. Agents need programmatic, deterministic deployment surfaces.

This is why immutable deployments , preview URLs on every commit, and instant rollbacks aren't just developer experience upgrades anymore. They are absolute prerequisites for machine-driven software development.

Vercel's CLI , API , MCP servers , and git integration give agents native access to a deployment surface where they can generate code, open a PR, get a preview URL, verify the output, and ship to production, all without human intervention.

## Link to heading 2. Infrastructure for building and running agents

Serverless workloads need functions, caching, and short-lived requests at the edge, but managing that stack yourself means config drift and hours debugging across systems. Vercel solved that by unifying every layer into the frontend cloud.

Agent workloads are a fundamentally different shape. They require long-lived execution, multi-step orchestration, model routing, cost controls, sandboxed code execution, and abuse resistance. It's a more complex stack, and the penalty for running it yourself compounds: every wasted request burns inference dollars, provider outages take your agent offline, and untrusted code opens the door to prompt injection.

Vercel's agentic infrastructure unifies every AI primitive we've built into a single, secure platform, the same way we did for serverless.

- AI SDK gives developers a unified way to build AI-powered applications across frameworks and providers, and AI SDK 6 adds an agent abstraction so developers can define an agent once and reuse it across interfaces and workflows.
AI SDK gives developers a unified way to build AI-powered applications across frameworks and providers, and AI SDK 6 adds an agent abstraction so developers can define an agent once and reuse it across interfaces and workflows.

- Chat SDK makes agents available across dozens of chat apps and platforms from a single codebase.
Chat SDK makes agents available across dozens of chat apps and platforms from a single codebase.

- AI Gateway gives teams a single endpoint for hundreds of models, with budgets, monitoring, routing, retries, and fallbacks.
AI Gateway gives teams a single endpoint for hundreds of models, with budgets, monitoring, routing, retries, and fallbacks.

- Fluid compute is designed for the unusual shape of AI workloads, where latency, concurrency, and idle waiting all matter at once.
Fluid compute is designed for the unusual shape of AI workloads, where latency, concurrency, and idle waiting all matter at once.

- Workflows and Queues give agents a way to pause, resume, retry, maintain state, and offload background work.
Workflows and Queues give agents a way to pause, resume, retry, maintain state, and offload background work.

- Sandbox gives them isolated execution environments for untrusted code.
Sandbox gives them isolated execution environments for untrusted code.

- Observability lets teams trace what agents are doing and where they are going wrong.
Observability lets teams trace what agents are doing and where they are going wrong.

Together, these building blocks give developers everything they need to build and run agents in one place. But Vercel also puts each of them into a single system with shared context: code, model calls, and runtime behavior. That context is what turns the infrastructure itself into an agent.

## Link to heading 3. Infrastructure that is itself agentic

Traditional infrastructure is a one-way street: code goes in, logs come out, and a human reads the logs to fix the code. A unified platform provides complete visibility across every layer in real time, giving agents the ability to not just monitor production, but autonomously respond to it.

When a latency spike hits a critical route or a model provider drops requests, Vercel doesn't wait for a human to notice. It investigates the anomaly, queries observability data, reads logs, inspects source code, performs root-cause analysis, and reviews proposed fixes in isolated sandboxes. The platform interprets what the developer intended, observes what the system actually did, and acts on the delta.

Today, that still happens with human approval in the loop. Over time, the platform will take on more of that operational burden, not because it's replacing developers, but because it has enough context to act on their behalf.

## Link to heading Where we're going

The history of cloud computing is the history of removing the human from the machine. Agentic infrastructure is the next evolution, moving us from passive tools that wait for commands to proactive systems that act on our behalf.

The companies that win the next decade will build on infrastructure that expects software to write, ship, and heal itself.
