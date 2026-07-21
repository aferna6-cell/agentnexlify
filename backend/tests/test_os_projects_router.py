"""Router contracts for OS Projects, task PATCH, and MCP context-tool."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("TESTING", "1")

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.tests.conftest import SyncASGITestClient


CLAIMS = {"tenant_id": "11111111-1111-1111-1111-111111111111"}


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, sink, table):
        self._rows = rows
        self._sink = sink
        self._table = table

    @property
    def not_(self):
        return self

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self._sink.append((self._table, name, args))
            if name == "execute":
                return _Result(self._rows)
            return self

        return _method


def _db(rows_by_table, sink=None):
    sink = sink if sink is not None else []
    db = MagicMock()
    db.table.side_effect = lambda name: _Query(
        rows_by_table.get(name, []), sink, name
    )
    db._sink = sink
    return db


def _client():
    app.dependency_overrides[_get_current_tenant] = lambda: CLAIMS
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)


DRAFT = {"id": "p1", "client_id": CLAIMS["tenant_id"], "status": "draft",
         "title": "Promo", "ask": "launch promo"}
STEP = {"id": "s1", "project_id": "p1", "position": 1, "department": "marketing",
        "objective": "Draft email", "status": "pending"}


class TestProjectsRouter:
    def teardown_method(self):
        _teardown()

    def test_flag_off_hides_projects(self):
        client = _client()
        with patch("backend.routers.os_projects.flag_enabled", return_value=False):
            resp = client.get("/api/v1/os/projects")
        assert resp.status_code == 404

    def test_list_projects(self):
        client = _client()
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase",
                 return_value=_db({"os_projects": [DRAFT]}),
             ):
            resp = client.get("/api/v1/os/projects")
        assert resp.status_code == 200
        assert resp.json()["projects"][0]["id"] == "p1"

    def test_create_project_plans(self):
        client = _client()
        planned = {"project": DRAFT, "steps": [STEP]}
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase",
                 return_value=_db({}),
             ), patch(
                 "backend.routers.os_projects.plan_project",
                 new=AsyncMock(return_value=planned),
             ):
            resp = client.post(
                "/api/v1/os/projects", json={"ask": "launch a spring promo"}
            )
        assert resp.status_code == 200
        assert len(resp.json()["steps"]) == 1

    def test_create_project_limit_maps_to_422(self):
        client = _client()
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase",
                 return_value=_db({}),
             ), patch(
                 "backend.routers.os_projects.plan_project",
                 new=AsyncMock(side_effect=ValueError("active project limit reached")),
             ):
            resp = client.post(
                "/api/v1/os/projects", json={"ask": "launch a spring promo"}
            )
        assert resp.status_code == 422

    def test_get_project_with_steps(self):
        client = _client()
        db = _db({"os_projects": [DRAFT], "os_project_steps": [STEP]})
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase", return_value=db
             ):
            resp = client.get("/api/v1/os/projects/p1")
        assert resp.status_code == 200
        assert resp.json()["steps"][0]["id"] == "s1"

    def test_get_missing_project_404(self):
        client = _client()
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase",
                 return_value=_db({"os_projects": []}),
             ):
            resp = client.get("/api/v1/os/projects/nope")
        assert resp.status_code == 404

    def test_approve_draft_project(self):
        client = _client()
        sink: list = []
        db = _db({"os_projects": [DRAFT], "os_project_steps": [STEP]}, sink)
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase", return_value=db
             ):
            resp = client.post("/api/v1/os/projects/p1/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_approve_non_draft_422(self):
        client = _client()
        running = {**DRAFT, "status": "running"}
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase",
                 return_value=_db({"os_projects": [running]}),
             ):
            resp = client.post("/api/v1/os/projects/p1/approve")
        assert resp.status_code == 422

    def test_approve_planless_draft_422(self):
        client = _client()
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase",
                 return_value=_db({"os_projects": [DRAFT], "os_project_steps": []}),
             ):
            resp = client.post("/api/v1/os/projects/p1/approve")
        assert resp.status_code == 422

    def test_cancel_running_project_cancels_pending_steps(self):
        client = _client()
        sink: list = []
        running = {**DRAFT, "status": "running"}
        db = _db({"os_projects": [running]}, sink)
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase", return_value=db
             ):
            resp = client.post("/api/v1/os/projects/p1/cancel")
        assert resp.status_code == 200
        step_updates = [
            s for s in sink if s[0] == "os_project_steps" and s[1] == "update"
        ]
        assert any("canceled" in str(u[2]) for u in step_updates)

    def test_cancel_done_project_422(self):
        client = _client()
        done = {**DRAFT, "status": "done"}
        with patch("backend.routers.os_projects.flag_enabled", return_value=True), \
             patch(
                 "backend.routers.os_projects.get_service_supabase",
                 return_value=_db({"os_projects": [done]}),
             ):
            resp = client.post("/api/v1/os/projects/p1/cancel")
        assert resp.status_code == 422


class TestTaskPatch:
    def teardown_method(self):
        _teardown()

    def test_patch_updates_fields(self):
        client = _client()
        row = {"id": "t1", "enabled": False, "interval_days": 14}
        with patch(
            "backend.routers.os_tasks.get_service_supabase",
            return_value=_db({"os_scheduled_tasks": [row]}),
        ):
            resp = client.patch(
                "/api/v1/os/tasks/t1",
                json={"enabled": False, "interval_days": 14, "prompt": "New weekly prompt"},
            )
        assert resp.status_code == 200
        assert resp.json()["id"] == "t1"

    def test_patch_nothing_422(self):
        client = _client()
        resp = client.patch("/api/v1/os/tasks/t1", json={})
        assert resp.status_code == 422

    def test_patch_missing_task_404(self):
        client = _client()
        with patch(
            "backend.routers.os_tasks.get_service_supabase",
            return_value=_db({"os_scheduled_tasks": []}),
        ):
            resp = client.patch("/api/v1/os/tasks/t1", json={"enabled": True})
        assert resp.status_code == 404


class TestMcpContextTool:
    def teardown_method(self):
        _teardown()

    def test_set_context_tool(self):
        client = _client()
        server = {"id": "m1", "enabled": True, "name": "crm"}
        sink: list = []
        db = _db({"tenant_mcp_servers": [server]}, sink)
        with patch("backend.routers.os_mcp.flag_enabled", return_value=True), \
             patch("backend.routers.os_mcp.get_service_supabase", return_value=db):
            resp = client.patch(
                "/api/v1/os/mcp/servers/m1/context-tool",
                json={"context_tool": "list_orders", "context_args": {"limit": 5}},
            )
        assert resp.status_code == 200
        assert resp.json()["context_tool"] == "list_orders"

    def test_clear_context_tool(self):
        client = _client()
        server = {"id": "m1", "enabled": True, "name": "crm"}
        sink: list = []
        db = _db({"tenant_mcp_servers": [server]}, sink)
        with patch("backend.routers.os_mcp.flag_enabled", return_value=True), \
             patch("backend.routers.os_mcp.get_service_supabase", return_value=db):
            resp = client.patch(
                "/api/v1/os/mcp/servers/m1/context-tool",
                json={"context_tool": None},
            )
        assert resp.status_code == 200
        assert resp.json()["context_tool"] is None
        updates = [s for s in sink if s[0] == "tenant_mcp_servers" and s[1] == "update"]
        assert updates and updates[0][2][0]["context_args"] == {}
