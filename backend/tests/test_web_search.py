import httpx

from app.tools import web_search as web_search_module
from app.tools.web_search import web_search


def test_missing_api_key_returns_error(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    result = web_search("weather in Paris")
    assert result == "Error: TAVILY_API_KEY is not configured"


def test_formats_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(
        web_search_module,
        "_call_tavily",
        lambda query, api_key: {
            "results": [
                {"title": "Paris weather", "url": "https://example.com", "content": "Sunny, 20C"}
            ]
        },
    )
    result = web_search("weather in Paris")
    assert result == "- Paris weather (https://example.com): Sunny, 20C"


def test_no_results_found(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(web_search_module, "_call_tavily", lambda query, api_key: {"results": []})
    result = web_search("an obscure query")
    assert result == "No results found for 'an obscure query'"


def test_http_error_is_caught(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    def _raise(query, api_key):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(web_search_module, "_call_tavily", _raise)
    result = web_search("weather in Paris")
    assert result.startswith("Error: Tavily search failed")
