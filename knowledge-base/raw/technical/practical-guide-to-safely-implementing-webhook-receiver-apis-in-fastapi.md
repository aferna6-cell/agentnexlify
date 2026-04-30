---
source_url: https://blog.greeden.me/en/2026/04/07/a-practical-guide-to-safely-implementing-webhook-receiver-apis-in-fastapi-from-signature-verification-and-retry-handling-to-idempotency-and-asynchronous-processing/
fetched_at: 2026-04-24T10:06:38Z
category: technical
title: Practical Guide to Safely Implementing Webhook Receiver APIs in FastAPI
---

# Practical Guide to Safely Implementing Webhook Receiver APIs in FastAPI

Source: https://blog.greeden.me/en/2026/04/07/a-practical-guide-to-safely-implementing-webhook-receiver-apis-in-fastapi-from-signature-verification-and-retry-handling-to-idempotency-and-asynchronous-processing/

# A Practical Guide to Safely Implementing Webhook Receiver APIs in FastAPI: From Signature Verification and Retry Handling to Idempotency and Asynchronous Processing

## Summary

- A webhook receiver API is not just “an endpoint that accepts POST requests.” In real-world systems, you need to design for authenticity verification of the sender, tamper protection, tolerance to retries, timeout avoidance, and auditability . Stripe recommends using its official library for signature verification, and GitHub also strongly recommends signature verification using a secret.

- In FastAPI, the safe pattern is to obtain the raw request body from Request , verify the signature first, and only then route the request to processing logic for each event type. If you modify the body before verification, validation is likely to fail. Stripe also explicitly instructs developers to use the unmodified request body.

- In production, it is more stable not to complete heavy business processing inside the webhook endpoint itself. Instead, the recommended approach is to verify, record, return an ACK quickly, and offload downstream processing to background tasks or a job queue . FastAPI’s BackgroundTasks is suitable for lightweight post-response processing.

- In this article, I will organize a safe FastAPI webhook implementation in the following order: basic design → signature verification → idempotency → retry/out-of-order handling → audit logs → testing , while incorporating the design ideas of Stripe and GitHub and presenting them as a practical pattern with reduced provider dependency.

## Who will benefit from reading this

### Individual developers and learners

- People who want to receive payment completion events or GitHub events in FastAPI, but still have only a vague understanding of how to build webhooks safely.

- People thinking, “Can’t I just receive the POST and update the database?” but wanting to understand what else is needed once signature verification and retry handling are taken into account.

For these readers, the main value is establishing the idea that a webhook is an authenticated external event entry point , then learning a pattern that starts from the minimum structure and moves toward a safer design. Both Stripe and GitHub emphasize signature verification using a shared secret.

### Backend engineers in small teams

- Engineers who have started dealing with multiple webhooks such as payments, GitHub, and external SaaS events, and whose endpoint design and retry handling are becoming scattered.

- Engineers who want to avoid timeouts and duplicate processing while organizing the parts that can be shared.

For these readers, the most useful part will be the role separation of “receive, verify, record, ACK, downstream processing,” and the way to divide signature verification, event ID persistence, and job dispatch. General webhook best practices also emphasize authenticity checks, retries, idempotency, and quick responses.

### SaaS teams and startups

- Teams for whom payment integrations and external event integrations are business-critical, where missed events or duplicate processing directly affect revenue and customer experience.

- Teams that want to build a receiver foundation on FastAPI that remains robust, auditable, and retry-tolerant even as the number of event types grows in the future.

For these readers, the key value is a design in which event reception is separated from business processing and flowed into audit logs, an idempotency table, and a job queue . GitHub and Stripe both show that webhooks should be handled only after signature verification and designed with failure and retries as normal conditions.

## Accessibility evaluation

- A summary is placed first, followed by a step-by-step structure of “why it is dangerous,” “how to protect it,” and “how to implement it in FastAPI.”

- Technical terms are briefly explained at first appearance and then used consistently afterward.

- Code is split into short sections so that each part can be viewed by role.

- The target level is equivalent to AA.

## 1. Why should a webhook receiver API be built more carefully than a normal POST API?

A webhook is a notification that an external service actively sends to your server. For example, events like “payment succeeded,” “invoice failed,” or “repository updated” arrive from outside. GitHub recommends that the receiving server perform signature verification before processing webhook deliveries , and Stripe officially documents verification using the Stripe-Signature header and an endpoint secret.

A normal internal API is usually called by your own client using an authentication token. A webhook is very different because you must verify on your side whether the sender is legitimate . In addition, webhooks may be retried and may arrive out of order, so if you write your code under the assumptions that “it will come only once” and “it will always arrive in order,” it becomes fragile in real operations. Webhook best practices repeatedly stress authentication, signatures, retries, and idempotency.

## 2. The first design principle: keep the responsibilities of the receiver endpoint small

The safest approach is to keep the responsibilities of a webhook receiver endpoint as small as possible. A recommended flow is:

- Receive the raw request body and headers

- Verify the signature and the authenticity of the sender

- Record the event ID and similar identifiers, and check whether it is a duplicate

- Return a 2xx response as quickly as possible when appropriate

- Hand off truly heavy business processing to a downstream system

With this structure, the webhook receiver becomes the “front door for external events,” clearly separated from the main body of business logic. Stripe’s documentation also explains webhook endpoints on the premise that they first verify signatures and then handle events safely, and FastAPI allows lightweight post-response work using BackgroundTasks .

## 3. Signature verification basics: a secret plus the raw request body

GitHub documents verification using X-Hub-Signature-256 with a webhook secret. If a secret is configured, GitHub includes an HMAC SHA-256 digest in the header. Stripe does something similar, requiring the Stripe-Signature header, the endpoint secret, and the raw, unmodified request body for verification.

The especially important point here is that verification must use the raw body before parsing it as JSON . Stripe explicitly identifies modified request bodies as a cause of signature verification errors and treats access to the unmodified body as a critical requirement. In FastAPI, you can access the raw body directly from the Request object.

## 4. A minimal FastAPI example for safely receiving the raw body

First, let’s create the skeleton of a webhook receiver in FastAPI. Here, we receive headers and the raw body in a provider-agnostic way.

```
from fastapi import APIRouter, Request, Header, HTTPException, status

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/generic")
async def receive_webhook(
    request: Request,
    x_signature: str | None = Header(default=None),
):
    raw_body = await request.body()

    if not x_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing signature header",
        )

    # Perform signature verification here
    # Parse JSON only after signature verification succeeds
    payload = await request.json()

    return {"received": True}
```

At this stage, signature verification is not yet implemented, but the core points are already clear. You should call await request.body() first to get the raw body , and you should not proceed to business logic before signature verification is complete. The ability to access the raw request body through FastAPI’s Request object is extremely important for webhook implementations.

## 5. A basic pattern for self-implemented HMAC signature verification

Here is a minimal HMAC-SHA256 verification pattern similar to GitHub’s webhook verification. If the actual provider offers an official library, you should prefer that first. Stripe also recommends using its official library.

```
import hashlib
import hmac

def verify_hmac_sha256(raw_body: bytes, header_signature: str, secret: str) -> bool:
    digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Assume the form "sha256=<hex>"
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, header_signature)
```

You can use it in FastAPI like this:

```
from fastapi import Request, Header, HTTPException, status

WEBHOOK_SECRET = "replace-me"

@router.post("/github-like")
async def receive_github_like_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
):
    raw_body = await request.body()

    if not x_hub_signature_256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing signature",
        )

    if not verify_hmac_sha256(raw_body, x_hub_signature_256, WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid signature",
        )

    payload = await request.json()
    return {"ok": True, "event_type": payload.get("action")}
```

This pattern applies to many webhooks, but the exact header format and whether timestamps are included vary by provider , so in production you must follow the provider’s official specification. GitHub uses X-Hub-Signature-256 , and Stripe uses Stripe-Signature .

## 6. For Stripe-style verification, stay as close to the official library flow as possible

Stripe recommends using its official library for webhook signature verification. It also clearly states that the required pieces are the Stripe-Signature header, the endpoint secret, and the unmodified request body.

So for Stripe integration, the flow conceptually looks like this:

```
# This is a conceptual example. In practice, follow the recommended procedure
# of the stripe library.
@router.post("/stripe")
async def receive_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    raw_body = await request.body()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="missing Stripe-Signature")

    # Conceptually, you would pass this into something like:
    # stripe.Webhook.construct_event(raw_body, stripe_signature, endpoint_secret)
    event = {"type": "payment_intent.succeeded"}  # explanatory placeholder

    return {"received": True, "type": event["type"]}
```

The important point here is the order: do not inspect the event type until signature verification has passed . It is tempting to branch early based on event type, but verifying whether the sender is legitimate must come first.

## 7. Idempotency: make sure the system does not break if the same event arrives twice

Webhooks may be delivered more than once. If the receiving side times out or the network is unstable, the sender cannot be sure the delivery succeeded, so it retries. That is why you need idempotency . In other words, the system should end in the same final state even if the same event is received multiple times. Webhook best practices also place idempotency at the core of a robust design.

The most practical method is to store the event ID or delivery ID assigned by the provider and check whether it has already been processed . GitHub provides delivery identifiers through headers and payloads, and Stripe also provides event IDs inside event objects.

### 7.1 Example model for storing processed events

```
from pydantic import BaseModel
from datetime import datetime

class ProcessedWebhookEvent(BaseModel):
    provider: str
    event_id: str
    received_at: datetime
```

### 7.2 Example of a simple duplicate check

```
from fastapi import HTTPException, status

processed_event_ids: set[str] = set()

def ensure_not_processed(provider: str, event_id: str) -> None:
    key = f"{provider}:{event_id}"
    if key in processed_event_ids:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="already processed",
        )
    processed_event_ids.add(key)
```

In production, you would of course store this in a database or Redis rather than memory. Still, the design concept is easy to understand: store event IDs under a unique constraint and prevent duplicate processing .

## 8. Prepare for out-of-order and delayed delivery: do not trust event sequence too much

Webhooks do not necessarily arrive in chronological order. So if you hardcode assumptions like “B will always come after A,” your system becomes fragile. General webhook best practices recommend designing the receiver under the assumption that out-of-order delivery and retries are normal.

A stable way to think about this is:

- Treat the webhook as a trigger to refresh or reconsider state

- If necessary, re-query the provider API to obtain the latest authoritative state

- Do not determine the full state solely from the received event

For example, in a payment integration, instead of saying “once I receive a payment succeeded event, I will finalize the billing state immediately,” it is often more robust to say, “after receiving the event, I may re-fetch the current payment state if needed.” Stripe also positions webhooks as an entry point for asynchronous event handling.

## 9. Return the ACK quickly: push heavy work downstream

Webhook senders often expect a 2xx response within a short time. If your receiver performs heavy aggregation or large database updates before responding, it is more likely to time out and trigger retries. That is why the standard approach is to do verification, minimal persistence, and the ACK first , then hand downstream processing to a background task or queue. FastAPI’s BackgroundTasks can run lightweight work after the response is sent.

### 9.1 Example using FastAPI’s BackgroundTasks

```
from fastapi import BackgroundTasks, Request, Header

def process_webhook_event(provider: str, event_id: str, payload: dict) -> None:
    # In reality, this would update a DB or enqueue a job
    print(provider, event_id, payload.get("type"))

@router.post("/generic-async")
async def receive_webhook_async(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signature: str | None = Header(default=None),
):
    raw_body = await request.body()

    if not x_signature:
        raise HTTPException(status_code=400, detail="missing signature")

    # Perform signature verification here
    payload = await request.json()

    provider = "generic"
    event_id = payload.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="missing event id")

    background_tasks.add_task(process_webhook_event, provider, event_id, payload)
    return {"received": True}
```

However, BackgroundTasks is best suited for lightweight post-response work in the same process. For heavy tasks or anything needing retries, it is more stable to hand the work off to a job queue such as Celery. FastAPI’s own documentation also presents BackgroundTasks as a mechanism for post-response work.

## 10. Event routing: avoid growing a giant if ladder

As the number of webhook event types grows, a single endpoint can easily accumulate a long chain of if event_type == ... conditions. A cleaner approach is to collect event-specific handler functions in a dictionary.

```
from collections.abc import Callable

def handle_payment_succeeded(payload: dict) -> None:
    ...

def handle_payment_failed(payload: dict) -> None:
    ...

HANDLERS: dict[str, Callable[[dict], None]] = {
    "payment.succeeded": handle_payment_succeeded,
    "payment.failed": handle_payment_failed,
}

def dispatch_event(event_type: str, payload: dict) -> None:
    handler = HANDLERS.get(event_type)
    if handler:
        handler(payload)
```

If you call this from downstream webhook processing, the diff when adding new events stays small. It also helps to separate files by provider, such as stripe_handlers.py and github_handlers.py , so responsibilities remain visible.

## 11. Audit logs and event logs: treat them separately from ordinary logs

Because webhooks are important externally originated events, it is extremely helpful to maintain logs that are easy to audit separately from normal application logs.

At a minimum, it is useful to record:

- provider (Stripe, GitHub, etc.)

- event_id

- event_type

- received_at

- signature_verified

- request_id

- processing_status

- error_message (on failure)

With external events such as those from Stripe and GitHub, being able to trace “received,” “verified,” and “processed or held” makes incident investigation much easier. GitHub also exposes various headers and delivery identifiers that help track deliveries.

## 12. What should return 2xx, and what should return 4xx or 5xx?

In webhook systems, the receiver’s response affects retry behavior. A practical classification is:

- Invalid signature, malformed body, missing required headers → 4xx (the delivery does not meet your acceptance conditions)

- Temporary internal failures, database outages → 5xx (designed under the assumption that retries may occur)

- Duplicate events already processed → often safe to treat as 2xx

The final choice depends on each provider’s retry policy, so production behavior should match the provider’s specification. Still, the principle that duplicates may be treated as successful, but invalid signatures must never be treated as successful is useful in many cases. Both GitHub and Stripe emphasize confirming the legitimacy of the delivery first.

## 13. It is usually better to separate webhook URLs by provider

It is possible to unify multiple providers’ webhooks under a single receiver, but in practice it is usually safer and easier to operate if you separate the URL by provider .

For example:

- /webhooks/stripe

- /webhooks/github

- /webhooks/internal

This gives you several advantages:

- Secrets are managed separately

- Differences in signature schemes are easier to absorb

- Logs and monitoring are easier to separate

- Incident investigation becomes faster

Since GitHub and Stripe use different header names and signature formats, separating them from the start is the more natural design.

## 14. Testing strategy: five tests worth protecting first

Webhook receivers can look simple, but they are fragile enough that testing matters a lot. Even just the following five tests add significant confidence:

- A request with a correct signature is accepted

- A request with an invalid signature is rejected

- Sending the same event ID twice does not cause duplicate processing

- Failure in heavy downstream processing does not break the receiver’s main responsibility

- Missing required headers or a missing required event ID results in rejection

You can test these with FastAPI’s normal API testing style using TestClient , while paying attention to signature headers and the raw body. If you build your test cases around the pattern GitHub and Stripe both rely on — signature header + raw body + secret — your tests will be genuinely useful in real operations.

## 15. Reader-specific roadmap

### For individual developers and learners

- Start by separating webhook URLs by provider

- Build the structure so it receives the raw body with Request.body()

- Add secret-based signature verification

- Store event IDs and prevent duplicate processing

- Hand heavy processing off to BackgroundTasks or a job queue

### For backend engineers in small teams

- Share the responsibility split of “receive, verify, ACK, downstream processing” across the team

- Consolidate provider-specific signature verification into shared functions

- Put an event storage table and audit logs in place

- Add persistence for idempotency keys such as event IDs

- Protect tests for duplicates, invalid signatures, and cases close to out-of-order delivery

### For SaaS teams and startups

- Redesign webhook reception as a domain event entry point

- Separate audit logs, the event table, and the job queue

- Define retry and failure policies by provider

- Monitor metrics such as received count, signature verification failures, duplicate count, and processing failure count

- Connect payment and contract-change webhooks to billing state and audit logs as part of a full-system design

## References

- FastAPI Background Tasks Request class Security

FastAPI

- Background Tasks

- Request class

- Security

- Stripe Receive Stripe events in your webhook endpoint Webhook signature errors Handle payment events with webhooks

Stripe

- Receive Stripe events in your webhook endpoint

- Webhook signature errors

- Handle payment events with webhooks

- GitHub Validating webhook deliveries Webhook events and payloads Best practices for using webhooks

GitHub

- Validating webhook deliveries

- Webhook events and payloads

- Best practices for using webhooks

- Practical best practices Webhook Security Best Practices Best Practices for Receiving Webhooks

Practical best practices

- Webhook Security Best Practices

- Best Practices for Receiving Webhooks

## Conclusion

- A webhook receiver API is an entry point that should be built more carefully than a normal POST API. Once you include signature verification, idempotency, retry handling, and auditability, it becomes much harder to break in real operations.

- In FastAPI, a particularly compatible baseline pattern is to retrieve the raw body from Request , verify the signature, return an ACK quickly, and pass downstream processing to background tasks or a job queue.

- Major services like Stripe and GitHub also assume secret-based signature verification. It is best to follow their official specifications first, and absorb provider-specific differences in your receiver design and shared helper functions.

- You do not need to build a perfect event platform from the beginning, but simply separating receive, verify, record, ACK, and downstream processing already makes the system much more resilient to future complexity.

As natural next topics, this article connects very well to subjects like “Designing external API clients in FastAPI (retries, timeouts, circuit breakers)” and “How to connect FastAPI job queue design to downstream webhook processing.”

### Share this:

- Post

- Share on Threads (Opens in new window) Threads
