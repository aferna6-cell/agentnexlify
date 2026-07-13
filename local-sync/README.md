# AgentNexLiFy Local Folder Sync

Point it at a folder on your computer; your AI assistant knows every document
in it. No uploading file after file — drop documents in the folder and they
sync automatically.

## Requirements

Python 3.9+ (preinstalled on macOS and most Linux; on Windows install from
python.org). Zero packages to install — the script is standard library only.

## Setup

The easy way: open the dashboard **Knowledge** page, click **Download
script**, then **Get sync command** — it hands you a ready-to-paste command
with a sync token baked in. The token lasts 180 days and only works for
knowledge sync (it can't touch anything else in your account).

Manual equivalent:

1. Download `anx_kb_sync.py` (from the Knowledge page or this folder).
2. Generate a sync token on the Knowledge page ("Get sync command").
3. Run it:

```bash
# one-time sync
python anx_kb_sync.py ~/Documents/business-docs \
    --tenant-id YOUR_TENANT_ID --token YOUR_TOKEN --once

# keep it running - re-scans every 5 minutes
python anx_kb_sync.py ~/Documents/business-docs \
    --tenant-id YOUR_TENANT_ID --token YOUR_TOKEN --watch
```

Or set credentials once via environment variables `ANX_TENANT_ID`,
`ANX_TOKEN` (and optionally `ANX_API_URL`).

## What it does

- Scans the folder (and subfolders) for `.pdf`, `.docx`, `.txt`, `.md` files
- Uploads only new or changed files (sha256-diffed via
  `.anx_sync_state.json` in the folder)
- Skips hidden files, hidden folders, and files over 5 MB
- Documents show up on the dashboard Knowledge page with source
  "Local folder sync"
- `--prune` also removes knowledge-base documents whose local files were
  deleted (only ones this tool created — dashboard uploads and Drive docs
  are never touched)

## Notes

- Your plan's document limit applies; over-limit files are skipped with a
  reason printed to the terminal.
- Scanned-image PDFs with no extractable text are skipped by the server.
- Stop watching anytime with Ctrl+C; state is saved after every pass.
