import asyncio

from backend.services import prospecting


class _FakeResponse:
    def __init__(self, status_code, *, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class _FakeAsyncClient:
    def __init__(self, responses, calls, *, timeout=None, follow_redirects=None):
        assert follow_redirects is False
        self._responses = responses
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        self._calls.append(str(url))
        response = self._responses.get(str(url))
        if response is None:
            raise AssertionError(f"unexpected outbound fetch: {url}")
        return response


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _install_client(monkeypatch, responses, calls):
    monkeypatch.setattr(
        prospecting.httpx,
        "AsyncClient",
        lambda timeout=None, follow_redirects=None: _FakeAsyncClient(
            responses,
            calls,
            timeout=timeout,
            follow_redirects=follow_redirects,
        ),
    )


def test_fetch_page_text_rejects_redirect_to_private_target(monkeypatch):
    start = "https://public.example/start"
    private = "http://169.254.169.254/latest/meta-data/"
    calls = []
    responses = {
        start: _FakeResponse(302, headers={"location": private}),
    }
    _install_client(monkeypatch, responses, calls)
    monkeypatch.setattr(
        prospecting,
        "is_safe_url",
        lambda url: "169.254.169.254" not in str(url) and "localhost" not in str(url),
    )

    assert _run(prospecting._fetch_page_text(start)) == ""
    assert calls == [start]


def test_fetch_page_text_allows_safe_relative_redirect(monkeypatch):
    start = "https://public.example/start"
    target = "https://public.example/contact"
    calls = []
    responses = {
        start: _FakeResponse(302, headers={"location": "/contact"}),
        target: _FakeResponse(200, text="safe body"),
    }
    _install_client(monkeypatch, responses, calls)
    monkeypatch.setattr(prospecting, "is_safe_url", lambda url: True)

    assert _run(prospecting._fetch_page_text(start)) == "safe body"
    assert calls == [start, target]


def test_fetch_page_text_stops_after_bounded_redirect_hops(monkeypatch):
    urls = [f"https://public.example/hop-{i}" for i in range(5)]
    calls = []
    responses = {
        urls[0]: _FakeResponse(302, headers={"location": urls[1]}),
        urls[1]: _FakeResponse(302, headers={"location": urls[2]}),
        urls[2]: _FakeResponse(302, headers={"location": urls[3]}),
        urls[3]: _FakeResponse(302, headers={"location": urls[4]}),
    }
    _install_client(monkeypatch, responses, calls)
    monkeypatch.setattr(prospecting, "is_safe_url", lambda url: True)

    assert _run(prospecting._fetch_page_text(urls[0])) == ""
    assert calls == urls[:4]
