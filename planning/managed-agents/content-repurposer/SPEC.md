# Content Repurposer Agent — Sales Spec

## One-line Pitch
"One long-form asset in. Ten channel-native posts out. Blog → Twitter, LinkedIn, Instagram, newsletter, YouTube shorts — in your voice."

## Problem Solved
SMBs create content sporadically because repurposing is manual labor: 3 hrs of editing to turn a blog into 10 social posts. Either they stop, or they post lazily. Both hurt reach.

## Target Customer
- SMB publishing 1-4 long-form pieces/month (blog, podcast, YouTube, newsletter)
- Has a brand voice + audience
- Uses social scheduling (Buffer, Hootsuite, Publer) or our AgentNexLiFy marketing addon
- Current state: posts original content once, repurposes rarely

## Pricing
| Tier | Setup | Monthly | Scope |
|------|-------|---------|-------|
| Basic | $2,000 | $500 | 1 source channel + 3 output channels + 10 repurposes/mo |
| Standard | $3,000 | $500 | 2 source channels + 5 output + 25 repurposes/mo |
| Premium | $4,000 | $500 | 3+ source + 7+ output + unlimited repurposes |

## Deliverables
- Agent trained on 10-20 samples of client's best content (voice capture)
- Source-channel watchers (RSS, YouTube API, podcast RSS, AgentNexLiFy CMS)
- Channel-native outputs:
  - **Twitter/X**: 3-5 tweet thread OR standalone tweet
  - **LinkedIn**: single post with hook + story + CTA
  - **Instagram**: caption + 5-slide carousel text + image prompts
  - **Newsletter**: intro paragraph + bullet takeaways + CTA
  - **YouTube Shorts / TikTok**: 30-60 sec script with hook
  - **Blog cross-post**: summary with link back to original
  - **Podcast promo**: 3-sentence episode promo + timestamps
- Scheduling: hand off to client's scheduler OR auto-schedule via AgentNexLiFy marketing addon
- Performance loop: pulls engagement per post → tunes future repurposing

## Positioning vs AgentNexLiFy Marketing Addon
The existing [marketing skills](../../.claude/skills/email-sequence/SKILL.md) + [seo-audit-marketing](../../.claude/skills/seo-audit-marketing/SKILL.md) already power the marketing addon for tenants.

This Content Repurposer packages that capability as a standalone managed agent for clients who don't use our core widget — expanding TAM to pure content businesses (creators, solo consultants, niche publishers).

For existing AgentNexLiFy tenants, this agent bolts onto the marketing addon and shares the same underlying skills.

## Integrations Supported
- Source ingest: RSS, YouTube (via API), Apple Podcasts RSS, Substack, Beehiiv, WordPress, Ghost
- Output scheduling: Buffer, Hootsuite, Publer, Typefully, AgentNexLiFy marketing addon
- Analytics: Twitter/X API, LinkedIn, Meta Insights, Google Analytics
- Image generation: via existing image tools in client stack (not included; optional add)

## Client Requirements
- 10-20 best-performing past pieces (voice training)
- Brand voice guide
- Audience description per channel (founder mode on LinkedIn, witty on X, educational on LinkedIn, etc.)
- API access to source + scheduler
- Hashtag + CTA library

## Setup Timeline
| Day | Milestone |
|-----|-----------|
| 0 | Kickoff + voice samples |
| 1-4 | Voice training + channel-native template build |
| 5-7 | Integration wiring (sources + schedulers) |
| 8-10 | Shadow run: 3 pieces repurposed, client approves |
| 11-14 | Auto-repurpose with approval gate per post |
| 15 | Launch with approval gate OR full auto per client preference |
| 30 | Performance loop tuning |

## Success Metrics
- Posts published/month (vs baseline)
- Engagement rate per channel (target: at or above client's manual best)
- Time saved per piece (target: 80%+)
- Follower growth across channels
- CTR to source content

## Why Managed Agent (vs DIY repurposer tools)
- Voice training = actually sounds like client, not AI slop
- Multi-hour session = can iterate on a piece across days as performance data comes in
- Approval gates = no rogue posts
- Cloud = runs without client's machine on
- Integrates with existing AgentNexLiFy marketing skills (not a separate rebuild)

## Cross-refs
- `.claude/skills/email-sequence/SKILL.md`
- `.claude/skills/seo-audit-marketing/SKILL.md`
- `.claude/skills/industry-content/SKILL.md`
- `backend/routers/marketing_campaigns.py`
