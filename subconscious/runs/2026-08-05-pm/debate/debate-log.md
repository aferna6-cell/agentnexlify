# Debate Log — Run 104 (2026-08-05-pm)

Top 3 debated: Idea A (Step 9J), Idea C (PR tombstoning), Idea E (merge readiness reporter).

---

## Round 1: Idea A — Step 9J Accumulated-Issue Auto-Closer

### ATTACK
The loop-health issue accumulation (#633, #635) is a UX nuisance, not an operational
gap. GH history preserves closed issues — humans who care about trend data will look at
closed issues. More importantly, auto-closing might hide the signal that the autopilot
loop has been failing for multiple consecutive days. A human should see "open since
2026-08-04" on #633 and feel urgency. Closing it after 24h removes that urgency signal.
Also: if Step 9D fires and the loop is broken, Step 9J closes the old evidence THEN
Step 9D opens a fresh issue — a human checking GH between those two steps sees nothing.
Brief window of information loss.

### DEFEND
The accumulation problem is genuine, not cosmetic. When #633 and #635 are both open,
the human cannot tell which is the CURRENT state. Do they comment on #633 or #635?
Which is "fresher"? The answer is knowable (look at creation date) but requires work.
The pattern should be: ONE open issue per condition, always the current one.

Urgency signal is preserved: the remaining OPEN issue (the fresh one from today's run)
STILL shows loop failure urgency. It's not removing the signal; it's consolidating it
into a single authoritative issue. The trend data (3 consecutive failure days) belongs
in the issue BODY, not in 3 separate issues.

Brief window of info loss: Step 9J runs before Step 9D. It closes the old issue, then
9D immediately opens a fresh one if the condition persists. Window is sub-second inside
a nightly run. Not a real concern.

Precedent: GitHub itself closes old Dependabot alerts when a newer version supersedes
them. This is the same pattern — "supersede, not accumulate."

### VERDICT: A PASSES
Attack's concern about urgency signal is valid but addressed by keeping body in the
new issue. Auto-close at end of each cycle keeps the list clean and unambiguous.

---

## Round 2: Idea C — PR Tombstoning

### ATTACK
Auto-closing subconscious draft PRs after 14 days eliminates evidence of what was tried,
removes pressure to merge, and could close PRs that are close to approval. The Step 9G
PRs (#625, #626) are 3 days old — they'd survive the threshold for now, but the pattern
would auto-close them before the human acts if it's a moderately busy week. The PR dedup
guard was created specifically to REUSE existing PRs, not to age them out. Tombstoning
directly contradicts the guard's design intent.

Also: PR debt (5 open) is a symptom of approval friction, not a cause. Auto-closing
doesn't fix the friction. The human who isn't merging PRs also won't be motivated
differently because fewer PRs are open — they'll just get a smaller notification badge.

### DEFEND
There's real cost to a 10+ PR open list: PR notifications become noise, the "what needs
action" signal is diluted. If 5 of 10 open PRs are stale subconscious drafts, the 3
Dependabot PRs that SHOULD be merged quickly get buried. Tombstoning creates scarcity
("only 1–2 subconscious PRs") that might improve merge rate on the current cycle.

The dedup guard ensures new runs don't ADD to the count. Tombstoning clears the floor.
Together they maintain a stable 1–2 PR subconscious footprint.

### VERDICT: C KILLED
Attack wins cleanly. Two decisive reasons:
1. The dedup guard's contract is "commit onto existing branches" — tombstoning deletes
   exactly what the guard preserves. Contradicts established pattern.
2. Approval friction is the root cause. Fewer visible PRs won't change that. Only
   increases cognitive distance from the evidence of pending work.

---

## Round 3: Idea E — PR Merge Readiness Reporter

### ATTACK
A daily "please merge this" comment on #625/#626 becomes noise in 3 days. The human
already knows the PRs exist — the morning digest surfaces them as priority #1. Adding a
third notification channel (PR comment, in addition to morning digest + morning digest
GH issue) just increases alert volume without changing the approval decision. The root
cause of non-merging is decision latency, not awareness. Comment-blindness applies to
PR comments the same as it applies to GH issue comments.

### DEFEND
The daily version is noisy, but a TIERED escalation version (comment at day 7, P1 issue
at day 14, P0 issue at day 21) is genuinely differentiated. It turns a monotonic "still
waiting" into an increasing urgency signal. The morning digest gives equal weight to all
priorities; this escalation would rank Step 9G above everything else after 14 days.

Step 9G PRs are already 3+ days old. At day 7 they'd get a comment; at day 14 a `critical`
issue. That's more forceful than the morning digest's #1 bullet.

### VERDICT: E WEAKENED
The tiered version has merit, but it adds S-effort complexity: need to track "last
comment date" to avoid daily spam, need to parse days-since-created, need to distinguish
"merge-ready" from "has conflicts." As designed in Idea A (XS, direct), the comparison
is unfavorable. Park the tiered escalation for run 102 mandate: if Step 9G is STILL
unmerged at day 21 (2026-08-13), raise as a P1 GH issue via a run-102 recommendation.

---

## Final Selection

**Winner: Idea A — Step 9J Accumulated-Issue Auto-Closer**

Rationale:
- Only candidate that passed all challenge rounds without weakening
- Directly observable gap (3 accumulating issues in this morning's digest)
- XS effort, HIGH confidence, zero destructive risk
- No external dependency (doesn't need Step 9G merged)
- Autonomous-executable via proven SKILL.md-edit channel
- Addresses a structural gap (no close-before-open primitive in any nightly step)

Runner-up (Idea E, tiered escalation) parks to run 102 mandate: if Step 9G is still
unmerged at day 21 (2026-08-13), make it a P1 GH issue — that's a concrete mandate item
rather than a new recommendation cycle.
