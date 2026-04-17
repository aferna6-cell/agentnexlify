---
source_url: https://www.saastr.com/10-things-to-know-before-you-deploy-your-first-ai-sdr-the-very-latest-with-saastrs-jason-and-amelia/
fetched_at: 2026-04-17T22:04:19Z
category: small-biz-saas
title: 10 Things to Know Before You Deploy Your First AI SDR: The Very Latest with SaaStr’s Jason and Amelia | SaaStr
---

# 10 Things to Know Before You Deploy Your First AI SDR: The Very Latest with SaaStr’s Jason and Amelia | SaaStr

## 10 Things to Know Before You Deploy Your First AI SDR: The Very Latest with SaaStr’s Jason and Amelia

by Jason Lemkin | Artificial Intelligence (AI), Blog Posts, SaaStr.Ai, Vibe Coding

We’ve now been running AI SDR agents for 10+ months at SaaStr. We use four different vendors in daily rotation (Artisan, Salesforce AgentForce, Qualified, and Monaco), we’ve sent hundreds of thousands of outbound messages, processed 1.5 million inbound sessions on a single website, and we’ve made every mistake you can make along the way.

Someone asked us the other day to break down what they should know before rolling out their very first AI SDR. So here are the 10 biggest lessons, drawn from real deployment data, real failures, and real results.

## 1. You Probably Only Need One Vendor

We run four AI SDR tools. You do not need to do that. We hyper-segment across platforms because each one does something slightly different well, but for 90%+ of use cases, one vendor will handle the bulk of what you need.

At most, you might end up with two: one for outbound, one for inbound. But do not start by buying three or four tools. Pick one that covers the majority of what you want to accomplish and go deep with it.

The tool matters far less than the strategy you bring to it.

## 2. Your Human Playbook Has to Work First

This is the single biggest mistake we see, and it cuts across company stage. We see it from raw startups at $1M ARR and from multi-billion-dollar public companies alike.

The pattern is always the same: they want to turn on an AI SDR without first proving that their human sales motion works. Or they use the AI SDR to “test new copy” they’ve never tried before.

If you have not gotten outbound to work with humans, buying an AI to do it will not fix that. We did not deploy our first AI SDR until we knew exactly what was working with our human SDRs: which messaging converted, which segments responded, what cadences performed. Then we fed all of that into the agent.

The goal of an AI SDR is to clone the best person on your team. If it is just you, clone you. If you have four people and one is crushing it at outbound, clone that person. These tools, in the beginning, are cloning machines. They take context word for word and use it to build out their brain. If you feed them garbage context, or untested context, they will produce garbage results.

You basically have to have done founder-led sales before you hand it off to an agent. The playbook has to work, at least a little, before you automate it.

And watch out: some vendors will steer you toward using their tool for “pure cold testing.” Sure, you can do that. But you will likely be disappointed compared to scaling something that already converts. Do not fall into that trap.

## 3. Segment Ruthlessly

This one we cannot overstate. Segment ruthlessly. Literally every day.

Every AI SDR tool we have tried, and that is over a dozen, has some version of functionality where you can tell the agent who to reach out to and give it specific context for that segment. The difference between one generic campaign brain and hyper-segmented campaigns with tailored context is enormous.

Here is a concrete example. We initially treated our inbound agent as one big bucket: “they’re inbound to the website.” But that was wrong. We actually have brand-new visitors, people who came via a social ad, prior sponsors returning, current customers checking on something, and lapsed customers browsing the pricing page. Each of those segments needs completely different context.

A lapsed customer who churned in 2022 and is now browsing your pricing page? Your agent should know they are a former customer, highlight what has changed with the product since then, and speak to them totally differently than a brand-new cold visitor.

We run roughly 100 effective segments across about 1,000 contacts at a time. That sounds like a lot of work. It is. But it is exactly where the leverage comes from.

One important caveat: none of the AI SDR tools today can auto-segment well enough to deliver these results on their own. You still need a human (or a tool like Claude) to define and manage the segments. The platforms default to “run one campaign, keep adding leads.” That is the wrong approach.

## 4. Consistency Beats Brilliance

Your AI SDR does not need to write the greatest email on Earth. It needs to write a pretty good email, every time, without fail.

We have sent 40,000+ messages through Artisan alone, 100,000+ through Qualified, close to 200,000 through Salesforce. Are these the greatest emails since sliced bread? No. They are solid. They are consistent. They follow the proven messaging and subject lines we already know work.

That consistency, combined with hyper-segmentation and proven copy, will outperform a human SDR who ignores training, skips follow-ups, or goes off-script.

The agent remembers every instruction you give it. Every time. A human SDR forgets by Thursday.

We see a lot of “AI SDR paralysis” from founders who test a tool, see the output, and say “it’s not that great.” Okay, but did you segment properly? Did you give it copy that already converts? Did you iterate on the context? You can almost always get the output to “pretty good.” And pretty good at infinite scale and perfect consistency will beat brilliant-but-sporadic every time.

## 5. You Need 1-2 Humans to Run This

Agents are not zero-headcount tools. You need at least one person, ideally two, dedicated to managing your AI SDR deployment.

Why two? Because if one person owns all the tribal knowledge of how your agents are configured, which contexts are loaded, who your FD is at each vendor, where to tweak things, and that person leaves or gets pulled onto another project, your agents grind to a halt.

We have experienced this firsthand. When my time got split between agent management and SaaStr Annual production, our agents started sitting idle. Outbound agents in particular will finish their sequence in a few days and just sit there waiting for you to load the next segment, the next batch of contacts, the next round of context.

Unless you are feeding them continuously, they idle. And idle agents are wasted money.

Some tools (like Monaco) are better at self-refilling the pipeline by automatically finding lookalike targets. But even then, the setup, monitoring, and ongoing calibration require real human time every single day.

## 6. Read Everything. Especially in the First 30 Days.

When you first deploy, read every single output your agent produces before it goes out. Every email. Every chat response. Everything.

You will catch things you did not anticipate. Our agents would sometimes lowercase “SaaStr” when it should be capitalized. They would scrape old event dates from the internet and put wrong dates in outbound emails. Small stuff, but stuff that kills credibility.

Even 10 months in, I still do a daily speedrun through our agent outputs. Some days it is 10 minutes, some days longer. I spot-check inbound conversations, review outbound messages, and look for anything off. When I find something, I add it to the agent’s context so it learns.

This is how you continuously improve. If you only care about inputs and ignore outputs, you are seeing half the picture.

And it is rare, but agents do hallucinate. Ours have occasionally gone off the rails or made up information. If you are not reading, you will not catch it until a prospect or customer complains.

## 7. Budget at Least Two Weeks of Ramp Time

Nothing is instant. Nothing is set-and-forget.

Some outbound agents need two to three weeks just to warm up dedicated email addresses and IPs before they can send at scale. On top of that, steps 1 through 6 on this list take real time to execute: figuring out what copy works, what subject lines convert, what time of day performs, hyper-segmenting your base, configuring the tool, setting up CRM integrations.

Even our fastest deployment (Monaco, which is genuinely very good at self-service) took about a week and a half.

Be wary of any tool that promises “instant AI SDR, deploy today.” If the ramp time is zero, the quality is probably zero too.

After the initial two-week setup, it is still a daily commitment. Think of it like a short daily one-on-one with a human team member. Fifteen minutes minimum, every day, to check in on what your agents are doing, adjust context, reload segments. That is your ongoing operating cost.

## 8. Most People Still Prefer Chat Over Voice and Video

We have a multimodal AI agent (Amelia AI) that can do text chat, voice, and video. We did motion capture at the Qualified studios to build a full video avatar. It is genuinely cool.

And 85% of people still choose to interact via text chat.

The 15% who use voice or video tend to stay in that mode and seem to enjoy it. Some people at our London event last December told us they had full conversations with Amelia AI beforehand. But the overwhelming preference in B2B is still text-based.

The takeaway: do not kill yourself trying to launch voice and video on day one. Get your text-based chat agent working well first. We ran our Qualified agent for a full quarter before we added the voice and video layer. Once the text brain was dialed in, we layered on the multimodal experience. That is the right order.

One important nuance: voice and video agents need significantly more guardrails than text agents. When people are talking live to a video avatar, they start asking personal questions, going off-topic, and testing boundaries in ways they do not with a chat box. You need explicit training on how to handle those detours and redirect back to the goal.

## 9. Be Careful With Person-Dependent Deployments

Our Amelia AI talks like Amelia. Our Jason AI talks like me. These agents are deeply tied to specific people, their personalities, their knowledge, their likenesses.

That works for us because Amelia and I are founders. We are not going anywhere.

But think twice before you build your AI SDR around a specific employee who might leave. Qualified’s “Piper” agent is based on a real employee who has since been promoted. She is still there, but what if she leaves? Her likeness is on billboards and across their website. There are no real legal precedents yet for AI agent likenesses in employment contexts.

Beyond the legal question, there is an operational one. If one person holds all the tribal knowledge of how your agents are configured and that person walks, you are in trouble. Our sales team member David has logged into Qualified exactly twice in 10 months. He does not know where anything is. If Amelia were not managing the agents, they would degrade fast.

The scale of this risk grows quickly. Amelia AI had 30+ video conversations in a single day recently. Over six months, 1.5 million sessions on one website alone. That is a lot of exposure to an agent that is dependent on one specific person to maintain it.

Document your agent configurations. Have backups. Do not let it become a single point of failure.

## 10. Your Data Fundamentals Have to Be in Place

Our Qualified agent works off nearly 6,000 pieces of context: website scrapes refreshed every couple days, custom snippets, uploaded PDFs, Q&A documents. Every few days, someone asks the agent something we have not trained it on, and we have to create new documentation and feed it in.

This snowball never stops. Almost every day you will discover a new scenario your agent cannot handle because you have not given it the context yet. “People are asking about this product feature I never documented.” “They want to know about pricing tiers I forgot to upload.” That is the ongoing reality.

Inbound agents: You probably need at least 10,000 to 25,000 monthly website visitors for an inbound AI SDR (like a Qualified-style chat agent) to generate meaningful results. If you have fewer than 10K monthly visitors, focus on outbound first, or on using agents for existing customer e

[truncated]
