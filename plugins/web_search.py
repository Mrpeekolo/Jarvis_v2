import os
from urllib.parse import urlsplit

import httpx

from core.plugins import BasePlugin, PluginMetadata, ParamSpec


class WebSearchPlugin(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web_search",
            description=(
                "Searches the public web with Brave Search and returns up to five results. "
                "The query is sent to Brave Search; use for current information or when the "
                "user explicitly asks to search online."
            ),
            version="1.0.0",
            mode="GENERAL",
            parameters=[
                ParamSpec(
                    name="query",
                    type="string",
                    description="A concise web search query",
                )
            ],
        )

    async def execute(self, query: str, **kwargs):
        query = query.strip()
        if not query:
            return {"error": "Search query must not be empty."}
        if len(query) > 512:
            return {"error": "Search query must be 512 characters or fewer."}

        api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
        if not api_key:
            return {
                "error": (
                    "Web search is not configured. Set BRAVE_SEARCH_API_KEY in the "
                    "environment, then restart JARVIS."
                )
            }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": 5, "safesearch": "moderate"},
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": api_key,
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException:
            return {"error": "Brave Search timed out. Please try again."}
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                return {"error": "Brave Search rejected the API key. Check BRAVE_SEARCH_API_KEY."}
            if exc.response.status_code == 429:
                return {"error": "Brave Search rate limit reached. Please try again later."}
            return {"error": f"Brave Search returned HTTP {exc.response.status_code}."}
        except httpx.RequestError as exc:
            return {"error": f"Could not connect to Brave Search: {exc}"}

        try:
            payload = response.json()
        except ValueError:
            return {"error": "Brave Search returned an invalid response."}
        if not isinstance(payload, dict):
            return {"error": "Brave Search returned an invalid response."}

        web_data = payload.get("web", {})
        raw_results = web_data.get("results", []) if isinstance(web_data, dict) else []
        results = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            if not isinstance(url, str):
                continue
            parsed_url = urlsplit(url)
            if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
                continue
            results.append({
                "title": str(item.get("title", "Untitled result"))[:240],
                "url": url[:2048],
                "description": str(item.get("description", ""))[:600],
            })
            if len(results) == 5:
                break

        return {
            "provider": "Brave Search",
            "query": query,
            "results": results,
            "notice": "Search query was sent to Brave Search; results are external and unverified.",
        }
