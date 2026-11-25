import asyncio
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import _extract_explicit_web_query, app
from plugins.web_search import WebSearchPlugin


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "web": {
                "results": [
                    {
                        "title": "FastAPI",
                        "url": "https://fastapi.tiangolo.com/",
                        "description": "Official FastAPI documentation.",
                    },
                    {
                        "title": "Unsafe URL",
                        "url": "javascript:alert(1)",
                        "description": "Must be discarded.",
                    },
                ]
            }
        }

    def raise_for_status(self):
        pass


class FakeAsyncClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

    async def get(self, url, *, params, headers):
        assert url == "https://api.search.brave.com/res/v1/web/search"
        assert params["q"] == "FastAPI docs"
        assert params["count"] == 5
        assert headers["X-Subscription-Token"] == "test-key"
        return FakeResponse()


def test_web_search_requires_api_key():
    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": ""}):
        result = asyncio.run(WebSearchPlugin().execute("FastAPI docs"))

    assert "BRAVE_SEARCH_API_KEY" in result["error"]


def test_web_search_returns_only_http_sources():
    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key"}):
        with patch("plugins.web_search.httpx.AsyncClient", FakeAsyncClient):
            result = asyncio.run(WebSearchPlugin().execute("  FastAPI docs  "))

    assert result["provider"] == "Brave Search"
    assert result["query"] == "FastAPI docs"
    assert result["results"] == [{
        "title": "FastAPI",
        "url": "https://fastapi.tiangolo.com/",
        "description": "Official FastAPI documentation.",
    }]

def test_explicit_web_search_phrases_extract_only_search_query():
    assert _extract_explicit_web_query("Search the web for FastAPI docs") == "FastAPI docs"
    assert _extract_explicit_web_query("Look up current weather online") == "current weather"
    assert _extract_explicit_web_query("Search workspace code for TODO") is None

def test_explicit_search_routes_to_web_tool_and_reports_missing_key():
    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": ""}):
        with TestClient(app) as client:
            status = client.get("/api/status").json()
            response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "Search the web for FastAPI docs"}],
                    "mode": "GENERAL",
                },
            )

    assert status["web_search_configured"] is False
    assert response.status_code == 200
    assert '"tool": "web_search"' in response.text
    assert "BRAVE_SEARCH_API_KEY" in response.text
    assert '"type": "done"' in response.text


if __name__ == "__main__":
    test_web_search_requires_api_key()
    test_web_search_returns_only_http_sources()
    test_explicit_web_search_phrases_extract_only_search_query()
    test_explicit_search_routes_to_web_tool_and_reports_missing_key()
    print("All web search tests passed.")
