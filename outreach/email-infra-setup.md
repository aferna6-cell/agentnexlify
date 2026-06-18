# Cold-Email Infrastructure Setup Runbook

Owner-executed. Goal: stand up the outbound cold-email stack that feeds the
lead engine. Decisions locked in the 2026-06-18 partner discussion. Follow
top-to-bottom in one sitting; warmup then runs untouched for ~3 weeks.

Target at steady state: **9 inboxes / 3 domains / ~250 sends per day** (~5k/mo),
all-in cost **under $100/mo**.

---

## 0. Hard rules (do not skip)

1. **Never send cold mail from `agentnexlify.com`.** One spam-trap hit poisons
   the deliverability of the real domain (welcome emails, password resets, lead
   alerts). Cold goes from separate lookalike domains only.
2. **Max ~3 inboxes per domain.** More looks like a spam farm. 9 inboxes = 3
   domains x 3 inboxes.
3. **Warmup is automated, not manual.** Do not send real prospects during
   warmup. The tool generates inbox-to-inbox traffic for ~3 weeks first.
4. **Steady-state ceiling is ~25-30 sends/inbox/day.** Do not exceed.

---

## 1. Buy 3 sending domains (~$10-15/yr each)

Register 3 lookalikes of agentnexlify.com. Suggested (check availability):

- `tryagentnexlify.com`
- `getagentnexlify.com`
- `agentnexlify.io`  (or `.co` / `agentnexlifyhq.com` if `.io` is taken)

Where: any registrar (Cloudflare Registrar = at-cost, no markup). Or buy them
inside Instantly's done-for-you flow (see Section 4, Option B) to skip DNS.

After purchase: set each domain to **301-redirect to https://agentnexlify.com**
so links in emails resolve to the real site (registrar/Cloudflare page rule).

---

## 2. Create 9 mailboxes (3 per domain)

Pick names that look like real people, not `sales@` / `noreply@`. Two per
partner-friendly first-name pattern:

| Domain | Inbox 1 | Inbox 2 | Inbox 3 |
|--------|---------|---------|---------|
| tryagentnexlify.com | aidan@ | aidan.f@ | team@ |
| getagentnexlify.com | <partner2>@ | <p2 variant>@ | hello@ |
| agentnexlify.io | <partner3>@ | <p3 variant>@ | <p4>@ |

Each partner manages 2-3 inboxes for reply-handling; sending/warmup is
centralized in Instantly so nobody babysits individual boxes.

---

## 3. DNS records — set on EACH of the 3 domains

Three records per domain. Values for SPF/DKIM come from your mailbox provider
(Google Workspace, Microsoft 365, or Instantly's hosted inboxes — the provider
shows the exact strings in its setup screen). Generic shapes:

**SPF** (TXT, host `@`):
```
v=spf1 include:<provider-spf-domain> ~all
```
- Google Workspace: `include:_spf.google.com`
- Microsoft 365: `include:spf.protection.outlook.com`

**DKIM** (TXT or CNAME, host given by provider, e.g. `google._domainkey`):
```
<paste the exact DKIM value the provider generates>
```

**DMARC** (TXT, host `_dmarc`):
```
v=DMARC1; p=none; rua=mailto:dmarc@agentnexlify.com; fo=1
```
Start at `p=none` (monitor only). After 2-3 weeks of clean sending, raise to
`p=quarantine`.

Verify all three resolve before warmup (Instantly checks this for you, or use
`dig TXT <domain>` / mxtoolbox.com).

---

## 4. Sending platform — Instantly

Decision: **Instantly** for cold (chosen over Brevo, which is better for
transactional/newsletter, not cold). The send platform is flat-rate with
unlimited sending accounts, so 9 vs 6 inboxes barely changes platform cost.

- Plan: **Growth (~$37/mo annual)** covers 9 inboxes + a few thousand sends/mo.
- Built-in warmup is included on paid plans — turn it ON for all 9 inboxes.

### Option A — bring your own mailboxes (Google/MS)
~$6/inbox/mo. You configure DNS (Section 3) yourself. Google has tightened
bulk-Workspace rules for cold outreach, so inboxes can get suspended.

### Option B — Instantly hosted / done-for-you inboxes (recommended)
~$3-4/inbox/mo. Instantly provisions domains + mailboxes + DNS pre-configured.
Cheaper, fewer suspensions, skips Section 1-3 setup. **Pick this unless you have
a reason to self-host.**

---

## 5. Warmup schedule (automated — do not send real mail yet)

| Window | Action |
|--------|--------|
| Day 0 | All 9 inboxes created, DNS verified, Instantly warmup ON |
| Weeks 1-3 | Warmup only. Zero real prospects. Let it run. |
| Week 4, day 1 | Start real sends at **5-10/inbox/day** |
| Week 4-5 | Ramp +5/inbox every few days |
| Steady state | **25-30/inbox/day** ceiling = ~250/day across 9 inboxes |

Keep warmup ON permanently alongside real sends (Instantly mixes it in).

---

## 6. Campaign setup (week 4)

- Import the lead CSV from the lead engine (`scripts/leadgen/build_leads.py`
  output: name, email, website, demo_url, etc.).
- Use the 3 pain-first sequences in `outreach/cold-sequences.md`
  (roofers / home services / insurance).
- **Run ONE vertical across all 9 inboxes first** for a clean signal. Split by
  vertical only after you know what converts — 3 underpowered tests on day one
  beats nothing learned.
- Personalize with the `demo_url` column (each prospect gets a demo framed for
  their business — already wired).

---

## 7. Cost summary

| Item | Option A (Google/MS) | Option B (Instantly hosted) |
|------|----------------------|------------------------------|
| Instantly platform | ~$37/mo | ~$37/mo |
| 9 mailboxes | ~$54/mo | ~$27-36/mo |
| 3 domains (amortized) | ~$3/mo | ~$3/mo |
| **Total** | **~$95/mo** | **~$70/mo** |
| Domains upfront | ~$30-45/yr | included or ~$30-45/yr |

---

## 8. Checklist

- [ ] 3 domains registered + 301-redirect to agentnexlify.com
- [ ] 9 mailboxes created (3 per domain, human-looking names)
- [ ] SPF + DKIM + DMARC set + verified on all 3 domains
- [ ] Instantly Growth plan active, all 9 inboxes connected
- [ ] Warmup ON for all 9
- [ ] Calendar reminder: start real sends in 3 weeks
- [ ] Lead CSV ready (needs `GOOGLE_PLACES_API_KEY` for the engine)
- [ ] First campaign = ONE vertical, all 9 inboxes

---

## Notes
- This is operator-executed (accounts + payment + DNS). The code side (lead
  engine, demo links, cold sequences, lead-capture alerts) is already built.
- The only remaining engineering dependency for go-live is the
  `GOOGLE_PLACES_API_KEY` to generate the lead list.
- Source decisions: partner discussion 2026-06-18; tool eval favored Instantly
  for cold over Brevo.
