#!/usr/bin/env python3
"""AgentNexLiFy local folder sync — point it at a folder, your AI knows it.

Watches a local folder for PDF/DOCX/TXT/MD documents and uploads new or
changed files to your AgentNexLiFy knowledge base. Runs on plain Python 3.9+
with zero dependencies — nothing to pip install.

Usage:
    python anx_kb_sync.py ~/Documents/business-docs \
        --tenant-id <your-tenant-id> --token <your-api-token> --once

    # keep it running, re-scan every 5 minutes:
    python anx_kb_sync.py ~/Documents/business-docs --watch

    # also remove KB documents whose local files were deleted:
    python anx_kb_sync.py ~/Documents/business-docs --once --prune

Credentials can come from env vars instead of flags:
    ANX_TENANT_ID, ANX_TOKEN, ANX_API_URL

State lives in .anx_sync_state.json inside the synced folder — sha256 per
file, so unchanged files are never re-uploaded. Documents land with
source=local_sync so the dashboard Knowledge page shows where they came from.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEFAULT_API_URL = "https://agentnexlify-production.up.railway.app"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}
MAX_FILE_BYTES = 5 * 1024 * 1024  # server rejects bigger files; skip locally
STATE_FILENAME = ".anx_sync_state.json"
BATCH_SIZE = 20  # files per upload request (server cap is 100)
SOURCE = "local_sync"


# ---------------------------------------------------------------- scanning


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_folder(folder: Path) -> dict:
    """Map of relative path -> {sha256, size} for every supported document.

    Skips hidden files/dirs, unsupported extensions, and oversized files.
    Relative paths use forward slashes so state files move across OSes.
    """
    found = {}
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            path = Path(root) / name
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            size = path.stat().st_size
            if size > MAX_FILE_BYTES:
                print(f"  skip {name}: over 5MB limit", file=sys.stderr)
                continue
            rel = path.relative_to(folder).as_posix()
            found[rel] = {"sha256": sha256_file(path), "size": size}
    return found


def diff_state(current: dict, previous: dict) -> tuple:
    """(changed, removed): relpaths to upload and relpaths that vanished."""
    changed = [
        rel
        for rel, meta in sorted(current.items())
        if previous.get(rel, {}).get("sha256") != meta["sha256"]
    ]
    removed = [rel for rel in sorted(previous) if rel not in current]
    return changed, removed


# ------------------------------------------------------------------- state


def load_state(state_path: Path) -> dict:
    try:
        with open(state_path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("files", {}) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state_path: Path, files: dict) -> None:
    payload = {"version": 1, "files": files}
    tmp = state_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    os.replace(tmp, state_path)


# --------------------------------------------------------------- transport


def encode_multipart(files: list, extra_fields: dict) -> tuple:
    """Build a multipart/form-data body from [(filename, bytes), ...].

    Returns (body_bytes, content_type). Stdlib has no multipart encoder,
    so we assemble the RFC 2388 body by hand.
    """
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in extra_fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    for filename, data in files:
        safe_name = filename.replace('"', "'")
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="files"; '
                f'filename="{safe_name}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode("utf-8")
        )
        parts.append(data)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def api_request(method: str, url: str, token: str, body=None, content_type=None):
    """One HTTP call; returns parsed JSON. Raises RuntimeError with a
    readable message on HTTP or network failure."""
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"{method} {url} failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} unreachable: {exc.reason}") from exc
    return json.loads(raw) if raw else {}


def upload_batch(config: dict, batch: list) -> list:
    """POST one multipart batch; returns the per-file result list."""
    body, content_type = encode_multipart(batch, {"source": SOURCE})
    url = f"{config['api_url']}/api/v1/kb/{config['tenant_id']}/documents"
    payload = api_request("POST", url, config["token"], body, content_type)
    return payload.get("results", [])


def prune_removed(config: dict, removed: list) -> int:
    """Delete KB documents (source=local_sync only) whose files vanished."""
    base = f"{config['api_url']}/api/v1/kb/{config['tenant_id']}/documents"
    listing = api_request("GET", base, config["token"])
    remote = {
        doc["filename"]: doc["id"]
        for doc in listing.get("documents", [])
        if doc.get("source") == SOURCE
    }
    deleted = 0
    for rel in removed:
        doc_id = remote.get(rel)
        if not doc_id:
            continue
        api_request("DELETE", f"{base}/{doc_id}", config["token"])
        deleted += 1
    return deleted


# -------------------------------------------------------------------- sync


def sync_once(config: dict) -> dict:
    """One scan-diff-upload pass. Returns a summary dict."""
    folder = config["folder"]
    state_path = folder / STATE_FILENAME
    previous = load_state(state_path)
    current = scan_folder(folder)
    changed, removed = diff_state(current, previous)

    summary = {
        "scanned": len(current),
        "uploaded": 0,
        "skipped": 0,
        "errors": 0,
        "pruned": 0,
    }

    synced = dict(previous)
    for start in range(0, len(changed), BATCH_SIZE):
        rels = changed[start : start + BATCH_SIZE]
        batch = [(rel, (folder / rel).read_bytes()) for rel in rels]
        try:
            results = upload_batch(config, batch)
        except RuntimeError as exc:
            print(f"  upload failed: {exc}", file=sys.stderr)
            summary["errors"] += len(rels)
            continue
        by_name = {r.get("filename"): r for r in results}
        for rel in rels:
            outcome = by_name.get(rel, {})
            status = outcome.get("status")
            if status in ("added", "updated", "unchanged"):
                summary["uploaded"] += 1
                synced[rel] = current[rel]
            else:
                summary["skipped"] += 1
                reason = outcome.get("reason") or outcome.get("error") or status
                print(f"  skipped {rel}: {reason}", file=sys.stderr)

    for rel in removed:
        synced.pop(rel, None)
    if removed and config.get("prune"):
        try:
            summary["pruned"] = prune_removed(config, removed)
        except RuntimeError as exc:
            print(f"  prune failed: {exc}", file=sys.stderr)
            summary["errors"] += 1

    save_state(state_path, synced)
    return summary


def run(config: dict) -> int:
    while True:
        started = time.strftime("%H:%M:%S")
        summary = sync_once(config)
        print(
            f"[{started}] scanned {summary['scanned']} files: "
            f"{summary['uploaded']} synced, {summary['skipped']} skipped, "
            f"{summary['pruned']} pruned, {summary['errors']} errors"
        )
        if not config["watch"]:
            return 1 if summary["errors"] else 0
        time.sleep(config["interval"])


# -------------------------------------------------------------------- main


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync a local folder into your AgentNexLiFy knowledge base."
    )
    parser.add_argument("folder", help="Folder containing PDF/DOCX/TXT/MD docs")
    parser.add_argument(
        "--tenant-id", default=os.environ.get("ANX_TENANT_ID", "")
    )
    parser.add_argument("--token", default=os.environ.get("ANX_TOKEN", ""))
    parser.add_argument(
        "--api-url", default=os.environ.get("ANX_API_URL", DEFAULT_API_URL)
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Sync once and exit")
    mode.add_argument(
        "--watch", action="store_true", help="Keep running, re-scan on interval"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between scans in --watch mode (default 300)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Also delete KB docs whose local files were removed",
    )
    return parser.parse_args(argv)


def main(argv: list) -> int:
    args = parse_args(argv)
    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Not a folder: {folder}", file=sys.stderr)
        return 2
    if not args.tenant_id or not args.token:
        print(
            "Missing credentials. Pass --tenant-id and --token, or set "
            "ANX_TENANT_ID and ANX_TOKEN.",
            file=sys.stderr,
        )
        return 2
    config = {
        "folder": folder,
        "tenant_id": args.tenant_id,
        "token": args.token,
        "api_url": args.api_url.rstrip("/"),
        "watch": args.watch and not args.once,
        "interval": max(args.interval, 30),
        "prune": args.prune,
    }
    return run(config)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
