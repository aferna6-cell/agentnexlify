---
source_url: https://thenewstack.io/how-to-build-production-ready-ai-agents-with-rag-and-fastapi/
fetched_at: 2026-04-14T22:16:16Z
category: technical
title: "How to build production-ready AI agents with RAG and FastAPI"
---

# How to build production-ready AI agents with RAG and FastAPI

AI
/


AI Agents
/


AI Engineering



# How to build production-ready AI agents with RAG and FastAPI


Learn how to build reliable, observable, and cost-aware agentic AI systems using RAG, guardrails, cost metering, and a FastAPI API.


Jan 20th, 2026 7:00am by


Oladimeji Sowole




Featured image by ra2 studio on Shutterstock.












Andela sponsored this post.





Agentic AI has shifted from toy demos to the front lines of real products: autonomous research assistants, compliance copilots, ops bots that watch dashboards and file tickets, and Retrieval-Augmented Generation (RAG) copilots wired to enterprise data.

The problem is not "can we make an agent do something clever once?" Rather, it's "can we make agents reliable, observable, cost-aware, and safe every time?"

Achieving this requires a comprehensive, production-focused way to build, secure, and scale agentic AI systems.

This tutorial walks you through a pragmatic blueprint for shipping agentic systems to production. It implements a minimal, production-minded stack with:


- Reasoning and orchestration with a LangChain/LangGraph-style loop.

- RAG vector search and reranking.

- Guardrails such as schema validation and allow/deny.

- Cost and telemetry with token metering and traces.

- Async execution and timeouts, so a flaky tool can't stall the run.

- An API surface (FastAPI) that you can containerize and deploy anywhere.

This project covers production workflows from reasoning loops and RAG to guardrails, telemetry, and cost control, enabling reliable, observable, and affordable deployment of autonomous AI workflows in real-world environments.

## Architecture at a glance


- API layer (FastAPI): Receives a task.

- Agent loop: Reason-act-observe with structured tools.

- RAG: Embed &rarr; retrieve &rarr; rerank &rarr; synthesize.

- Guardrails: Pydantic schema, content filters.

- Cost and telemetry: Usage logs; hooks for OpenTelemetry.

- Async tools: Timeouts/retries.

- Cachin (optional): Semantic cache to cut cost/latency.

## Step 0: Install the essentials

*Production tip: *It's possible to swap the FAISS library for Pinecone/Qdrant and add `opentelemetry-exporter-otlp` for full tracing.

## Step 1: Define robust tool interfaces

Tools should be pure functions (or async) with clear inputs/outputs. Add timeouts and retries to prevent the agent from hanging.

*Why this matters:* It helps isolate I/O, add default timeouts and truncate early to control costs.

## Step 2: Set up RAG with FAISS

The following will embed documents once, then retrieve the top-k at runtime. Add a simple lexical reranking to improve quality without requiring additional model calls.

*Production tip:* Swap lexical for learned rerankers (Cohere/Rerankers) when latency budget allows.

## Step 3: Define guardrails (schemas and content filters)

Ensure the agent's final output matches a schema and passes basic policy checks before returning it to users or downstream systems.

*Why this matters:* Schema validation catches malformed outputs; policy filters stop obvious leaks.

## Step 4: The agent loop (reason &rarr; act &rarr; observe) with cost metering

The following implements a light React-style loop with a max step budget, tool calls, and token usage accounting.

*Cost-aware defaults:* Use a cheaper model (such as `gpt-4o-mini`) for planning/tooling and reserve premium models for critical prompts. Track `usage_metadata` if your software development kit (SDK) provides it. Otherwise, meter tokens are estimated with tiktoken.

## Step 5: FastAPI surface for your agent

Make the agent callable from frontends, cron, or other services. Add timeouts so requests don't hang.

Run it locally:

```
uvicorn app:app --host 0.0.0.0 --port 8080
```

## Step 6: Add simple telemetry and cost logging

Start with a plain logfile; later wire into OpenTelemetry/Prometheus.

Use it inside `agent_run` / `app.py`:

```

# ...after final answer
from telemetry import log_event
log_event(&quot;answer&quot;, tokens=obj.cost_tokens, sources=obj.sources)

```

*Production tip:* Export traces (`opentelemetry-sdk`, OTLP) and dashboard token cost per route/user/workflow.

## Step 7: Make it resilient: Retries, fallbacks, caching


- Retries: Wrap tool calls with exponential backoff.

- Fallbacks: If a premium model fails, degrade to a smaller one and flag the response.

- Semantic cache: Hash the query and retrieved document IDs; if a similar query-context pair has been seen recently, return the cached response.

Skeleton cache:

## Step 8: Evaluate before shipping (agentic eval)

Add a quick, large language model "LLM-as-a-judge" sanity pass for a holdout dataset. Keep it lightweight but repeatable.

Track scores across versions; fail the build if the metrics regress.

## Step 9: Production notes: Deploy and scale


- Containerize with a tiny base image (such as `python:3.11-slim`), pin dependencies, and set `--workers` for Uvicorn.

- Kubernetes:

Requests/limits for CPU/RAM; horizontal pod autoscaler on CPU or custom metric (requests/minute).

- Mount config as secrets/ConfigMaps (model keys, thresholds).

- Sidecar for OpenTelemetry or FluentBit to ship logs.


- Cost controls: Implement per-tenant budgets, route cheap models by default, turn on caching, cap max tokens, and truncate inputs early.

- Safety: Implement content filters (like the `policy_check` above), personally identifiable information (PII) detection for outbound responses, and human-in-the-loop for critical actions.

## Why this blueprint works


- **Separation of concerns**: Tools are independent; the agent loop orchestrates them.

- **Deterministic guardrails**: Schemas and policies gate outputs before they escape.

- **Observability from day one**: Employ basic telemetry now, full tracing later, no rewrites.

- **Cost-aware defaults**: Select cheaper models for planning, truncation, caching, and metering to prevent runaway bills.

- **Portability**: FastAPI and containers make it cloud-agnostic. Add Terraform/K8s when you're ready to scale.

## **Closing thoughts**

Getting an agent to work once is easy. Making it predictable, observable, and affordable is the real job. This pattern gets you there with measured tool use, guardrails that enforce shape and safety, RAG that privileges relevant context, and an API you can monitor and scale.

From here you can:


- Swap FAISS for a managed vector database; add learned reranking.

- Wire OpenTelemetry and set service-level objectives (p95 latency, answer correctness > X).

- Add multiagent patterns (planner/executor/critic) only when the single-agent baseline is stable.

Build the slow-moving parts now, so the details can shine later.












Andela provides the world&#8217;s largest private marketplace for global remote tech talent driven by an AI-powered platform to manage the complete contract hiring lifecycle. Andela helps companies scale teams & deliver projects faster via specialized areas: App Engineering, AI, Cloud, Data & Analytics.




Learn More








The latest from Andela


$(document).ready(function() {
$.ajax({
method: 'POST',
url: '/no-cache/sponsors-rss-block/',
headers: {
'Cache-Control': 'no-cache, no-store, must-revalidate',
'Pragma': 'no-cache',
'Expires': '0'
},
data : {
sponsorSlug : 'andela',
numItems : 3
},
success : function(data) {
if (data == "") {
$('.sponsor-note-rss').hide();
return
}

if (data.startsWith('ERROR')) {
console.log(data)
$('.sponsor-note-rss').hide();
return
}

$('.sponsor-note-rss-items-andela').html(data);
}
});
});






Hear more from our sponsor



Submit





$(document).ready(function () {
var publication = 'thenewstack'

// 1) Enter key on email input triggers submit click
$(document).on('keydown', '.tns-sponsor-note .sponsor-note-lead-form-input', function (event) {
if (event.key === 'Enter') {
event.preventDefault()
$(this).closest('.tns-sponsor-note').find('.sponsor-note-lead-form-submit').trigger('click')
}
})

// 2) If already logged-in, pre-populate the email field
var userCookieJSONPrefill = window.tns.getCookie('tns-user')
if (userCookieJSONPrefill) {
var currentUserPrefill = JSON.parse(userCookieJSONPrefill)
if (currentUserPrefill && currentUserPrefill.email) {
$('.tns-sponsor-note .sponsor-note-lead-form-input').val(currentUserPrefill.email)
}
}

function getStatusBox($root) {
return $root.find('.sponsor-note-lead-form-status')
}

function showSuccessMessage($root) {
var $wrapper = $root.find('.sponsor-note-lead-form-input-wrapper')
var $status = getStatusBox($root)
var wrapperHeight = $wrapper.outerHeight()
$status.css({ height: wrapperHeight + 'px' })
$wrapper.stop().transition({ duration: 250, opacity: 0 }, function () {
$wrapper.css({ display: 'none' })
$status.text("Thank you! We'll share your info with this sponsor.")
$status.css({ display: 'block', opacity: 0 })
$status.stop().transition({ delay: 50, duration: 250, opacity: 1 })
})
}

function showErrorMessageThenRestore($root) {
var $wrapper = $root.find('.sponsor-note-lead-form-input-wrapper')
var $status = getStatusBox($root)
var wrapperHeight = $wrapper.outerHeight()
$status.css({ height: wrapperHeight + 'px' })
$wrapper.stop().transition({ duration: 250, opacity: 0 }, function () {
$wrapper.css({ display: 'none' })
$status.text('Something went wrong on our end, please try again')
$status.css({ display: 'block', opacity: 0 })
$status.stop().transition({ delay: 50, duration: 250, opacity: 1 }, function () {
setTimeout(function () {
$status.stop().transition({ duration: 250, opacity: 0 }, function () {
$status.css({ display: 'none' })
$wrapper.css({ display: 'block', opacity: 0 })
$wrapper.stop().transition({ duration: 250, opacity: 1 })
})
}, 5000)
})
})
}

$(document).on('click', '.tns-sponsor-note .sponsor-note-lead-form-submit', function (event) {
event.preventDefault()

var $sponsorNoteRoot = $(this).closest('.tns-sponsor-note')
if (!$sponsorNoteRoot.length) console.log('[IMGJS] No Sponsor Note found')

var sponsorSlug = ($sponsorNoteRoot.f
