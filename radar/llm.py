"""The summarising / structuring layer.

The live scan gets its web results from the separate `search` step (DuckDuckGo
by default, Tavily if a key is set), then uses Groq to turn those results into a
structured list. `DemoLLM` returns the built-in sample dataset with no key.

Groq is reached over plain HTTP with `requests` (its API is OpenAI-compatible).
We deliberately avoid the OpenAI SDK: it pulls in a compiled `jiter` extension
that some locked-down Windows machines block via Application Control, which has
nothing to do with the scan itself.

Every engine returns the same thing: (list[LLMRadarItem], list[Source]).
"""
from __future__ import annotations

import json
import re
from typing import Protocol

from . import search
from .config import (
    GROQ_BASE_URL, GROQ_MAX_TOKENS, GROQ_MODEL, MAX_SEARCH_QUERIES, SEARCH_MAX_RESULTS,
)
from .sample_data import SAMPLE_ITEMS
from .schemas import ClientProfile, LLMRadar, LLMRadarItem, Source
from .sectors import SECTORS, label_for


class LLM(Protocol):
    name: str
    def scan(self, sectors: list[str], start_date: str, end_date: str, query: str | None,
             client: ClientProfile | None, max_uses: int) -> tuple[list[LLMRadarItem], list[Source]]: ...


# --------------------------------------------------------------------------- #
# Prompt / parsing helpers
# --------------------------------------------------------------------------- #
_REGULATORS = "RBI SEBI MeitY NPCI IRDAI FIU-IND CERT-In"
# The kinds of documents a real regulatory update usually is — steers search
# toward the actual notification page rather than news or marketing.
_DOC_TERMS = "circular notification master direction guidelines press release consultation paper"


def _year_hint(start_date: str, end_date: str) -> str:
    years = sorted({start_date[:4], end_date[:4]})
    return " ".join(y for y in years if y)


def _build_queries(sectors: list[str], query: str | None,
                   start_date: str, end_date: str) -> list[str]:
    """Build a few focused search angles rather than one broad query.

    With sub-sectors chosen, one targeted query per sector gives better recall
    than cramming every label into a single string. With none chosen, we ask
    broadly for the most significant recent developments.
    """
    yrs = _year_hint(start_date, end_date)
    queries: list[str] = []
    if sectors:
        for s in sectors[:MAX_SEARCH_QUERIES]:
            q = f"India {label_for(s)} regulation {_REGULATORS} {_DOC_TERMS} {yrs}"
            if query:
                q += f" {query}"
            queries.append(" ".join(q.split()))
    else:
        base = f"India fintech regulation major update {_REGULATORS} {_DOC_TERMS} {yrs}"
        if query:
            base += f" {query}"
        queries.append(" ".join(base.split()))
        # A second angle improves recall of fresh circulars/notifications.
        queries.append(" ".join(f"RBI SEBI new circular notification fintech India {yrs}".split()))
    return queries


def _format_results(results: list[search.SearchResult]) -> str:
    return "\n\n".join(
        f"[{i}] Title: {r.title or ''}\nURL: {r.url}\nSnippet: {r.snippet or ''}"
        for i, r in enumerate(results, start=1)
    )


def _structure_system(sectors: list[str], client: ClientProfile | None,
                      start_date: str, end_date: str) -> str:
    sector_ids = ", ".join(SECTORS.keys())
    tailoring = ""
    if client and client.business_types:
        bt = ", ".join(label_for(s) for s in client.business_types)
        name = client.name or "the client"
        tailoring = (
            f" The reader advises {name}, whose business involves: {bt}. Where an "
            "item is relevant, make the action_items specific to them."
        )
    focus = ""
    if not sectors:
        focus = (
            " No sub-sector was selected, so cover only the highest-impact, most "
            "consequential developments across all areas — do not pad with minor items."
        )
    return (
        "You turn web search results about Indian fintech regulation into a "
        "structured list. Respond with ONLY a JSON object (no prose, no code "
        "fences) of this shape:\n"
        '{"items":[{"title":"...","regulator":"RBI|SEBI|MeitY|NPCI|IRDAI|FIU-IND|CERT-In|Other",'
        '"date":"YYYY-MM-DD","status":"notified|draft|consultation|enforcement",'
        '"sectors":["<sector id>"],"summary":"...","impact_level":"high|medium|low",'
        '"affected_entities":["..."],"action_items":["..."],'
        '"source_url":"...","source_title":"...","source_index":<result number>}]}\n'
        f"Valid sector ids: {sector_ids}. "
        f"Only include developments whose date falls between {start_date} and {end_date}; "
        "put the real publication or notification date in 'date' (YYYY-MM-DD). "
        "Order items with the most recent and most significant first. "
        "For each item, set source_index to the [number] of the search result it is based "
        "on, and copy that result's exact URL into source_url — the specific page for the "
        "development, never a regulator's homepage." + focus +
        " Only include real developments supported by the results; do not invent anything. "
        "Keep summaries short and plain." + tailoring
    )


def _parse_items(text: str | None) -> list[LLMRadarItem]:
    if not text:
        return []
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start:end + 1]
    try:
        return LLMRadar.model_validate(json.loads(t)).items
    except Exception:
        return []


def _attach_source_links(items: list[LLMRadarItem],
                         results: list[search.SearchResult]) -> None:
    """Point each item's source at the exact result URL it cited.

    The model references a result by its [number]; we overwrite source_url/title
    with that result's real deep link so the card never points at a homepage.
    """
    for item in items:
        idx = item.source_index
        if idx and 1 <= idx <= len(results):
            r = results[idx - 1]
            item.source_url = r.url
            item.source_title = r.title or item.source_title


# --------------------------------------------------------------------------- #
# Groq (OpenAI-compatible) + search
# --------------------------------------------------------------------------- #
class GroqLLM:
    name = "groq"

    def __init__(self, api_key: str, model: str = GROQ_MODEL,
                 tavily_key: str | None = None, max_tokens: int = GROQ_MAX_TOKENS):
        self.api_key = api_key
        self.model = model
        self.tavily_key = tavily_key
        self.max_tokens = max_tokens

    def scan(self, sectors, start_date, end_date, query, client, max_uses):
        results = self._gather_results(sectors, query, start_date, end_date)
        sources = [Source(url=r.url, title=r.title) for r in results]
        if not results:
            return [], sources

        import requests

        resp = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [
                    {"role": "system",
                     "content": _structure_system(sectors, client, start_date, end_date)},
                    {"role": "user", "content": "Search results:\n\n" + _format_results(results)
                     + "\n\nReturn the JSON now."},
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        items = _parse_items(content)
        _attach_source_links(items, results)
        return items, sources

    def _gather_results(self, sectors, query, start_date, end_date):
        """Run each search angle, merge and de-duplicate by URL.

        web_search already retries and falls back from Tavily to DuckDuckGo, so
        a per-query failure is skipped; only when every angle fails do we let the
        error surface so the app can report it.
        """
        queries = _build_queries(sectors, query, start_date, end_date)
        per_query = max(4, SEARCH_MAX_RESULTS // max(1, len(queries)))
        merged: list[search.SearchResult] = []
        seen: set[str] = set()
        failures = 0
        for q in queries:
            try:
                hits = search.web_search(q, max_results=per_query, tavily_key=self.tavily_key)
            except search.SearchError:
                failures += 1
                continue
            for r in hits:
                if r.url and r.url not in seen:
                    seen.add(r.url)
                    merged.append(r)
        if not merged and failures:
            # Every angle failed — run one more so the real error propagates.
            search.web_search(queries[0], max_results=SEARCH_MAX_RESULTS,
                              tavily_key=self.tavily_key)
        return merged[:SEARCH_MAX_RESULTS]


# --------------------------------------------------------------------------- #
# Demo engine (sample data)
# --------------------------------------------------------------------------- #
class DemoLLM:
    name = "demo"

    def scan(self, sectors, start_date, end_date, query, client, max_uses):
        wanted = set(sectors) if sectors else None
        items: list[LLMRadarItem] = []
        for item in SAMPLE_ITEMS:
            if wanted and not (set(item.sectors) & wanted):
                continue
            if query and query.lower() not in (item.title + " " + item.summary).lower():
                continue
            items.append(item.model_copy(deep=True))
        return items, []


# --------------------------------------------------------------------------- #
# Model discovery (Groq model names change over time)
# --------------------------------------------------------------------------- #
# Preference order; the first one the account actually has is chosen by default.
GROQ_PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "moonshotai/kimi-k2-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "qwen/qwen3-32b",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]
# Non-chat models to hide from the picker.
_GROQ_SKIP = ("whisper", "tts", "guard", "embed", "prompt-guard")


def list_groq_models(api_key: str) -> list[str]:
    """Return the chat-capable model ids available to this Groq key."""
    import requests

    resp = requests.get(
        f"{GROQ_BASE_URL}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    resp.raise_for_status()
    ids = [m["id"] for m in resp.json().get("data", [])]
    chat = [i for i in ids if not any(s in i.lower() for s in _GROQ_SKIP)]
    return sorted(chat)


def default_groq_model(models: list[str]) -> str:
    for preferred in GROQ_PREFERRED_MODELS:
        if preferred in models:
            return preferred
    return models[0] if models else GROQ_MODEL


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def get_llm(*, provider: str = "demo", groq_key: str | None = None,
            tavily_key: str | None = None, model: str | None = None) -> LLM:
    if provider == "groq" and groq_key:
        return GroqLLM(groq_key, model or GROQ_MODEL, tavily_key)
    return DemoLLM()
