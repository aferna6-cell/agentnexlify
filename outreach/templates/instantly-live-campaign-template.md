# Instantly Outreach Email Templates

Source: Claude Code session (Instantly campaign review + new campaign launch, 2026-07-16/17).

## Original live campaign template ("Small Business CT 7/10", "Roofing CT/NE", "New Leads 6/25")

**The exact body text of the original template is NOT contained in the session this file was
written from**, and it could not be re-fetched at write time: the Instantly API returned
`402 Payment Required — "Workspace does not have an active paid plan"`, so campaign sequences
are inaccessible until the workspace plan is reactivated.

What the session does establish about the original template:

- Subject line: `AI for {{company_name}}`
- **Known bug**: every send rendered the subject as literally `AI for ` (trailing blank) because
  lead payloads store the company under the camelCase key `companyName`, not `company_name`.
  Verified against sent-email records via `GET /api/v2/emails`. Use `{{companyName}}` in all
  Instantly templates in this workspace.
- Lead payloads also carried `website` and `demo_url` (`https://www.agentnexlify.com/`) variables;
  the original body contained a tracked hyperlink (link tracking was enabled and one recipient,
  reccenter@wpi.edu, clicked it).
- Single-step sequence, one variant, sent from 9 sender accounts across
  agentnexlifyhq.com / getagentnexlify.com / tryagentnexlify.com.

To recover the exact original body: reactivate the Instantly plan, then
`GET https://api.instantly.ai/api/v2/campaigns/{id}` and read
`sequences[0].steps[0].variants[0].body` for campaign IDs
`6b3239fe-9368-407b-9ab8-bb5c7642e3f8`, `68076b2e-7d32-4817-aed4-171bdc006a66`,
`d7c34941-91e6-425e-b00a-d3a8d4d7cfb2`.

---

The three templates below were provided by Aidan in the session and deployed verbatim as new
campaigns on 2026-07-17. Greeting renders as plain "Hi," (leads have company names, not first
names). All use `{{companyName}}` where a company variable is needed.

## Template 1 — New outreach, no hyperlink

Campaign: **New Outreach (fresh leads) 7/16** (`7a4c8bad-ed83-48df-808d-829b96186058`)
Audience: fresh Google-Places-sourced CT small-business leads (463 at launch).

**Subject:** `AI for {{companyName}}`

```
Hi,

Your competitors are already using AI to save time, streamline operations, and create a better experience for their customers.

The businesses that adopt AI now will have a significant advantage over the businesses that wait to figure it out later.

At Agent NexLiFy, we've made it simple and affordable for small businesses to leverage AI without the complexity or large investment most people expect.

The opportunity is here today. The question is whether your business will be ahead of the curve or trying to catch up later.

Let's put 15 minutes on the calendar next week and show you exactly what this could look like for your business.

Thank you,
The Team at Agent NexLiFy
```

## Template 2 — Follow-up to people who opened the email (no click)

Campaign: **Follow-Up - Email Openers 7/16** (`2590060e-4ba3-4e6a-a13e-11c338cd5dea`)
Audience: 316 leads from the three original campaigns with opens > 0, clicks = 0, replies = 0.

**Subject:** `Following up - AI for {{companyName}}`

```
Hi,

I wanted to follow up on my note from a few weeks ago regarding Agent NexLiFy and how we're helping small businesses leverage AI.

Do you have 15 minutes for a quick conversation this week or next?

We're seeing more and more small businesses use AI to save time, automate repetitive tasks, improve responsiveness, and compete more effectively without adding headcount or overhead.

The businesses getting started now are putting themselves in a much better position than the businesses waiting to figure it out later.

If nothing else, we'd be happy to share what we're seeing in the market and how other small businesses are finding success with AI.

Thank you,
The Team at Agent NexLiFy
```

## Template 3 — Follow-up to anyone who clicked the link

Campaign: **Follow-Up - Link Clickers 7/16** (`dc798cad-ba60-44eb-a15a-d34c6ce7390d`)
Audience: leads with clicks > 0, replies = 0 (one lead at launch; campaign completed same day).

**Subject:** `Following up on Agent NexLiFy`

```
Hi,

I wanted to follow up on my note from a few weeks ago and see if you had any thoughts or questions after learning a bit more about Agent NexLiFy.

Let's put 15 minutes on the calendar this week or next to discuss whether there may be an opportunity to leverage AI within your business.

At a minimum, we'd be happy to share what we're seeing in the market and how other small businesses are finding success with AI.

Thank you,
The Team at Agent NexLiFy
```

---

Sending config shared by all three campaigns: M-F 09:00-18:00 America/Detroit, 9 sender
accounts, daily limit 270, stop-on-reply, open + link tracking, unsubscribe header enabled.
Prior repliers are excluded from all audiences.
