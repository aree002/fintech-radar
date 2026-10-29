"""Web search step, decoupled from the language model.

Default provider is DuckDuckGo, which needs no API key. Tavily is used instead
when a Tavily key is supplied (more reliable, built for LLM use, free tier).
Keeping search separate from the model means we never touch a provider's
grounding quota, which is what blocked the Gemini live scan.
"""
from __future__ import annotations

import time

from pydantic import BaseModel

# Transient network failures (dropped connection, timeout) are retried a few
# times before giving up; a single reset shouldn't fail a whole scan.
_RETRIES = 3
_RETRY_WAIT = 1.5


class SearchResult(BaseModel):
    title: str | None = None
    url: str
    snippet: str | None = None


class SearchError(Exception):
    pass


def _tavily(query: str, max_results: int, api_key: str) -> list[SearchResult]:
    import requests

    resp = requests.post(
        "https://api.tavily.com/search",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "api_key": api_key,            # sent in the body too, for compatibility
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    out: list[SearchResult] = []
    for item in data.get("results", []):
        url = item.get("url")
        if url:
            out.append(SearchResult(url=url, title=item.get("title"),
                                    snippet=item.get("content")))
    return out


def _duckduckgo(query: str, max_results: int) -> list[SearchResult]:
    try:
        from ddgs import DDGS  # current package name
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # older package name
        except ImportError as exc:
            raise SearchError(
                "DuckDuckGo search needs the 'ddgs' package (pip install ddgs)."
            ) from exc
    out: list[SearchResult] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            url = item.get("href") or item.get("url")
            if url:
                out.append(SearchResult(
                    url=url,
                    title=item.get("title"),
                    snippet=item.get("body") or item.get("snippet"),
                ))
    return out


def _with_retries(fn, *args) -> list[SearchResult]:
    """Run a search function, retrying on transient connection errors."""
    last_exc: Exception | None = None
    for attempt in range(_RETRIES):
        try:
            return fn(*args)
        except Exception as exc:  # network blips: reset, timeout, refused
            last_exc = exc
            if attempt < _RETRIES - 1:
                time.sleep(_RETRY_WAIT * (attempt + 1))
    raise last_exc if last_exc else SearchError("Web search failed")


def web_search(query: str, max_results: int = 10,
               tavily_key: str | None = None) -> list[SearchResult]:
    """Return search results, using Tavily if a key is given, else DuckDuckGo.

    Each provider is retried on transient connection errors. If Tavily cannot be
    reached at all, we fall back to DuckDuckGo so the scan can still complete.
    """
    try:
        if tavily_key:
            try:
                return _with_retries(_tavily, query, max_results, tavily_key)
            except Exception:
                # Tavily unreachable after retries — fall back to keyless search.
                return _with_retries(_duckduckgo, query, max_results)
        return _with_retries(_duckduckgo, query, max_results)
    except SearchError:
        raise
    except Exception as exc:
        raise SearchError(f"Web search failed: {exc}") from exc
