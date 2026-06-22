---
type: report
report: validation
date: 2026-06-22
status: pass
---

# Validation Report

Deterministic validators in `_tools/`. Run from the vault root: `python3 _tools/run_all.py`.

## Scripts (`_tools/`)

| Script | Purpose |
|---|---|
| `validate_artifacts.py` | confirm all required folders + files exist |
| `validate_slugs.py` | empty filenames, invalid paths (e.g. `People` + `/.md`), dup slugs, unsafe chars |
| `validate_wikilinks.py` | resolve every double-bracket link with Obsidian semantics (filename, path, alias; ignore `#`/`\|`); report unresolved + ambiguous |
| `validate_provenance.py` | every canonical note has provenance → `Sources/` or SOURCE-MANIFEST; no placeholders |
| `scan_secrets.py` | API keys, tokens, private keys, JWTs, DB-credential URLs, secret assignments |
| `validate_manifest.py` | SOURCE-MANIFEST documents every connector + account/status fields |
| `refresh_connectors.py` | re-sync GitHub + Supabase state into connector source traces (read-only; env creds) |
| `run_all.py` | runs all validators, prints PASS/FAIL summary |

## Results — final run 2026-06-22 (`python3 _tools/run_all.py`)

| Gate | Result | Detail |
|---|---|---|
| required artifacts | **PASS** | 14 folders + 7 required files present |
| slugs/paths | **PASS** | clean; 0 empty / 0 duplicate / 0 unsafe |
| wikilinks | **PASS** | ~90 notes, ~500 links, **0 unresolved, 0 ambiguous** |
| provenance | **PASS** | 57 canonical notes; all have valid provenance, 0 placeholders |
| secrets | **PASS** | 0 secrets/credentials detected |
| manifest | **PASS** | 7 connectors documented with account + status |

**ALL GATES PASS.**

## Refresh mechanism verified
- `python3 _tools/refresh_connectors.py` with no creds → both connectors skip cleanly,
  `state.json.last_refresh` stamped, `INGESTION-LOG.md` appended. With `GITHUB_TOKEN` /
  `SUPABASE_ACCESS_TOKEN` set it rewrites the connector source traces from live state.
  See [[Refresh The Brain]].

## Notes
- Wikilink validator mirrors Obsidian: resolves by filename anywhere in vault, supports path
  links + frontmatter aliases, ignores heading/block (`#`) and display (`|`) segments.
- Secret scanner uses specific provider patterns so public identifiers (Supabase project refs,
  Slack user IDs, emails) are not false-flagged.
