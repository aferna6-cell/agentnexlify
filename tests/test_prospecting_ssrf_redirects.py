import asyncio
from urllib.parse import urlparse


from backend.services import prospecting
from backend.services.url_validation import PinnedTarget


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


def _make_pinned(url: str) -> PinnedTarget:
    """Return a PinnedTarget where connect_url == url (test simplification)."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    return PinnedTarget(
        url=url,
        connect_url=url,
        hostname=hostname,
        ip="1.2.3.4",
        host_header=hostname,
        sni_hostname=hostname,
    )


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
    """pin_safe_url returns None for private targets — redirect must be dropped."""
    start = "https://public.example/start"
    private = "http://169.254.169.254/latest/meta-data/"
    calls = []
    responses = {
        start: _FakeResponse(302, headers={"location": private}),
    }
    _install_client(monkeypatch, responses, calls)

    def _pin(url):
        if "169.254.169.254" in url or "localhost" in url:
            return None
        return _make_pinned(url)

    monkeypatch.setattr(prospecting, "pin_safe_url", _pin)

    assert _run(prospecting._fetch_page_text(start)) == ""
    assert calls == [start]


def test_fetch_page_text_allows_safe_relative_redirect(monkeypatch):
    """Relative redirect resolves via urljoin, then pinned — should succeed."""
    start = "https://public.example/start"
    target = "https://public.example/contact"
    calls = []
    responses = {
        start: _FakeResponse(302, headers={"location": "/contact"}),
        target: _FakeResponse(200, text="safe body"),
    }
    _install_client(monkeypatch, responses, calls)
    monkeypatch.setattr(prospecting, "pin_safe_url", _make_pinned)

    assert _run(prospecting._fetch_page_text(start)) == "safe body"
    assert calls == [start, target]


def test_fetch_page_text_stops_after_bounded_redirect_hops(monkeypatch):
    """Chain longer than _ENRICH_MAX_REDIRECTS must be aborted."""
    urls = [f"https://public.example/hop-{i}" for i in range(5)]
    calls = []
    responses = {
        urls[0]: _FakeResponse(302, headers={"location": urls[1]}),
        urls[1]: _FakeResponse(302, headers={"location": urls[2]}),
        urls[2]: _FakeResponse(302, headers={"location": urls[3]}),
        urls[3]: _FakeResponse(302, headers={"location": urls[4]}),
    }
    _install_client(monkeypatch, responses, calls)
    monkeypatch.setattr(prospecting, "pin_safe_url", _make_pinned)

    assert _run(prospecting._fetch_page_text(urls[0])) == ""
    assert calls == urls[:4]


def test_fetch_page_text_rejects_protocol_relative_location(monkeypatch):
    """Location: //evil.com/ must be rejected (not silently inherit scheme)."""
    start = "https://public.example/start"
    calls = []
    responses = {
        start: _FakeResponse(302, headers={"location": "//evil.com/payload"}),
    }
    _install_client(monkeypatch, responses, calls)
    monkeypatch.setattr(prospecting, "pin_safe_url", _make_pinned)

    result = _run(prospecting._fetch_page_text(start))
    assert result == ""
    # Must not attempt to fetch the protocol-relative URL
    assert calls == [start]


def test_fetch_page_text_ip_pinned_on_initial_url(monkeypatch):
    """Initial fetch must use pinned.connect_url, not raw hostname."""
    start = "https://public.example/page"
    pinned_url = "https://1.2.3.4/page"
    calls = []
    responses = {
        pinned_url: _FakeResponse(200, text="content"),
    }
    _install_client(monkeypatch, responses, calls)

    def _pin(url):
        parsed = urlparse(url)
        return PinnedTarget(
            url=url,
            connect_url=pinned_url,
            hostname="public.example",
            ip="1.2.3.4",
            host_header="public.example",
            sni_hostname="public.example",
        )

    monkeypatch.setattr(prospecting, "pin_safe_url", _pin)

    assert _run(prospecting._fetch_page_text(start)) == "content"
    # fetch must go to the IP-pinned URL, not the original hostname
    assert calls == [pinned_url]
