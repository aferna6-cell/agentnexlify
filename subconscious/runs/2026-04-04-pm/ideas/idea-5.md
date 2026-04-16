# Idea 5: Proactive Security Scan Hook (Bandit + ESLint Security)

**Category:** security
**Effort:** low (1 day setup)
**Impact:** Medium — 8 HIGH + 5 MEDIUM vulnerabilities found reactively in last audit

---

## Hypothesis

Adding Bandit (Python AST security scanner) to the pre-commit hook and `eslint-plugin-security` to the frontend lint step will catch OWASP-class vulnerabilities at write time rather than in periodic reactive audits. This shifts security left — the most efficient place to catch it.

---

## Evidence

1. git log `c815703`: "fix(security): patch 8 HIGH-severity vulnerabilities — Twilio verification, OAuth state signing, XSS, JWT secret" — 8 HIGH vulnerabilities found in a single reactive scan.
2. git log `c73a1ff`: "fix(security): patch MEDIUM vulnerabilities — XSS, SSRF, tenant isolation, HTML escaping" — followed 2 days later with 5 more MEDIUM vulnerabilities. Pattern: reactive batch fixes, not prevention.
3. `docs/dev-knowledge/bug-patterns.md`: Multiple XSS and tenant isolation bugs already documented — these classes would be caught by Bandit (hardcoded secrets, unsafe deserialization) and ESLint security (innerHTML, dangerous patterns).
4. CLAUDE.md "Development Rules": "NEVER skip security review on auth or payment endpoints" — currently enforced by human discipline only.
5. Current pre-commit hook: blocks secrets, dangerous imports, bare except — but doesn't run any security analyzer.
6. Project has `--break-system-packages` for pip installs, so Bandit can be added without venv complexity.

---

## Implementation Sketch (no code)

1. **Install Bandit**: `pip install bandit --break-system-packages`
2. **Pre-commit hook addition** — `bandit -r backend/ -ll -q` (low severity threshold, quiet output)
3. **ESLint security**: add `eslint-plugin-security` to `frontend/package.json`, add rules to `.eslintrc`
4. **GitHub Action** — add security scan step to PR validation workflow
5. **Baseline suppression** — `bandit.yaml` with known-safe exceptions to avoid false-positive noise on existing code
6. **Scope**: backend Python only for Bandit (routers/, services/); frontend JS/JSX only for ESLint security

---

## Success Metric

- Bandit runs < 10s on pre-commit
- 0 new HIGH-severity findings in next reactive audit
- ESLint security rules integrated into frontend build check
- `hooks/pre-commit` updated to show security scan output
