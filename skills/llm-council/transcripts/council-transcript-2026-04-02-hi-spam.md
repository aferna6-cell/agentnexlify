# LLM Council Transcript — "Hi" Spam Problem
**Date:** 2026-04-02
**Question:** What's the best approach to handle the "hi" spam problem on an AI chatbot widget for a financial services site?

---

## Original Question

A solo engineer running an AI chatbot widget on a financial services client site faces a "hi" spam problem. 79% of 247 messages over 6 days were just "hi" with no follow-up. 3 device IDs sent 51% of all traffic. Each message triggers a full Claude API call (~$0.003). The existing IP-based rate limit (60/min) doesn't help because spam comes from many IPs. Backend is FastAPI with 4 Uvicorn workers (no shared in-memory state). Widget runs on external client sites with no server-side session.

Options considered:
1. Detect repeat "hi" in chat history → canned response
2. Per-session message cooldown (min 5 seconds)
3. Per-session daily message cap
4. Smart detection: if last N messages are all single-word greetings → canned response
5. Widget-side JS debounce

Constraints: solo engineer, must not block first-time "hi" users, must not break real conversations, financial services context, FastAPI/Python backend.

---

## Framed Question (Chairman)

When can the `/api/v1/widget/chat` handler skip the Claude API call with confidence that it's not destroying value? The core decision: which of the 5 options delivers the best ratio of cost savings to false positive risk to implementation effort, specifically given that (a) chat history is already loaded before every Claude call, (b) in-memory state is per-worker and unreliable, and (c) a financial services context demands caution about blocking legitimate users?

---

## Advisor Responses

### Advisor 1 — The Contrarian

Every option proposed has a hidden failure mode. Option 1 (detect repeat "hi" in chat history) breaks immediately in production: chat history is only reliable if it's fetched consistently across all 4 workers. If the same session hits different workers, history may be incomplete — the "repeat hi" detection misses repeat offenders half the time. Build it, it works in dev, fails silently in prod.

Option 4 has the same flaw plus: what counts as a single-word greeting? "Hey", "Hello", "Yo", "Hi!", "hi." — you need a list that needs maintenance. A legitimate confused user who says "hi" five times gets silenced right when they need help most.

Option 5 (widget-side JS debounce) is trivially bypassed by anyone with DevTools or curl. The data shows 3 device IDs driving 51% of traffic — targeted abuse, not fat-fingered users.

The real flaw: you're solving a symptom. Why are sessions sending only "hi" with no follow-up? The bot's opening response is so generic users disengage immediately. Fixing the bot's greeting — making it instantly show value ("Hi! I can help with mortgage rates, account questions, or scheduling a call. What brings you in?") — might eliminate 50% of the problem without any engineering.

Don't solve the wrong problem.

---

### Advisor 2 — The First Principles Thinker

Strip away the implementation details. What are we actually trying to solve? Reduce wasted Claude API calls. When can we skip the Claude call with confidence? When the message is semantically identical to a previous message in the same session AND the prior response was already sent.

This collapses Options 1 and 4 into a single principle: **response deduplication within a session**. If the session already has a bot response to "hi", return a canned variant without calling Claude. Deterministic, zero ML, zero new infrastructure, false positive rate near zero.

The key insight: chat history IS already loaded (last 20 messages) before every Claude call. The data needed for this check is already in memory at the time of the API call. The engineering cost is a 10-line Python function.

The per-worker memory constraint is a red herring — you're reading from the database-loaded chat history, not in-process state. It works across all workers automatically.

The answer is: short-circuit the Claude call when history proves the question has already been answered.

---

### Advisor 3 — The Expansionist

79% of messages being "hi" with no follow-up is not spam — it's users who opened the widget, got a generic response, and left. That's a conversion problem disguised as a spam problem. If you implement canned responses and suppress Claude calls, you've "solved" cost but left the underlying UX failure untouched.

On a financial services site, one extra lead converted per day is worth far more than $0.003 in saved API costs. The real upside: fix the bot's opening experience and convert some of that 79% into actual leads.

Second opportunity: **session-level intent classification**. After the first "hi", the bot should immediately surface the most relevant options for a financial services visitor — account help, rates, advisor scheduling. A proactive quick-reply menu after "hi" turns a dead session into a guided one.

Third: the 3 device IDs driving 51% of traffic are a test signal or bot signal. Before building anti-spam infrastructure, verify: are these internal QA sessions? Developer testing? If so, a test-mode flag in the widget makes the "spam" disappear from metrics immediately.

Solve the UX problem and the spam problem largely self-corrects.

---

### Advisor 4 — The Outsider

You have a chatbot that costs money per message. Most messages are "hi". You want to stop paying for those.

Look at the last bot message in the conversation. If the bot already sent a greeting response, and the new message is just "hi" again, return a similar response without calling the API. That's it.

Options 2 and 3 punish timing, not behavior. A real user who pauses and comes back gets punished. Option 5 doesn't protect the API — anyone calling the endpoint directly bypasses it. Options 1 and 4 are the same thing with different thresholds.

The thing that strikes me: you said no shared in-memory state between workers, but you also said chat history is loaded before every Claude call. You have the history. You have everything you need. The "no shared state" constraint doesn't apply because you're reading existing state, not adding new state.

A 10-line if-statement before the API call: if message is a greeting AND history contains a prior bot greeting response, return a canned redirect. Skip Claude. Done.

---

### Advisor 5 — The Executor

**Primary fix: Backend greeting short-circuit (Options 1+4 combined).** 2 hours max.

In the chat handler, before the Claude API call:
1. Load chat history (already happens).
2. Normalize incoming message: `.strip().lower()` + strip punctuation.
3. Check against greeting set: `{"hi", "hey", "hello", "yo", "sup", "hiya"}`.
4. Count prior user messages that are also greetings from loaded history.
5. If count >= 1 → return `"Still here! Is there anything specific I can help you with today?"` No Claude call.
6. First "hi" always goes to Claude normally.

**Secondary fix: Widget-side JS debounce.** Not a security control — a UX control. 1-second debounce on send button prevents double-send on slow connections. 15 minutes to implement.

**Skip for now:** Per-session cooldowns and daily caps. They introduce timing complexity and will generate support tickets.

Expected result: eliminate ~60-70% of Claude API calls from greeting spam. Ship the backend short-circuit first, verify in staging, deploy.

---

## Anonymization Mapping (for Peer Review)

- Response A = Advisor 2 (First Principles Thinker)
- Response B = Advisor 5 (The Executor)
- Response C = Advisor 1 (The Contrarian)
- Response D = Advisor 3 (The Expansionist)
- Response E = Advisor 4 (The Outsider)

---

## Peer Reviews

### Reviewer 1
**Strongest:** Response B (Executor) — exact implementation steps, greeting list, expected outcome. Actionable and correct.
**Biggest blind spot:** Response D (Expansionist) — the "fix the UX" advice is good but doesn't answer the question. The engineer still needs to stop paying for repeat greetings today.
**What all missed:** The 3 device IDs. If those are identifiable by device fingerprint, a device-level blocklist kills 51% of the spam immediately — faster than any architectural solution.

### Reviewer 2
**Strongest:** Response A (First Principles) — correctly identifies that the chat history is already loaded, making the "no shared state" constraint a non-issue. Eliminates the main technical objection.
**Biggest blind spot:** Response C (Contrarian) — raises good concerns but then pivots to "fix the bot's greeting" as primary advice, which is a product recommendation not an engineering solution.
**What all missed:** What happens to the canned response in the chat history? If the canned response isn't stored as a real bot message, the next request won't see a prior greeting and will trigger Claude again. This detail determines whether the solution actually works.

### Reviewer 3
**Strongest:** Response B (Executor) — concrete, scoped, includes a greeting list and a clear threshold. The 2-hour estimate is realistic.
**Biggest blind spot:** Response E (Outsider) — "return the same response you already sent" produces weird UX (verbatim repeat). The canned response should redirect, not repeat.
**What all missed:** The greeting list must handle punctuation and capitalization: "hi!", "HI", "hi.", "Hey!". Need `.strip().lower()` plus punctuation stripping. Trivial but easy to forget.

### Reviewer 4
**Strongest:** Response A (First Principles) — correctly frames the key constraint: history is already loaded, no new infrastructure needed.
**Biggest blind spot:** Response D (Expansionist) — the quick-reply menu idea is good product thinking but is a separate project. Conflating the two delays the simple fix.
**What all missed:** Observability. How do you know the short-circuit is working? You need a log line (`greeting_shortcircuit=True`) to prove ROI. A counter logged to stdout costs nothing.

### Reviewer 5
**Strongest:** Response B (Executor) — only response with a copy-pasteable greeting list and a clear threshold. The secondary JS debounce suggestion is also correct.
**Biggest blind spot:** Response C (Contrarian) — the "you're solving the wrong problem" argument is compelling but incomplete. Improving the bot's opening doesn't stop someone deliberately abusing the endpoint.
**What all missed:** The savings are on the Claude API call only, not on DB reads/writes (those still happen). Be clear about what you're eliminating so the ROI calculation is accurate.

---

## Chairman Synthesis

### Where the Council Agrees
All 5 advisors independently converged on the same technical approach: intercept the Claude API call in the backend handler when the incoming message is a greeting AND the chat history already contains a prior bot response to a greeting. Return a lightweight canned redirect response. No new infrastructure. The chat history is already loaded before every Claude call — this is the key insight that makes the solution trivially implementable without shared in-memory state across workers.

All five agree: widget-side JS debounce is a useful secondary measure (UX protection, not security), but it's not the primary fix. All five agree: per-session cooldowns and daily caps are wrong choices for this context.

### Where the Council Clashes
The Contrarian + Expansionist argue the root cause is a UX failure — the bot's generic opening drives users away before they engage, and fixing that is more valuable than the spam fix. The Executor, First Principles, and Outsider treat this as a valid but separate concern. Both sides are correct. The Executor wins on sequencing: fix the API cost first (2 hours), then iterate on the bot's opening experience (separate project).

### Blind Spots Caught in Peer Review
1. Write the canned response to the DB as a real bot message. If it isn't stored, the next request won't find a prior greeting in history and will hit Claude again. The fix only works if the response is persisted.
2. Normalize the greeting list properly — `.strip().lower()` plus punctuation stripping. A naive `== "hi"` check misses "Hi!", "HI", "hi.".
3. Add observability — log a counter when the short-circuit fires. Without this, you can't prove the fix works.
4. Check the 3 device IDs first. If 51% of traffic comes from 3 device fingerprints, verify these aren't internal QA sessions. If they're abuse, device-level blocking kills the problem independently.

### The Recommendation
Implement Options 1+4 combined as a single backend short-circuit. In the `/api/v1/widget/chat` handler, before the Claude API call:
1. Normalize the incoming message: `.strip().lower()` + strip punctuation.
2. Check against a greeting set: `{"hi", "hey", "hello", "yo", "sup", "hiya", "howdy"}`.
3. Scan the loaded chat history for any prior user greeting + bot reply pair.
4. If found: return `"Still here! Is there anything specific I can help you with? I can assist with [service areas]."` Skip Claude entirely.
5. Write this canned response to the DB as a real bot message.
6. Log `greeting_shortcircuit=True` for observability.

First "hi" in any session always goes to Claude normally. Add JS debounce (1-second) as a secondary UX layer only. After shipping, separately improve the bot's opening response to be more directive.

### The One Thing to Do First
Add a 10-line Python function to the chat handler that checks the already-loaded chat history before the Claude API call. If the session has already exchanged greetings, return a canned redirect and skip Claude entirely. Ship that. Everything else is secondary.

---
*Council generated 2026-04-02 by AgentNexLiFy Chairman (Claude Sonnet 4.6)*
