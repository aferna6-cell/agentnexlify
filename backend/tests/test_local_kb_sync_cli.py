"""Tests for the local folder-sync CLI (local-sync/anx_kb_sync.py) — goal
item 4. The CLI is stdlib-only and lives outside backend/, so it is loaded
here via importlib.

Contracts:
  - scan picks up pdf/docx/txt/md only, skips hidden + oversized, posix paths
  - diff is sha-based: new/changed upload, unchanged don't, vanished removed
  - state file round-trips and survives corruption
  - multipart body carries source=local_sync + each file
  - sync_once uploads in batches, keeps failed files out of state (retry),
    prunes remote local_sync docs for vanished files only when asked
  - main() exits 2 on bad folder / missing credentials
"""

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_CLI_PATH = Path(__file__).resolve().parents[2] / "local-sync" / "anx_kb_sync.py"
_spec = importlib.util.spec_from_file_location("anx_kb_sync", _CLI_PATH)
cli = importlib.util.module_from_spec(_spec)
sys.modules["anx_kb_sync"] = cli
_spec.loader.exec_module(cli)


def _config(folder, **overrides):
    config = {
        "folder": folder,
        "tenant_id": "t-1",
        "token": "tok",
        "api_url": "https://api.example.com",
        "watch": False,
        "interval": 30,
        "prune": False,
    }
    config.update(overrides)
    return config


# ---------------------------------------------------------------------------
# Scan + diff + state
# ---------------------------------------------------------------------------


class TestScanFolder:
    def test_supported_extensions_only(self, tmp_path):
        (tmp_path / "faq.md").write_text("hours")
        (tmp_path / "menu.PDF").write_bytes(b"%PDF-fake")
        (tmp_path / "photo.png").write_bytes(b"\x89PNG")
        (tmp_path / ".hidden.md").write_text("secret")
        found = cli.scan_folder(tmp_path)
        assert set(found) == {"faq.md", "menu.PDF"}
        assert found["faq.md"]["sha256"]

    def test_nested_paths_are_posix_relative(self, tmp_path):
        nested = tmp_path / "policies" / "2026"
        nested.mkdir(parents=True)
        (nested / "refunds.txt").write_text("30 days")
        found = cli.scan_folder(tmp_path)
        assert list(found) == ["policies/2026/refunds.txt"]

    def test_hidden_dirs_and_oversized_skipped(self, tmp_path):
        hidden = tmp_path / ".git"
        hidden.mkdir()
        (hidden / "notes.md").write_text("internal")
        big = tmp_path / "big.txt"
        big.write_bytes(b"x" * (cli.MAX_FILE_BYTES + 1))
        (tmp_path / "ok.txt").write_text("fine")
        found = cli.scan_folder(tmp_path)
        assert set(found) == {"ok.txt"}


class TestDiffState:
    def test_new_changed_unchanged_removed(self):
        previous = {
            "same.md": {"sha256": "aaa"},
            "edited.md": {"sha256": "bbb"},
            "gone.md": {"sha256": "ccc"},
        }
        current = {
            "same.md": {"sha256": "aaa", "size": 1},
            "edited.md": {"sha256": "NEW", "size": 1},
            "fresh.md": {"sha256": "ddd", "size": 1},
        }
        changed, removed = cli.diff_state(current, previous)
        assert changed == ["edited.md", "fresh.md"]
        assert removed == ["gone.md"]


class TestState:
    def test_round_trip(self, tmp_path):
        state_path = tmp_path / cli.STATE_FILENAME
        files = {"a.md": {"sha256": "abc", "size": 3}}
        cli.save_state(state_path, files)
        assert cli.load_state(state_path) == files

    def test_missing_or_corrupt_returns_empty(self, tmp_path):
        state_path = tmp_path / cli.STATE_FILENAME
        assert cli.load_state(state_path) == {}
        state_path.write_text("{not json")
        assert cli.load_state(state_path) == {}


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class TestEncodeMultipart:
    def test_body_carries_fields_and_files(self):
        body, content_type = cli.encode_multipart(
            [("faq.md", b"open 9-5")], {"source": "local_sync"}
        )
        assert content_type.startswith("multipart/form-data; boundary=")
        boundary = content_type.split("boundary=")[1]
        assert boundary.encode() in body
        assert b'name="source"\r\n\r\nlocal_sync' in body
        assert b'name="files"; filename="faq.md"' in body
        assert b"open 9-5" in body
        assert body.endswith(f"--{boundary}--\r\n".encode())


class TestApiRequest:
    def test_http_error_becomes_readable_runtime_error(self):
        import urllib.error

        err = urllib.error.HTTPError(
            "https://api.example.com/x", 403, "Forbidden", {},
            io.BytesIO(b'{"detail":"Not authorized"}'),
        )
        with patch.object(cli.urllib.request, "urlopen", side_effect=err):
            try:
                cli.api_request("GET", "https://api.example.com/x", "tok")
                assert False, "should have raised"
            except RuntimeError as exc:
                assert "403" in str(exc)
                assert "Not authorized" in str(exc)

    def test_success_parses_json(self):
        response = MagicMock()
        response.read.return_value = b'{"ok": true}'
        response.__enter__ = lambda self: response
        response.__exit__ = lambda self, *a: False
        with patch.object(cli.urllib.request, "urlopen", return_value=response):
            assert cli.api_request("GET", "https://api.example.com/x", "tok") == {
                "ok": True
            }


# ---------------------------------------------------------------------------
# sync_once
# ---------------------------------------------------------------------------


class TestSyncOnce:
    def test_uploads_new_files_and_saves_state(self, tmp_path):
        (tmp_path / "faq.md").write_text("hours")
        (tmp_path / "menu.txt").write_text("espresso")
        results = [
            {"filename": "faq.md", "status": "added"},
            {"filename": "menu.txt", "status": "added"},
        ]
        with patch.object(cli, "upload_batch", return_value=results) as up:
            summary = cli.sync_once(_config(tmp_path))
        assert summary["uploaded"] == 2
        assert summary["errors"] == 0
        names = [name for name, _ in up.call_args.args[1]]
        assert names == ["faq.md", "menu.txt"]
        state = cli.load_state(tmp_path / cli.STATE_FILENAME)
        assert set(state) == {"faq.md", "menu.txt"}

    def test_second_run_uploads_nothing(self, tmp_path):
        (tmp_path / "faq.md").write_text("hours")
        with patch.object(
            cli, "upload_batch",
            return_value=[{"filename": "faq.md", "status": "added"}],
        ):
            cli.sync_once(_config(tmp_path))
        with patch.object(cli, "upload_batch") as up:
            summary = cli.sync_once(_config(tmp_path))
        up.assert_not_called()
        assert summary["uploaded"] == 0

    def test_failed_upload_stays_out_of_state_for_retry(self, tmp_path):
        (tmp_path / "faq.md").write_text("hours")
        with patch.object(
            cli, "upload_batch", side_effect=RuntimeError("boom")
        ):
            summary = cli.sync_once(_config(tmp_path))
        assert summary["errors"] == 1
        assert cli.load_state(tmp_path / cli.STATE_FILENAME) == {}

    def test_server_skip_counted_not_synced(self, tmp_path):
        (tmp_path / "faq.md").write_text("hours")
        results = [
            {"filename": "faq.md", "status": "skipped", "reason": "plan limit"}
        ]
        with patch.object(cli, "upload_batch", return_value=results):
            summary = cli.sync_once(_config(tmp_path))
        assert summary["skipped"] == 1
        assert cli.load_state(tmp_path / cli.STATE_FILENAME) == {}

    def test_removed_file_dropped_from_state_and_pruned(self, tmp_path):
        state_path = tmp_path / cli.STATE_FILENAME
        cli.save_state(state_path, {"gone.md": {"sha256": "old", "size": 4}})
        with patch.object(cli, "prune_removed", return_value=1) as prune:
            summary = cli.sync_once(_config(tmp_path, prune=True))
        prune.assert_called_once()
        assert prune.call_args.args[1] == ["gone.md"]
        assert summary["pruned"] == 1
        assert cli.load_state(state_path) == {}

    def test_no_prune_flag_no_remote_delete(self, tmp_path):
        state_path = tmp_path / cli.STATE_FILENAME
        cli.save_state(state_path, {"gone.md": {"sha256": "old", "size": 4}})
        with patch.object(cli, "prune_removed") as prune:
            summary = cli.sync_once(_config(tmp_path))
        prune.assert_not_called()
        assert summary["pruned"] == 0
        assert cli.load_state(state_path) == {}


class TestPruneRemoved:
    def test_deletes_only_matching_local_sync_docs(self):
        listing = {
            "documents": [
                {"id": "d1", "filename": "gone.md", "source": "local_sync"},
                {"id": "d2", "filename": "gone.md", "source": "upload"},
                {"id": "d3", "filename": "other.md", "source": "local_sync"},
            ]
        }
        calls = []

        def fake_api(method, url, token, body=None, content_type=None):
            calls.append((method, url))
            return listing if method == "GET" else {}

        with patch.object(cli, "api_request", side_effect=fake_api):
            deleted = cli.prune_removed(
                _config(Path(".")), ["gone.md", "never-synced.md"]
            )
        assert deleted == 1
        deletes = [url for method, url in calls if method == "DELETE"]
        assert deletes == [
            "https://api.example.com/api/v1/kb/t-1/documents/d1"
        ]


class TestUploadBatch:
    def test_posts_multipart_with_local_sync_source(self):
        seen = {}

        def fake_api(method, url, token, body=None, content_type=None):
            seen.update(method=method, url=url, body=body, ct=content_type)
            return {"results": [{"filename": "faq.md", "status": "added"}]}

        with patch.object(cli, "api_request", side_effect=fake_api):
            results = cli.upload_batch(
                _config(Path(".")), [("faq.md", b"open 9-5")]
            )
        assert results[0]["status"] == "added"
        assert seen["method"] == "POST"
        assert seen["url"].endswith("/api/v1/kb/t-1/documents")
        assert b'name="source"\r\n\r\nlocal_sync' in seen["body"]
        assert "multipart/form-data" in seen["ct"]


class TestWireFormat:
    def test_handmade_multipart_parses_through_fastapi(
        self, client, mock_supabase
    ):
        """End-to-end: the CLI's stdlib multipart body must be parseable by
        the real upload endpoint — the exact bytes that go over the wire."""
        from backend.tests.conftest import _make_auth_token

        from backend.tests.test_tenant_kb import _chain

        tenant = "00000000-0000-0000-0000-000000000001"
        mock_supabase.table.return_value = _chain([])

        body, content_type = cli.encode_multipart(
            [("faq.md", b"# Hours\nOpen 9-5")], {"source": "local_sync"}
        )
        resp = client.post(
            f"/api/v1/kb/{tenant}/documents",
            headers={
                "Authorization": f"Bearer {_make_auth_token(tenant)}",
                "Content-Type": content_type,
            },
            content=body,
        )
        assert resp.status_code == 200, resp.text
        result = resp.json()["results"][0]
        assert result["filename"] == "faq.md"
        assert result["status"] == "added"


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_bad_folder_exits_2(self, tmp_path):
        assert cli.main([str(tmp_path / "missing")]) == 2

    def test_missing_credentials_exit_2(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANX_TENANT_ID", raising=False)
        monkeypatch.delenv("ANX_TOKEN", raising=False)
        assert cli.main([str(tmp_path)]) == 2

    def test_once_runs_single_sync(self, tmp_path):
        (tmp_path / "faq.md").write_text("hours")
        with patch.object(
            cli, "upload_batch",
            return_value=[{"filename": "faq.md", "status": "added"}],
        ):
            code = cli.main(
                [
                    str(tmp_path),
                    "--tenant-id", "t-1",
                    "--token", "tok",
                    "--once",
                ]
            )
        assert code == 0
        assert set(cli.load_state(tmp_path / cli.STATE_FILENAME)) == {"faq.md"}

    def test_state_file_itself_never_synced(self, tmp_path):
        # .anx_sync_state.json is hidden (dot-prefixed) so scan skips it
        cli.save_state(tmp_path / cli.STATE_FILENAME, {})
        assert cli.scan_folder(tmp_path) == {}

    def test_error_exit_code_nonzero(self, tmp_path):
        (tmp_path / "faq.md").write_text("hours")
        with patch.object(
            cli, "upload_batch", side_effect=RuntimeError("boom")
        ):
            code = cli.main(
                [str(tmp_path), "--tenant-id", "t-1", "--token", "tok", "--once"]
            )
        assert code == 1

    def test_json_state_file_is_valid_json(self, tmp_path):
        cli.save_state(tmp_path / cli.STATE_FILENAME, {"a.md": {"sha256": "x"}})
        raw = (tmp_path / cli.STATE_FILENAME).read_text()
        assert json.loads(raw)["version"] == 1
