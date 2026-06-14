---
source_url: https://vercel.com/blog/agent-responsibly
fetched_at: 2026-04-24T22:06:47Z
category: technical
title: Agent responsibly - Vercel
---

# Agent responsibly - Vercel

5 min read

The following is based on an internal talk given at Vercel. We're sharing it publicly because the problem it describes isn't unique to us, and the framework is useful for any team shipping with agents.

Coding agents generate code at unprecedented speeds. In the hands of disciplined engineers, they are a productivity multiplier. But without rigorous judgment, they are a highly efficient way to ship bad assumptions directly to production.

When teams deploy agent-generated code blindly, the fallout can be immediate and severe. A flawless-looking pull request can ship a query that passes tests, but scans every row in production. Retry logic that seems correct can cause a thundering herd on a downstream service. And a cache with no TTL can quietly grow until Redis dies.

Green CI is no longer proof of safety. In an agentic world, passing CI is merely a reflection of the agent's ability to persuade your pipeline that a change is safe, even if it will immediately degrade your infrastructure at scale.

## Link to heading False confidence

Agent-generated code is dangerously convincing. It comes with a polished PR description, passes static analysis, follows repository conventions, and includes reasonable test coverage. On the surface, it looks like it was written by an experienced engineer.

But an agent doesn't understand your production environment. It doesn't know your traffic patterns, your failure modes, or the implicit constraints of your shared infrastructure. It doesn't know that a Redis instance is near capacity, that a database is hardcoded to a specific region, or that a feature flag rollout will fundamentally change the load profile of a downstream system.

The gap between "this PR looks correct" and "this PR is safe to ship" has always existed. Agents widen that gap by producing code that looks more flawless than ever, while remaining entirely blind to production realities.

## Link to heading Leveraging vs. relying

There is a fundamental difference between relying on AI and leveraging it.

- Relying means assuming that if the agent wrote it and the tests pass, it's ready to ship. The author never builds a mental model of the change. The result is massive PRs full of hidden assumptions that are impossible to review because neither the author nor the reviewer has a clear picture of what the code actually does.
Relying means assuming that if the agent wrote it and the tests pass, it's ready to ship. The author never builds a mental model of the change. The result is massive PRs full of hidden assumptions that are impossible to review because neither the author nor the reviewer has a clear picture of what the code actually does.

- Leveraging means using agents to iterate quickly while maintaining complete ownership of the output. You know exactly how the code behaves under load. You understand the associated risks. You're comfortable owning them.
Leveraging means using agents to iterate quickly while maintaining complete ownership of the output. You know exactly how the code behaves under load. You understand the associated risks. You're comfortable owning them.

Putting your name on a pull request means "I have read this and I understand what it does." If you have to re-read your own PR to explain how it might impact production, the engineering process has failed.

The litmus test is simple: would you be comfortable owning a production incident tied to this pull request?

## Link to heading Guarding production

The answer isn't to stop using agents. The productivity gains are undeniable and models will only get better. AI-assisted code review and analysis are incredibly powerful tools that catch bugs and surface risks humans miss.

But relying solely on review, whether human or synthetic, is a losing battle against the sheer volume of agent-generated code. We've hit an inflection point where implementation is abundant. The scarce resource is no longer writing code, it's the judgment of what is safe to ship. All infrastructure must match that new reality.

This isn't about wrapping the development lifecycle in red tape. It's about building a closed-loop system where agents can act with high autonomy because their environment is standardized, verification is easy, and deployment is safe by default.

The organizing principle is simple: make the right thing easy to do.

Self-driving deployments. Every change rolls out incrementally through gated pipelines. If a canary deployment degrades, the rollout stops and rolls back automatically. The system doesn't rely on an engineer babysitting a dashboard. It catches the problem, contains it to a fraction of traffic, and reverses it. When something goes wrong, it goes wrong in isolation, not globally.

Continuous validation. The infrastructure tests itself continuously, not just at deploy. Load tests, chaos experiments, and disaster recovery exercises run on an ongoing basis. At Vercel, the database failover we rehearsed in production last summer is the reason a real Azure outage this year was a non-event for our customers. The systems that hold up under pressure are the ones that have been deliberately stressed.

Executable guardrails. At Vercel, we are encoding operational knowledge as runnable tools instead of documentation. A safe-rollout skill isn't a Notion page explaining how feature flags work. It's a tool that wires the flag, generates a rollout plan with rollback conditions, and specifies how to verify expected behavior. When guardrails are executable, agents follow them autonomously and humans don't have to memorize them.

The endgame isn't a world where engineers apply extraordinary rigor to every change. It's a world where the infrastructure itself is rigorous. Where shipping fast is safe by default because the system contains the blast radius, validates continuously, degrades gracefully, and encodes best practices as executable defaults.

## Link to heading What we're investing in

We aren't just theorizing. Our core platform team is actively building these guardrails into shared infrastructure:

- Stronger guardrails around shared infra, with runtime validation at every stage of the deployment pipeline
Stronger guardrails around shared infra, with runtime validation at every stage of the deployment pipeline

- Stricter static checks at PR time, especially around feature flags
Stricter static checks at PR time, especially around feature flags

- Production-mirroring end-to-end testing in staging
Production-mirroring end-to-end testing in staging

- Read-only agents that continuously verify system invariants in production, using specialized agents to audit the assumptions made by generative agents
Read-only agents that continuously verify system invariants in production, using specialized agents to audit the assumptions made by generative agents

- Metrics like defect-commit vs. defect-escape ratios to surface when risk is increasing across the platform
Metrics like defect-commit vs. defect-escape ratios to surface when risk is increasing across the platform

## Link to heading Leverage agents, own the risk

Our bar: leverage agents, don't rely on them.

Low-quality code used to look like low-quality code. That's not the case anymore. AI tools are only going to get more powerful. The diffs will get larger, the code will get more convincing, and the temptation to blindly trust the output will grow. The engineers who thrive won't be the ones who generate the most code. They'll be the ones who maintain ruthless judgment over what they ship.

Before you open your next PR, ask yourself:

- What does this do? How does it behave once rolled out?
What does this do? How does it behave once rolled out?

- How can this adversely impact production or customers?
How can this adversely impact production or customers?

- Am I comfortable owning an incident tied to this code?
Am I comfortable owning an incident tied to this code?

If the answer is yes, you're leveraging AI. Ship it.

If the answer is no, you have more work to do.
