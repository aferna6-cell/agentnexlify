"""Widget StaticFiles still serves the embed script and rejects traversal.

Starlette GHSA-wqp7-x3pw-xc5r is a Windows UNC issue. These checks lock the
Linux behavior that the /widget mount must keep after the 1.10 bump:
the real script is served, and parent-path payloads are not.
"""

import os

os.environ.setdefault("TESTING", "1")

from fastapi.testclient import TestClient

from backend.main import app


def test_widget_script_is_served_and_traversal_is_not():
    client = TestClient(app)
    script = client.get("/widget/agentnexlify-widget.js")
    assert script.status_code == 200
    assert "javascript" in script.headers.get("content-type", "")
    assert b"function" in script.content or b"AgentNexLiFy" in script.content

    for path in (
        "/widget/../backend/main.py",
        "/widget/%2e%2e/backend/main.py",
        "/widget/..%5C..%5Cbackend%5Cmain.py",
    ):
        response = client.get(path)
        assert response.status_code == 404
        assert b"API_SECRET_KEY" not in response.content
