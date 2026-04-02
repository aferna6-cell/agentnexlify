# Council Transcript — Priority Sequencing
**Date:** 2026-04-01
**Question:** Optimal execution order for 4 priorities with 2 testers, zero revenue, solo engineer

## Framed Question
With 2 active testers on production, zero paying customers, and a solo engineer — what's the optimal execution order and approach for: Google Review Auto-Import (P2), Social Media hide-or-ship (P3), Wizard Drop-Off Tracking (P4), and Vertical SEO Pages (P5)?

## Advisor Responses

### The Contrarian
Hide social media today (30 min). Then STOP doing priorities 2, 4, and 5 entirely. Google Business Profile API requires verified business, OAuth consent screen review by Google, ongoing quota management. Your two testers aren't sitting there saying "I wish reviews auto-imported." Wizard tracking is premature optimization for n=2. SEO takes 6-12 months. Spend every remaining hour making core product bulletproof. You're not going to convert testers into paying customers by shipping four half-finished things.

### The First Principles Thinker
Strip everything back. What converts a tester into a paying customer? Not feature completeness — conviction that this tool solves their problem better than doing it manually or paying GoHighLevel $97/month. Priority 3 is the only emergency — a fake "Published" status is a trust-destroying lie. Remove from sidebar immediately. Priority 4 — ask testers directly, don't build analytics for n=2. Priority 5 — post-revenue activity. Priority 2 — reframe: do your testers actually care about review import? If yes, build it. If not, shelve. Stop executing priorities. Start executing conversations with testers.

### The Expansionist
Ship Social Media — don't hide it. Meta Graph API for Facebook/Instagram is 3-4 day build, not 2 weeks. The scheduling UI, post creation, database schema already exist. Only missing the API call layer. This makes testers compare you to a $300/mo platform, not a $40/mo widget. Order: Social Media > Google Reviews > Wizard Tracking > SEO. The upside nobody's seeing: ship social + reviews in the same week and your testers experience an end-to-end platform they can't unplug from.

### The Outsider
Remove social media immediately. Stop building for a week. Two testers are the entire universe — get on calls with them, find what makes them pay THIS WEEK. "Commonly asked about" by whom matters. SEO is 6-12 month play. Wizard tracking for n=2 is overkill — just call them. Everything else is procrastination wearing a product roadmap costume. Progress is exactly one thing — revenue.

### The Executor
Execution order: 3A (hide social, today), 4 (wizard tracking, 2-3 hours), 2 (Google Reviews, 3-4 days), 5 (backlog). SessionStorage + single analytics endpoint for wizard. Google Review import via cron + dedup. Total timeline: 1.5 weeks for priorities 3A, 4, and 2. Priority 5 goes on the backlog.

## Peer Reviews

**Anonymization mapping:** A=Expansionist, B=Outsider, C=Executor, D=Contrarian, E=First Principles

### Reviewer 1
- Strongest: E — correctly reframes the entire question
- Biggest blind spot: A — recommends largest time investment with no evidence of demand
- All missed: Are the 2 testers representative of target customer?

### Reviewer 2
- Strongest: E — clearest decision framework
- Biggest blind spot: A — ignores Meta's app review process, token refresh, content validation
- All missed: Are testers representative? Can they convert? Budget authority?

### Reviewer 3
- Strongest: E — reframes every priority through "do testers care?" lens
- Biggest blind spot: A — "3-4 day" timeline is fantasy with OAuth approval
- All missed: Is there a conversion mechanism? Stripe checkout? Trial expiration?

### Reviewer 4
- Strongest: E — "do your testers actually care?" is the sharpest insight
- Biggest blind spot: A — assumes feature breadth over depth
- All missed: Are testers genuine buyers or unpaid volunteers?

### Reviewer 5
- Strongest: E — actionable framework
- Biggest blind spot: A — ignores Meta API review (weeks)
- All missed: What bugs/UX friction are testers hitting NOW? Bug backlog may matter more.

## Chairman's Synthesis

### Where the Council Agrees
1. Hide Social Media immediately (5/5)
2. Talk to testers before building (4/5)
3. Wizard tracking premature for n=2 (4/5)
4. SEO pages post-revenue (5/5)

### Where the Council Clashes
- Ship vs hide social media (1 vs 4)
- Google Reviews: build now vs validate with testers first

### Blind Spots
1. Are testers actual target customers with budget authority?
2. Is there a functioning conversion mechanism (Stripe, trial expiry)?
3. What's the current bug backlog?

### The Recommendation
Stop building features. Start closing. Hide social media (30 min). Call each tester this week. Build whatever they say matters.

### The One Thing to Do First
Hide Social Media from the sidebar now. Then schedule calls with testers.
