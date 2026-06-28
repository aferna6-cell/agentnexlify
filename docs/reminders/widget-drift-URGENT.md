# URGENT: Widget Drift — Human Action Required

**Filed:** 2026-06-28 (subconscious run 70)  
**Mandate:** `governance.json:run_70_mandate` — unconditional at run 70.  
**Priority:** CRITICAL — pre-commit Check 13 has been in FAIL+BLOCK mode since 2026-06-23 (5 days).

---

## The Problem

`scripts/check_project_invariants.py` exits 1 with this single failure:

```
drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js
```

Every git commit is blocked. The subconscious has attempted delivery 6 consecutive runs (65–70) without success.

---

## The Fix (30 seconds)

```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
python3 scripts/check_project_invariants.py
git add landing-page-v2/widget/agentnexlify-widget.js
git commit -m "fix: sync widget to landing-page-v2 (pre-commit unblocked)"
```

That is it. One command. No code changes. No risk.

---

## Why the Subconscious Could Not Fix This

`landing-page-v2/` is on the FORBIDDEN paths list in `.claude/skills/nightly-commit-review/SKILL.md` (legacy code protection). The nightly autonomous system correctly refused to touch it. Step 9B (autonomous governance executor, added run 66) proved it works for other tasks — ffefe61 fixed 10 em-dash violations on 2026-06-27. But landing-page-v2/ is out of scope.

The autonomous stack is not broken. This specific path is deliberately excluded. Only a human can override.

---

## Delivery Failure Chain

| Run | Date | Mechanism | Result |
|-----|------|-----------|--------|
| 65 | 2026-06-24-pm | Nightly autonomous | SKIP — cp not in nightly scope |
| 66 | 2026-06-25 | Step 9B addition to SKILL.md | SKIP — editing existing SKILL.md not in scope |
| 67 | 2026-06-25-pm | Interactive human session requested | NOT EXECUTED |
| 68 | 2026-06-26-pm | 30-second terminal command block + push notification | NOT EXECUTED |
| 69 | 2026-06-27 | Step 9B widget exception + hard run 70 deadline | Step 9B worked for em-dashes; widget cp still blocked by FORBIDDEN list |
| 70 | 2026-06-28 | Run 70 mandate fires → this file | You are reading this. |

---

## After You Fix It

The subconscious will NOT raise this topic again. It is retired from the improvement loop permanently as of run 70.

Future widget syncs: any time `widget/agentnexlify-widget.js` is updated, also update `landing-page-v2/widget/agentnexlify-widget.js`. One-liner. Add it to your widget deploy checklist.

If you want an automated guard: add `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js` to the pre-push hook or create a Makefile target.

---

*Filed by subconscious run 70 per `governance.json:run_70_mandate`. Topic retired from subconscious after this run.*
