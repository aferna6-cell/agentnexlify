---
name: security-patch-from-review
description: Systematically close every finding from a code review or audit report by parsing findings, fixing in severity order, tracking status, and committing with matching classification codes. Use when user says 'security-patch-from-review', 'patch findings', 'fix review findings', 'close security findings', 'patch audit results', or asks about security patch from review.
version: 1.0.0
origin: claude
user_invocable: true
triggers:
- security-patch-from-review
- patch findings
- fix review findings
- close security findings
- patch audit results
effort: high
---

# Security Patch from Review

Consume a structured review/audit findings list and systematically close every item.

## Usage

- `/security-patch-from-review` — reads the most recent review from agent-comms or asks for input
- `/security-patch-from-review <path-to-review.md>` — reads a specific review file

## When to Use
- Systematically fixing all findings from a completed security audit or code review
- Creating an auditable chain of security fixes with consistent commit messages

## When NOT to Use
- Running a new security scan (use security-audit instead)
- Fixing a single non-security bug (just fix it directly)
- Reviewing code for correctness (use review skill instead)

## Workflow

### Step 1: Parse Findings

Read the review and extract every finding into a tracking list:

```
| Code | Severity | File | Description | Status |
|------|----------|------|-------------|--------|
| C1 | CRITICAL | file.py:123 | Description | PENDING |
| H1 | HIGH | file.py:456 | Description | PENDING |
```

If the review doesn't use codes (C1, H1, M1...), assign them based on severity ordering.

### Step 2: Fix in Severity Order

Process: CRITICAL → HIGH → MEDIUM → LOW.

For each finding:
1. Read the file at the referenced line
2. Understand the full context (read surrounding code)
3. Apply the minimal targeted fix
4. Mark status: FIXED
5. If a finding is invalid or already fixed: mark SKIPPED with reason

### Step 3: Verify No Regressions

After all fixes:
```bash
python3 -m pytest tests/ -x --tb=short
```

If tests fail, identify which fix caused it and adjust.

### Step 4: Commit

Use the same classification codes from the review:

```
fix(security): resolve all review findings from <source>

Findings addressed:
- C1: <what was fixed>
- C2: <what was fixed>
- H1: <what was fixed>
- H2: <what was fixed>
- M1: <what was fixed>

Skipped (with reason):
- L2: Already fixed in commit abc123
```

### Step 5: Report Back

```
## Patch Report

| Code | Status | Fix Applied |
|------|--------|-------------|
| C1 | FIXED | Added tenant verification to send_campaign |
| H1 | FIXED | Enabled Twilio signature check |
| M1 | SKIPPED | Already resolved in prior commit |

Total: N fixed, N skipped, N remaining
Tests: PASS/FAIL
```

## Key Discipline

- Same classification codes in commit as in review (auditable chain)
- Never skip a CRITICAL or HIGH without explicit justification
- One commit per review (atomic — either all findings are addressed or none)
- If a fix is too risky, mark as DEFERRED with explanation, don't silently skip
