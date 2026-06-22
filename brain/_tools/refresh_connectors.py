#!/usr/bin/env python3
"""Refresh the brain from live GitHub + Supabase state.

This is the deterministic re-sync mechanism for the vault. Run it on demand or on a
schedule (cron / GitHub Action) wherever the vault lives. It re-pulls connector state and
rewrites the connector source traces + an Activity snapshot + timestamps, so the brain stays
current as GitHub/Supabase change.

It uses ONLY the Python stdlib (urllib) and reads credentials from the environment:
  GITHUB_TOKEN            - PAT with repo:read for aferna6-cell/agentnexlify
  SUPABASE_ACCESS_TOKEN   - Supabase Management API token (sbp_...)
  SUPABASE_PROJECT_REF    - default: pxserpybmajixqrmzaly (active AgentNexLiFy DB)

Missing creds for a connector → that connector is skipped with a clear message (graceful
degradation). Read-only: it performs no GitHub/Supabase writes. It NEVER writes secret values
into the vault — only counts, titles, and metadata.

Exit 0 on success (even if a connector is skipped); 1 only on an unexpected error.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
OWNER, REPO = "aferna6-cell", "agentnexlify"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
TODAY = NOW[:10]


def _get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _post(url, headers, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, headers=headers, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def refresh_github():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None, "skipped — GITHUB_TOKEN not set"
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
         "User-Agent": "vault-refresh"}
    base = f"https://api.github.com/repos/{OWNER}/{REPO}"
    open_issues, open_prs = [], []
    page = 1
    while page <= 10:
        items = _get(f"{base}/issues?state=open&per_page=100&page={page}", h)
        if not items:
            break
        for it in items:
            (open_prs if "pull_request" in it else open_issues).append(it)
        page += 1
    closed = _get(f"{base}/issues?state=closed&per_page=30&sort=updated&direction=desc", h)
    closed_issues = [c for c in closed if "pull_request" not in c]
    return {
        "open_issues": open_issues, "open_prs": open_prs,
        "recent_closed_issues": closed_issues,
    }, "ok"


def refresh_supabase():
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    ref = os.environ.get("SUPABASE_PROJECT_REF", "pxserpybmajixqrmzaly")
    if not token:
        return None, "skipped — SUPABASE_ACCESS_TOKEN not set"
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
         "User-Agent": "vault-refresh"}
    url = f"https://api.supabase.com/v1/projects/{ref}/database/query"
    sql = ("select table_name, "
           "(select count(*) from information_schema.columns c "
           " where c.table_name=t.table_name and c.table_schema='public') as cols "
           "from information_schema.tables t "
           "where table_schema='public' and table_type='BASE TABLE' order by table_name;")
    rows = _post(url, h, {"query": sql})
    return {"ref": ref, "table_count": len(rows)}, "ok"


def write_github_trace(gh):
    oi, op, rc = gh["open_issues"], gh["open_prs"], gh["recent_closed_issues"]
    top = [f"  - #{i['number']} {i['title']}" for i in oi
           if "digest" not in [l["name"] for l in i.get("labels", [])]][:15]
    p = VAULT / "Sources" / "connector-github-issues.md"
    p.write_text(
        f"""---
type: source
source_id: connector-github-issues
origin: connector
connector: GitHub
account: aferna6-cell
repo: aferna6-cell/agentnexlify
accessed: {TODAY}
last_refresh: {NOW}
sensitivity: normal
tags: [source, connector]
---

# Source: GitHub issues/PRs (auto-refreshed)

## What this is
Live snapshot from `refresh_connectors.py` of `{OWNER}/{REPO}`.

## Counts (as of {NOW})
- Open issues: {len(oi)}
- Open PRs: {len(op)}
- Recent closed issues sampled: {len(rc)}

## Top open issues (non-digest)
{chr(10).join(top) if top else "  (none)"}

## Notes
- Autonomous-dev cadence: morning-digest / nightly-commit-review / subconscious loop.
- Regenerated automatically; edits here will be overwritten on next refresh.
""", encoding="utf-8")


def write_supabase_trace(sb):
    p = VAULT / "Sources" / "connector-supabase-schema.md"
    p.write_text(
        f"""---
type: source
source_id: connector-supabase-schema
origin: connector
connector: Supabase
account: VoltOps
project: {sb['ref']}
accessed: {TODAY}
last_refresh: {NOW}
sensitivity: normal
tags: [source, connector]
---

# Source: Supabase schema (auto-refreshed)

## What this is
Live snapshot from `refresh_connectors.py` of project `{sb['ref']}` (org [[VoltOps]]).

## Counts (as of {NOW})
- public BASE TABLE count: {sb['table_count']}
- RLS expected on all tables (multi-tenant invariant).

## Notes
- This is the canonical [[AgentNexLiFy Platform]] database. No row contents read.
- Regenerated automatically; edits here will be overwritten on next refresh.
""", encoding="utf-8")


def stamp_state(results):
    sp = VAULT / "state.json"
    try:
        st = json.loads(sp.read_text())
    except Exception:
        st = {}
    st["last_refresh"] = {"at": NOW, "results": results}
    sp.write_text(json.dumps(st, indent=2), encoding="utf-8")
    with (VAULT / "INGESTION-LOG.md").open("a", encoding="utf-8") as f:
        f.write(f"\n## {NOW} — refresh_connectors.py\n- " +
                "\n- ".join(f"{k}: {v}" for k, v in results.items()) + "\n")


def main():
    results = {}
    try:
        gh, gh_status = refresh_github()
        results["github"] = gh_status
        if gh:
            write_github_trace(gh)
            results["github"] = (f"ok — {len(gh['open_issues'])} open issues, "
                                 f"{len(gh['open_prs'])} open PRs")
    except Exception as e:
        results["github"] = f"error — {e}"
    try:
        sb, sb_status = refresh_supabase()
        results["supabase"] = sb_status
        if sb:
            write_supabase_trace(sb)
            results["supabase"] = f"ok — {sb['table_count']} tables"
    except Exception as e:
        results["supabase"] = f"error — {e}"

    stamp_state(results)
    print(f"Refresh @ {NOW}")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("\nRun _tools/run_all.py next to re-validate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
