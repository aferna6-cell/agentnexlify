# Research Skill Graph — Command Center

## 1. Mission

Deep research system that takes ONE question and produces a multi-angle analysis no single Google search or ChatGPT prompt could ever match.

Instead of 50 open tabs and scattered notes, this system forces structured thinking through 6 research lenses, each one rethinking the question from a fundamentally different angle.

Research Question: [PASTE YOUR QUESTION HERE]
Scope: [DEFINE BOUNDARIES — what's in, what's out]
Time Horizon: [how far back and forward are we looking?]
Output Goal: [what decision does this research inform?]

## Prior Research (optional — for compound mode)
Check [[research-log]] for previous research that may connect to this question.
Relevant prior projects: [link any related projects from research-log.md, or leave empty for clean slate]

## 2. Node Map

Every node below is a knowledge file. Read the relevant ones before executing any task. The [[wikilinks]] are clickable — follow them.

### Methodology
- [[research-frameworks]] — how to approach different types of questions. start here to pick the right research structure
- [[source-evaluation]] — criteria for judging if a source is worth trusting. tier system from primary data to random blog posts
- [[synthesis-rules]] — how to combine findings across lenses without losing nuance. the hardest part of research
- [[contradiction-protocol]] — what to do when sources disagree. this is where the real insights hide

### Lenses (the core engine)
- [[technical]] — how does it work mechanically? what do the numbers actually say? strip away narrative, look at data
- [[economic]] — follow the money. who pays, who profits, what markets move, what incentives drive behavior
- [[historical]] — what patterns repeat? what's been tried before? what context does everyone forget?
- [[geopolitical]] — which countries, which power dynamics, which alliances and conflicts shape this?
- [[contrarian]] — what if the consensus is wrong? who benefits from the current narrative? what's nobody saying?
- [[first-principles]] — forget everything you think you know. rebuild from fundamental truths only

### Outputs
- [[executive-summary]] — the final synthesis. 500 words max. what did we learn, what does it mean, what's still unknown
- [[deep-dive]] — the full analysis organized by lens, with cross-references and contradictions highlighted
- [[key-players]] — people, organizations, countries that matter most on this topic
- [[open-questions]] — what we STILL don't know after research. often more valuable than what we found

### Knowledge Base
- [[concepts]] — key terms, definitions, mental models relevant to the research
- [[data-points]] — hard numbers, statistics, metrics collected during research. always with source attribution

### Sources
- [[source-template]] — template for processing raw sources into structured notes

## 3. Execution Instructions

When given a research question:

1. Read this file completely. understand the scope and goal
2. Read [[research-frameworks]] to pick the right approach for this type of question
3. Read [[source-evaluation]] so you know what counts as good evidence
4. For EACH lens in order (technical → economic → historical → geopolitical → contrarian → first-principles):
   a. Read the lens file for its specific angle and questions
   b. Research the topic THROUGH that lens only
   c. Record findings, sources, and confidence level
   d. Note any contradictions with previous lenses
5. Read [[contradiction-protocol]] — resolve or document disagreements between lenses
6. Read [[synthesis-rules]] — combine everything
7. Produce all 4 output files: [[executive-summary]], [[deep-dive]], [[key-players]], [[open-questions]]
8. Update [[concepts]] and [[data-points]] with everything learned

CRITICAL RULE: each lens must RETHINK the question, not just add more information. the technical lens and the contrarian lens should feel like they were written by two different researchers who disagree with each other. that tension is where insight lives.

## 4. Output Format (strict)

Produce your response as four clearly-delimited sections using these exact markers so the automation can parse them:

```
===EXECUTIVE_SUMMARY===
(500 words max: what did we learn, what does it mean, what's still unknown)

===DEEP_DIVE===
(full per-lens analysis with contradictions highlighted and cross-references)

===KEY_PLAYERS===
(bulleted list of people/organizations/countries that matter on this topic)

===OPEN_QUESTIONS===
- [ ] unresolved question 1
- [ ] unresolved question 2
- [ ] unresolved question 3

===NEW_CONCEPTS===
- term :: definition (one per line)

===NEW_DATA_POINTS===
- metric | value | source | date (one per line)
```
