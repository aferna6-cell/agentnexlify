# Research brief: Phonely AI 2026 — AI receptionist startup, pricing, ICP, funding, voice AI tech stack

- Generated: 2026-04-10T15:23:34
- Session: sesn_011CZvdhRzENUoH9WZJMgVKM
- Events: 28
- Elapsed: 125.7s

---

Now let me compile the brief and save it.
---

# Phonely AI — Research Brief (April 2026)

## Summary

Phonely is a YC-backed (S24) AI receptionist startup founded in 2023 by two former PhD AI researchers from the University of Melbourne. The company provides voice AI agents that answer business phone calls with human-like fluency, powered by a differentiated tech stack built on Groq LPU inference hardware, Maitai model orchestration, and custom fine-tuned open-source LLMs with LoRA hotswapping. Phonely serves an ICP spanning SMBs through Fortune 500 contact centers across healthcare, insurance, legal, and real estate verticals, with tiered pricing from ~\$35/mo to custom enterprise. Publicly confirmed funding totals at least \$2.7 M (YC seed + follow-on), the team is ~12 people, and the platform claims 5,000+ businesses and 1.2 M calls/month processed.

---

## Key Findings

### Founding & Team
- Phonely was spun out of the University of Melbourne's AI Research Lab and launched in February 2024. Phonely was founded in 2023.
- Will Bodewes is the co-founder and CEO. Prior to starting Phonely, he was pursuing a PhD at the University of Melbourne researching applied artificial intelligence applications. Nisal is the Co-founder and CTO. With a background in Electronic and Telecommunications Engineering, he worked as a senior engineer in the AI team of a major telecommunications company for nearly three years, then pursued a PhD at the University of Melbourne focusing on explainable AI and AI for healthcare.
- The startup has gone on to employ 12 staff.

### Funding
- Phonely, a San Francisco, CA-based AI-driven phone answering service startup, raised \$500K in funding. Y Combinator made the investment. CoreNest is the lead investor in Phonely's latest funding round held on Nov 22, 2024.
- Since then the startup has gone on to raise a further US\$2.2 million.
- Transpose Platform Management, 7BC Venture Capital, Alpine Ventures (California), CoreNest Capital, and Nivesha Ventures are 5 of 9 investors who have invested in Phonely. Phonely has 8 investors. Pioneer Fund invested in Phonely's Seed VC funding round.

### Product & Features
- Phonely uses a website URL to build a humanlike AI answering system in just a few minutes. The platform connects to scheduling software, routes calls, and integrates with an existing knowledge base, all while improving its responses over time. After the call, Phonely provides powerful AI analytics and automatically extracts relevant information, sending it directly to the business CRM, phone, or inbox.
- Phonely is an omnichannel solution that lets businesses deliver consistent customer experiences across phone, chat, SMS, and API. It supports natural, human-like conversations with 1,000+ voices, voice cloning, and seamless turn-taking.
- Enterprise-Grade Security: SOC II, HIPAA, and ISO certified, built for high reliability and compliance in sensitive industries. Scalable Performance: Handles over 1 million concurrent calls.
- Trusted by 5,000+ companies processing 1.2 M calls monthly.

### Voice AI Tech Stack
- Phonely partnered with Maitai and Groq to enhance the speed and accuracy of its AI phone support agents. While closed-source general-purpose models like GPT-4o offered high-quality outputs, Phonely faced growing limitations in latency and performance.
- Phonely transitioned from closed-source general-purpose models to custom open-source models, hosted on GroqCloud, powered by its purpose-built AI inference chip, the Groq LPU.
- The solution emerged from Groq's development of "zero-latency LoRA hotswapping" — the ability to instantly switch between multiple specialized AI model variants without any performance penalty.
- TTFT (P90) slashed by 73.4%, delivering near-instantaneous responses. Completion Time (P90) reduced by 74.6%. Accuracy elevated from 81.5% to 99.2% through strategic model refinement, exceeding GPT-4o by 4.5 percentage points.
- Phonely deployed its own speech-to-text system locally in Australia to save on latency. The partnership with Maitai and Groq enabled 300–400 millisecond response times out of the AI model.

### Pricing
- Phonely is usage-based, not agent-based, so you pay only for active AI call time.
- Starter: For very small organizations or solopreneurs receiving up to 50 calls per month. Professional: Ideal for small businesses handling 50–250 calls per month. Business: Perfect for medium-sized businesses handling 250–1,000 calls per month. Enterprise: Tailored for large organizations receiving 1,000+ calls per month, with features like custom integrations, SIP trunking, and enterprise-grade security.
- Pricing starts at \$34.99 per month (Starter), Professional at \$99.99/mo, Business at \$499.99/mo.
- Phonely starts at \$34.99 per month for 200 minutes, with scalable pricing that can drop to 10 cents per minute at higher usage.

### Ideal Customer Profile (ICP)
- From small businesses to governments, Phonely is transforming how organizations handle communication.
- Phonely excels in appointment scheduling and lead qualification. The company has partnered with major firms handling insurance, legal, and automotive customer interactions.
- Contact Centers & BPOs: Automate inbound and outbound support. Healthcare: Schedule appointments, handle refills, manage patient communications securely. Insurance & Financial Services: Process claims, verify information, and handle payments with compliance. SMBs & Enterprises: Manage bookings, lead qualification, order tracking, and customer support.
- One of Phonely's customers is replacing 350 human agents this month alone.

---

## Sources

1. **Y Combinator — Phonely profile** — https://www.ycombinator.com/companies/phonely
2. **Startup Daily** — "Y Combinator backs AI-based virtual receptionist startup Phonely with \$750,000" — https://www.startupdaily.net/topic/funding/y-combinator-backs-ai-based-virtual-receptionist-startup-phonely-with-750000/
3. **VentureBeat** — "Phonely's new AI agents hit 99% accuracy" — https://venturebeat.com/ai/phonelys-new-ai-agents-hit-99-accuracy-and-customers-cant-tell-theyre-not-human
4. **Phonely.ai (About page)** — https://www.phonely.ai/about
5. **Phonely.ai (Pricing page)** — https://www.phonely.ai/pricing
6. **Phonely blog — Maitai + Groq benchmark post** — https://www.phonely.ai/blogs/phonely-sets-new-benchmark-for-ai-phone-support-with-lightning-fast-model-inference-through-maitai-and-groq
7. **Business News Australia** — "Voice AI startup Phonely enters partnership with TSA Group" — https://www.businessnewsaustralia.com/articles/melbourne-founded-voice-ai-startup-phonely-removes-annoying-pauses--sees-revenue-dial-up.html
8. **PitchBook — Phonely profile** — https://pitchbook.com/profiles/company/597004-03
9. **Tracxn — Phonely profile** — https://tracxn.com/d/companies/phonely/__UuvtdLBvsUBN-UaYmBiyjg0w_42FLsiWXJOoYT0g-68
10. **Maitai blog — Breakthrough Performance for Enterprise Voice AI** — https://blog.trymaitai.ai/phonely-multi-lora/

---

## Open Questions

1. **True total funding**: Tracxn shows \$500 K across 2 rounds, but Business News Australia quotes Bodewes citing a further \$2.2 M raise. No Series A has been publicly confirmed — the discrepancy likely reflects partially undisclosed rounds.
2. **Revenue verification**: Getlatka reports \$5 M revenue (self-reported). This has not been independently confirmed by press or filings.
3. **99.2% accuracy metric**: Based on Phonely's own internal evaluation across four model iterations. No independent third-party audit has been published.
4. **Enterprise retention**: No public data on churn, NRR, or contract lengths. The "4,500-agent BPO" and "350 agents replaced" case studies are testimonial-level, not independently verified.
5. **Competitive moat durability**: The Groq + Maitai + LoRA stack is a partnership, not proprietary hardware. If Groq inference speeds commoditize, the latency edge may narrow.
6. **Compliance depth**: HIPAA compliance is claimed with BAA available, but no public SOC 2 Type II audit report or ISO certificate has been linked directly.
7. **International expansion**: Founded in Melbourne, HQ'd in San Francisco. Extent of non-US go-to-market is not well documented beyond the TSA Group (Australia) partnership.
