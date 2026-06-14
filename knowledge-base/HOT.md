# KB HOT — Active State Cache

Rolling 500-token snapshot of what's currently load-bearing. Read this BEFORE crawling INDEX.md (44K) or full wiki articles. Saves tokens on repeat KB queries.

Pattern source: Karpathy LLM Wiki — small "what's hot right now" file at the top of the vault, refreshed weekly.

## Rules
- Cap: ~500 tokens. If it grows past 700, prune oldest.
- Update cadence: weekly Monday during `/morning` OR after any major decision/incident
- One section per category; one line per item; link to wiki/raw if deeper read needed
- Stale items >14 days → drop unless still load-bearing

## How to use
- Claude reads `HOT.md` first on any KB-touching task
- If answer is in HOT, stop — don't crawl INDEX or full wiki
- If not, fall through to `INDEX.md` semantic catalog → wiki article → raw source

---

## Active this week

_Last updated: 2026-05-03_

### Decisions in motion
- (none yet — populate weekly)

### Recent incidents / failure modes
- (none yet — populate as they happen; cross-link to `docs/dev-knowledge/failed-approaches.md`)

### Live audits / specs
- `audits/audit-architecture-2026-05-02.md` — latest architecture audit
- `audits/audit-ops-automations-2026-05-01.md` — ops automations wiring depth audit

### Hot tenants / customers
- MTOptions — top message volume (704), textback automation activation runbook live

### Hot competitors
- GoHighLevel — primary competitive frame; widget-first + lower friction is the wedge

### Hot tech bets
- Claude Opus 4.7 (`claude-opus-4-7`) — xhigh effort default, self-verification, /ultrareview
- Issue-to-PR loop — 15-min poll cadence
- KB autopopulate — twice-daily 6 AM + 6 PM

---

## Cross-refs
- Full catalog: `INDEX.md`
- Append-only history: `log.md`
- Pending raw → wiki: `PENDING.md`
- Karpathy pattern: `wiki/ai-llm/llm-wiki-karpathy-pattern.md`
- KB-first rule: `.claude/rules/kb-first.md`
