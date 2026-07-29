import httpx

from app.tools import fetch_webpage as fetch_webpage_module
from app.tools.fetch_webpage import fetch_webpage


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        pass


def test_strips_html_tags(monkeypatch):
    monkeypatch.setattr(
        fetch_webpage_module,
        "_get",
        lambda url: _FakeResponse("<html><body><h1>Hi</h1><p>World</p></body></html>"),
    )
    result = fetch_webpage("https://example.com")
    assert result == "Hi World"


def test_strips_script_and_style_content(monkeypatch):
    monkeypatch.setattr(
        fetch_webpage_module,
        "_get",
        lambda url: _FakeResponse(
            "<html><head><style>body{color:red}</style></head>"
            "<body><script>alert('x')</script><p>Hello</p></body></html>"
        ),
    )
    result = fetch_webpage("https://example.com")
    assert result == "Hello"


def test_truncates_long_content(monkeypatch):
    monkeypatch.setattr(fetch_webpage_module, "_get", lambda url: _FakeResponse("x" * 5000))
    result = fetch_webpage("https://example.com")
    assert result.endswith("...")
    assert len(result) == fetch_webpage_module._MAX_CHARS + 3


def test_http_error_is_caught(monkeypatch):
    def _raise(url):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(fetch_webpage_module, "_get", _raise)
    result = fetch_webpage("https://example.com")
    assert result.startswith("Error: could not fetch")
