---
source_url: https://www.searchenginejournal.com/how-ai-agents-see-your-website-and-how-to-build-for-them/570443/
fetched_at: 2026-04-17T22:04:19Z
category: growth
title: How AI Agents See Your Website (And How To Build For Them)
---

# How AI Agents See Your Website (And How To Build For Them)

Every major AI platform can now browse websites autonomously. Chrome’s auto browse scrolls and clicks. ChatGPT Atlas fills forms and completes purchases. Perplexity Comet researches across tabs. But none of these agents sees your website the way a human does.

This is Part 4 in a five-part series on optimizing websites for the agentic web. Part 1 covered the evolution from SEO to AAIO. Part 2 explained how to get your content cited in AI responses. Part 3 mapped the protocols forming the infrastructure layer. This article gets technical: how AI agents actually perceive your website, and what to build for them.

The core insight is one that keeps coming up in my research: The most impactful thing you can do for AI agent compatibility is the same work web accessibility advocates have been pushing for decades. The accessibility tree, originally built for screen readers, is becoming the primary interface between AI agents and your website.

According to the 2025 Imperva Bad Bot Report (Imperva is a cybersecurity company), automated traffic surpassed human traffic for the first time in 2024, constituting 51% of all web interactions. Not all of that is agentic browsing, but the direction is clear: the non-human audience for your website is already larger than the human one, and it’s growing. Throughout this article, we draw exclusively from official documentation, peer-reviewed research, and announcements from the companies building this infrastructure.

## Three Ways Agents See Your Website

When a human visits your website, they see colors, layout, images, and typography. When an AI agent visits, it sees something entirely different. Understanding what agents actually perceive is the foundation for building websites that work for them.

The major AI platforms use three distinct approaches, and the differences have direct implications for how you should structure your website.

## Vision: Reading Screenshots

Anthropic’s Computer Use takes the most literal approach. Claude captures screenshots of the browser, analyzes the visual content, and decides what to click or type based on what it “sees.” It’s a continuous feedback loop: screenshot, reason, act, screenshot. The agent operates at the pixel level, identifying buttons by their visual appearance and reading text from the rendered image.

Google’s Project Mariner follows a similar pattern with what Google describes as an “observe-plan-act” loop: observe captures visual elements and underlying code structures, plan formulates action sequences, and act simulates user interactions. Mariner achieved an 83.5% success rate on the WebVoyager benchmark.

The vision approach works, but it’s computationally expensive, sensitive to layout changes, and limited by what’s visually rendered on screen.

## Accessibility Tree: Reading Structure

OpenAI took a different path with ChatGPT Atlas. Their Publishers and Developers FAQ is explicit:

ChatGPT Atlas uses ARIA tags, the same labels and roles that support screen readers, to interpret page structure and interactive elements.

Atlas is built on Chromium, but rather than analyzing rendered pixels, it queries the accessibility tree for elements with specific roles (“button”, “link”) and accessible names. This is the same data structure that screen readers like VoiceOver and NVDA use to help people with visual disabilities navigate the web.

Microsoft’s Playwright MCP, the official MCP server for browser automation, takes the same approach. It provides accessibility snapshots rather than screenshots, giving AI models a structured representation of the page. Microsoft deliberately chose accessibility data over visual rendering for their browser automation standard.

## Hybrid: Both At Once

In practice, the most capable agents combine approaches. OpenAI’s Computer-Using Agent (CUA), which powers both Operator and Atlas, layers screenshot analysis with DOM processing and accessibility tree parsing. It prioritizes ARIA labels and roles, falling back to text content and structural selectors when accessibility data isn’t available.

Perplexity’s research confirms the same pattern. Their BrowseSafe paper, which details the safety infrastructure behind Comet’s browser agent, describes using “hybrid context management combining accessibility tree snapshots with selective vision.”

Observe-plan-act with visual and structural data

The pattern is clear. Even platforms that started with vision-first approaches are incorporating accessibility data. And the platforms optimizing for reliability and efficiency (Atlas, Playwright MCP) lead with the accessibility tree.

Your website’s accessibility tree isn’t a compliance artifact. It’s increasingly the primary interface agents use to understand and interact with your website.

Last year, before the European Accessibility Act took effect, I half-joked that it would be ironic if the thing that finally got people to care about accessibility was AI agents, not the people accessibility was designed for. That’s no longer a joke.

## The Accessibility Tree Is Your Agent Interface

The accessibility tree is a simplified representation of your page’s DOM that browsers generate for assistive technologies. Where the full DOM contains every div, span, style, and script, the accessibility tree strips away the noise and exposes only what matters: interactive elements, their roles, their names, and their states.

This is why it works so well for agents. A typical page’s DOM might contain thousands of nodes. The accessibility tree reduces that to the elements a user (or agent) can actually interact with: buttons, links, form fields, headings, landmarks. For AI models that process web pages within a limited context window, that reduction is significant.

OpenAI’s Publishers and Developers FAQ is very clear about this:

Follow WAI-ARIA best practices by adding descriptive roles, labels, and states to interactive elements like buttons, menus, and forms. This helps ChatGPT recognize what each element does and interact with your site more accurately.

Making your website more accessible helps ChatGPT Agent in Atlas understand it better.

Research data backs this up. The most rigorous data on this comes from a UC Berkeley and University of Michigan study published for CHI 2026, the premier academic conference on human-computer interaction. The researchers tested Claude Sonnet 4.5 on 60 real-world web tasks under different accessibility conditions, collecting 40.4 hours of interaction data across 158,325 events. The results were striking:

Under standard conditions, the agent succeeded nearly 80% of the time. Restrict it to keyboard-only interaction (simulating how screen reader users navigate) and success drops to 42%, taking twice as long. Restrict the viewport (simulating magnification tools), and success drops to 28%, taking over three times as long.

The paper identifies three categories of gaps:

Perception gaps: agents can’t reliably access screen reader announcements or ARIA state changes that would tell them what happened after an action.

Cognitive gaps: agents struggle to track task state across multiple steps.

Action gaps: agents underutilize keyboard shortcuts and fail at interactions like drag-and-drop.

The implication is direct. Websites that present a rich, well-labeled accessibility tree give agents the information they need to succeed. Websites that rely on visual cues, hover states, or complex JavaScript interactions without accessible alternatives create the conditions for agent failure.

Perplexity’s search API architecture paper from September 2025 reinforces this from the content side. Their indexing system prioritizes content that is “high quality in both substance and form, with information captured in a manner that preserves the original content structure and layout.” Websites “heavy on well-structured data in list or table form” benefit from “more formulaic parsing and extraction rules.” Structure isn’t just helpful. It’s what makes reliable parsing possible.

## Semantic HTML: The Agent Foundation

The accessibility tree is built from your HTML. Use semantic elements, and the browser generates a useful accessibility tree automatically. Skip them, and the tree is sparse or misleading.

This isn’t new advice. Web standards advocates have been screaming “use semantic HTML” for two decades. Not everyone listened. What’s new is that the audience has expanded. It used to be about screen readers and a relatively small percentage of users. Now it’s about every AI agent that visits your website.

Use native elements. A <button> element automatically appears in the accessibility tree with the role “button” and its text content as the accessible name. A <div onclick="doSomething()"> does not. The agent doesn’t know it’s clickable.

<!-- Agent can identify and interact with this -->

<button type="submit">Search flights</button>

<!-- Agent may not recognize this as interactive -->

<div class="btn btn-primary" onclick="searchFlights()">Search flights</div>

Label your forms. Every input needs an associated label. Agents read labels to understand what data a field expects.

<!-- Agent knows this is an email field -->

<label for="email">Email address</label>

<input type="email" id="email" name="email" autocomplete="email">

<!-- Agent sees an unlabeled text input -->

<input type="text" placeholder="Enter email...">

The autocomplete attribute deserves attention. It tells agents (and browsers) exactly what type of data a field expects, using standardized values like name, email, tel, street-address, and organization. When an agent fills a form on someone’s behalf, autocomplete attributes make the difference between confident field mapping and guessing.

Establish heading hierarchy. Use h1 through h6 in logical order. Agents use headings to understand page structure and locate specific content sections. Skip levels (jumping from h1 to h4) create confusion about content relationships.

Use landmark regions. HTML5 landmark elements (<nav>, <main>, <aside>, <footer>, <header>) tell agents where they are on the page. A <nav> element is unambiguously navigation. A <div class="nav-wrapper"> requires interpretation. Clarity for the win, always.

<li><a href="/products">Products</a></li>

Microsoft’s Playwright test agents, introduced in October 2025, generate test code that uses accessible selectors by default. When the AI generates a Playwright test, it writes:

const todoInput = page.getByRole('textbox', { name: 'What needs to be done?' });

Not CSS selectors. Not XPath. Accessible roles and names. Microsoft built its AI testing tools to find elements the same way screen readers do, because it’s more reliable.

The final slide of my Conversion Hotel keynote about optimizing websites for AI agents. (Image Credit: Slobodan Manic)

## ARIA: Useful, Not Magic

OpenAI recommends ARIA (Accessible Rich Internet Applications), the W3C standard for making dynamic web content accessible. But ARIA is a supplement, not a substitute. Like protein shakes: useful on top of a real diet, counterproductive as a replacement for actual food.

The first rule of ARIA, as defined by the W3C:

If you can use a native HTML element or attribute with the semantics and behavior you require already built in, instead of re-purposing an element and adding an ARIA role, state or property to make it accessible, then do so.

The fact that the W3C had to make “don’t use ARIA” the first rule of ARIA tells you everything about how often it gets misused.

Adrian Roselli, a recognized web accessibility expert, raised an important concern in his October 2025 analysis of OpenAI’s guidance. He argues that recommending ARIA without sufficient context risks encouraging misuse. Websites that use ARIA are generally less accessible according to WebAIM’s annual survey of the top million websites, because ARIA is often applied incorrectly as a band-aid over poor HTML structure. Roselli warns that OpenAI’s guidanc

[truncated]
