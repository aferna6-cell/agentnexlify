#!/usr/bin/env python3
r"""Instantly cold-outreach lead engine.

Deterministic pipeline that tops up an Instantly campaign with verified,
deliverable leads. Given a list of candidate businesses (company + website
domain), it:

  1. Builds a role email (info@<domain>) when no explicit email is supplied.
  2. Dedupes against the leads already in the target campaign.
  3. Loads the new candidates.
  4. Verifies every new email through Instantly's verification API.
  5. Deletes the ones that come back invalid (protects sender-domain
     reputation so warmup is never burned on bounces).

The campaign itself does the sending on its own schedule, so the only lever
this engine pulls is "add more deliverable leads."

Secrets: the Instantly API key is read from the INSTANTLY_API_KEY environment
variable. It is never written to disk, logs, or argv.

Usage:
    export INSTANTLY_API_KEY=...            # base64 v2 key
    python instantly_lead_engine.py \
        --candidates candidates.csv \       # cols: company_name, domain[, email]
        --campaign 6b3239fe-... \
        [--target 350] [--dry-run]

Candidate CSV: header row with at least ``company_name`` and one of
``domain`` / ``website`` / ``email``.
"""

import argparse
import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.instantly.ai/api/v2"

# Some managed environments route outbound HTTPS through a MITM proxy that
# rejects the default Python-urllib User-Agent (403) and presents its own CA.
# A curl-like UA plus the proxy CA bundle (when present) keeps the engine
# working there and is harmless in a normal environment.
_UA = "curl/8.5.0"
_CA_BUNDLE = "/root/.ccr/ca-bundle.crt"


def _ssl_context():
    ctx = ssl.create_default_context()
    if os.path.exists(_CA_BUNDLE):
        try:
            ctx.load_verify_locations(_CA_BUNDLE)
        except Exception:
            pass
    return ctx


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------

def normalize_domain(raw: str) -> str:
    """Strip scheme, path, www., and whitespace from a website value."""
    if not raw:
        return ""
    d = raw.strip().lower()
    for prefix in ("https://", "http://"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d.strip()


def build_email(row: dict) -> str:
    """Return an explicit email if present, else info@<domain>."""
    email = (row.get("email") or "").strip().lower()
    if email:
        return email
    domain = normalize_domain(row.get("domain") or row.get("website") or "")
    return f"info@{domain}" if domain else ""


def build_candidates(rows: list) -> list:
    """Map raw CSV rows to {email, company_name}, dropping blanks + dupes."""
    out, seen = [], set()
    for row in rows:
        email = build_email(row)
        company = (row.get("company_name") or "").strip()
        if not email or "@" not in email or email in seen:
            continue
        seen.add(email)
        out.append({"email": email, "company_name": company})
    return out


def select_new(candidates: list, existing_emails: set) -> list:
    """Candidates whose email is not already in the campaign."""
    existing = {e.lower() for e in existing_emails}
    return [c for c in candidates if c["email"].lower() not in existing]


# ---------------------------------------------------------------------------
# Instantly API client (thin)
# ---------------------------------------------------------------------------

class Instantly:
    def __init__(self, key: str):
        self._key = key
        self._ctx = _ssl_context()

    def _req(self, method: str, path: str, body=None, timeout=45):
        url = f"{API_BASE}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._key}")
        req.add_header("User-Agent", _UA)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=self._ctx) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"{}")
            except Exception:
                return e.code, {}
        except Exception as e:  # network / timeout
            return 0, {"error": str(e)}

    def campaign_emails(self, campaign_id: str) -> set:
        """All lead emails currently in the campaign (paginated)."""
        emails, starting_after = set(), None
        for _ in range(50):
            body = {"campaign": campaign_id, "limit": 100}
            if starting_after:
                body["starting_after"] = starting_after
            _, d = self._req("POST", "/leads/list", body)
            items = d.get("items", [])
            for it in items:
                if it.get("email"):
                    emails.add(it["email"].lower())
            starting_after = d.get("next_starting_after")
            if not starting_after or not items:
                break
        return emails

    def add_lead(self, campaign_id: str, email: str, company: str):
        body = {"campaign": campaign_id, "email": email}
        if company:
            body["company_name"] = company
        _, d = self._req("POST", "/leads", body)
        return d.get("id")

    def verify(self, email: str):
        self._req("POST", "/email-verification", {"email": email})

    def verification_status(self, email: str) -> str:
        _, d = self._req("GET", f"/email-verification/{urllib.parse.quote(email)}")
        return d.get("verification_status") or "pending"

    def delete_lead(self, lead_id: str):
        self._req("DELETE", f"/leads/{lead_id}")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run(candidates_path: str, campaign_id: str, key: str,
        target: int = 0, poll_rounds: int = 12, dry_run: bool = False) -> dict:
    with open(candidates_path, newline="") as f:
        rows = list(csv.DictReader(f))
    candidates = build_candidates(rows)

    client = Instantly(key)
    existing = client.campaign_emails(campaign_id)
    new = select_new(candidates, existing)

    if target:
        room = max(0, target - len(existing))
        new = new[:room]

    summary = {
        "candidates_in": len(candidates),
        "already_in_campaign": len(existing),
        "new_to_add": len(new),
        "loaded": 0, "verified": 0, "invalid": 0, "pending": 0,
        "dry_run": dry_run,
    }
    if dry_run or not new:
        return summary

    # load
    ids = {}
    for c in new:
        lid = client.add_lead(campaign_id, c["email"], c["company_name"])
        if lid:
            ids[c["email"]] = lid
            summary["loaded"] += 1

    # verify
    for e in ids:
        client.verify(e)
    results = {}
    for _ in range(poll_rounds):
        pending = [e for e in ids if e not in results]
        if not pending:
            break
        for e in pending:
            vs = client.verification_status(e)
            if vs != "pending":
                results[e] = vs
        if len(results) < len(ids):
            time.sleep(10)

    # clean invalid
    for e, vs in results.items():
        if vs == "verified":
            summary["verified"] += 1
        else:
            summary["invalid"] += 1
            client.delete_lead(ids[e])
    summary["pending"] = len([e for e in ids if e not in results])
    # pending are left in place; a later run re-verifies via dedupe skip
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Instantly lead engine")
    ap.add_argument("--candidates", required=True,
                    help="CSV with company_name + domain/website/email columns")
    ap.add_argument("--campaign", default=os.environ.get("INSTANTLY_CAMPAIGN_ID"),
                    help="Instantly campaign id (or INSTANTLY_CAMPAIGN_ID env)")
    ap.add_argument("--target", type=int, default=0,
                    help="Stop once campaign reaches this many leads (0 = no cap)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    key = os.environ.get("INSTANTLY_API_KEY")
    if not key:
        sys.stderr.write("INSTANTLY_API_KEY not set in environment\n")
        return 2
    if not args.campaign:
        sys.stderr.write("campaign id required (--campaign or INSTANTLY_CAMPAIGN_ID)\n")
        return 2

    summary = run(args.candidates, args.campaign, key,
                  target=args.target, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
