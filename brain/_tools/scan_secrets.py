#!/usr/bin/env python3
"""Secret / credential scanner.

Scans vault files for credential-like values: private keys, cloud/provider tokens,
JWTs, bearer tokens, DB connection URLs with credentials, and key/secret assignments.
Specific patterns only (avoids flagging public project refs / user IDs / emails).

Exit 0 = no secrets, 1 = potential secrets (must redact before completion).
"""
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent

PATTERNS = {
    "private-key-block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36,}\b"),
    "stripe-live": re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{16,}\b"),
    "stripe-secret": re.compile(r"\b(?:sk|rk)_test_[0-9A-Za-z]{16,}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    "anthropic-key": re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),
    "bearer": re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.=]{20,}\b"),
    "db-url-creds": re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:@/]+:[^\s:@/]+@"),
    # Built from fragments so this source line itself does not resemble a credential.
    "secret-assignment": re.compile(
        r"(?i)\b(?:api[_\-]?key|secret|pass" + "word" + r"|passwd|access[_\-]?token|"
        r"refresh[_\-]?token|client[_\-]?secret|signing[_\-]?secret|webhook[_\-]?secret|"
        r"recovery[_\-]?code|session[_\-]?cookie)\b\s*"
        + r"[:=]\s*"
        + r"['\"]?[A-Za-z0-9_\-/+]{16,}"
    ),
}


def main():
    hits = []
    for p in VAULT.rglob("*"):
        if not p.is_file() or "_tools" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for name, rx in PATTERNS.items():
                if rx.search(line):
                    hits.append((str(p.relative_to(VAULT)), i, name, line.strip()[:80]))

    if hits:
        print(f"FAIL: {len(hits)} potential secret(s) — REDACT before completion:")
        for rel, ln, name, snip in hits:
            print(f"  {rel}:{ln} [{name}] {snip}")
        return 1
    print("PASS: 0 secrets/credentials detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
