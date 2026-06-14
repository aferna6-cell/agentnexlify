---
source_url: https://www.intercom.com/blog/fin-product-updates-february-recap/
fetched_at: 2026-04-20T22:03:18Z
category: competitors
title: Fin Product Updates: February recap - The Intercom Blog
---

# Fin Product Updates: February recap - The Intercom Blog

Every update this month removed a specific constraint on what teams can do with Fin.

Most Agents look impressive in demos and disappoint in production. The gap is almost always the same: complexity, control, and confidence. Can it handle the query that actually matters? Can it sound right on a call? Can your team deploy it without filing an engineering ticket? Can your managers understand what it’s doing?

This month, we shipped answers to all four. Here’s what we built.

## Procedures and Simulations (0:51)

The hardest problem in AI-powered customer service isn’t answering FAQs. It’s handling complex queries: billing refunds, multi-step flows with real business logic, actions that carry consequences if Fin gets them wrong.

Now, it’s much easier to build and manage Fin for complex queries without needing an engineer. You can write in natural language, test every step in simulation, and deploy with confidence.

The workflow starts with AI drafting the procedure from your existing source material. You edit in natural language, with structured hooks to pull in live data, apply business logic, and add code for deterministic control where you need it. That’s how you handle multi-step flows with the precision that matters when things go wrong.

Simulations are the test environment. Define a test case, pass in the data Fin would receive in a real conversation, and watch it work through each step. You see what Fin is doing, why, and whether it’s meeting the criteria you set. Full transparency at every point. I’ll be honest: watching Fin nail one of these is genuinely satisfying – there’s a particular confidence that comes from seeing the thing work before it goes anywhere near a customer.

Find out more about the latest Procedures and Simulations at [fin.ai/procedures](http://fin.ai/procedures). 

[](https://fin.ai/procedures)

## Fin Voice: Three major updates

When something’s wrong in a chat conversation, a customer might not notice for several exchanges. On a call, they notice in the first sentence. Every detail of how Fin sounds matters: the pronunciation of a brand name, how it handles background noise, whether it sounds like it belongs to your company at all. Three updates this month:

### 1. Pronunciation rules (4:18)

Fin has high out-of-the-box pronunciation accuracy. But it doesn’t know your brand – your product names, your industry terminology, the specific way your company uses certain words. That gap matters more than people expect. Mispronouncing a brand name on a customer call isn’t a small thing. It’s the first thing the customer tells someone about.

Alihan Zinna, Staff ML Scientist, demoed this with an IKEA scenario. Without pronunciation rules, Fin got both “IKEA” and a product name wrong. After adding rules, both were corrected and delivered naturally.

### 2. New natural voices (5:48)

We’ve added 11 new voices designed to match a range of brand tones. The goal is straightforward: a higher chance you’ll find a voice that actually sounds like it belongs to your company, not to a generic AI assistant.

### 3. Background noise reduction (6:28)

People call from airports, shops, and busy offices. Fin now monitors background noise continuously and increases noise reduction when the environment demands it. No configuration needed. As Alihan put it, 

“This is one of those things customers really notice when it’s not working. The goal was to make it invisible. That’s what we built.”

## Shopify setup experience (8:21)

Fin started as a Service Agent, but is becoming a Customer Agent – one unified AI agent working across the entire customer lifecycle, not just handling inbound support, but contributing to sales, to revenue, to the moments that matter before a customer ever has an issue.

The new Shopify setup is a clear step toward that.

A Shopify store can have thousands of products, each with variants and shifting inventory. Connecting all of that to an Agent has historically been painful. Robert Davitt and his fellow product engineers removed that hassle.

Three steps. First, connect your store. Second, install the Messenger directly in Shopify – no code, a few clicks. Third, deploy Fin. Total time: under two minutes. We timed it live.

What that unlocks is significant. In the demo, a first-time snowboarder asked for product recommendations. Fin searched the catalog, reasoned about what attributes matter to a beginner (there’s no “beginner” tag in the catalog), personalized recommendations by height and weight, and added a board to the cart.

Robert shared a real customer example that says it better than any demo. A store updated their website copy to promote a sale. Fin picked up on that context and started proactively recommending sale items, nudging customers to add more to their cart to avail of a discount. No extra configuration. Fin read the situation and acted on it.

Three steps and you have a shopping assistant that knows your store in real time and sells on your behalf.

## Helpdesk improvements (12:31)

Fin works with any helpdesk. But many of our customers prefer to consolidate and take advantage of Fin’s native integration with the Intercom helpdesk. We’ve shipped 19 helpdesk improvements in 2026. Two from this month worth highlighting:

### 11 new call metrics

Hold time, outbound dial time, missed and declined calls, call terminating party, and more. These metrics allow teams to analyze their workload distribution and call handling quality in detail.

### Holiday office hours

Teams no longer need to manually update office hours for every public holiday. This was the most upvoted request in our community. We shipped it.

•••

Every update this month removed a specific constraint on what teams can do with Fin: the complexity ceiling in automation, the quality ceiling in voice, the setup barrier in Shopify, the operational overhead in the helpdesk.

Finally, we end our Product Updates with a Star Wars crawl of 22 more updates.

All these features are live and available now. Take a closer look at [fin.ai/updates](http://fin.ai/updates). 

More to come. Back next month.
