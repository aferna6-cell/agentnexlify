# AgentNexLiFy Local Folder Sync

Point it at a folder on your computer; your AI assistant knows every document
in it. No uploading file after file — drop documents in the folder and they
sync automatically.

## Requirements

Python 3.9+ (preinstalled on macOS and most Linux; on Windows install from
python.org). Zero packages to install — the script is standard library only.

## Setup

1. Download `anx_kb_sync.py` from this folder.
2. Get your tenant ID and API token from the dashboard (Settings).
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
