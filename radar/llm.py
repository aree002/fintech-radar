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
from .config import GROQ_BASE_URL, GROQ_MAX_TOKENS, GROQ_MODEL, SEARCH_MAX_RESULTS
from .sample_data import SAMPLE_ITEMS
from .schemas import ClientProfile, LLMRadar, LLMRadarItem, Source
from .sectors import SECTORS, label_for


class LLM(Protocol):
    name: str
    def scan(self, sectors: list[str], lookback_days: int, query: str | None,
             client: ClientProfile | None, max_uses: int) -> tuple[list[LLMRadarItem], list[Source]]: ...


# --------------------------------------------------------------------------- #
# Prompt / parsing helpers
# --------------------------------------------------------------------------- #
def _sector_label_list(sectors: list[str]) -> str:
    chosen = sectors or list(SECTORS.keys())
    return ", ".join(label_for(s) for s in chosen)


def _search_query(sectors: list[str], query: str | None) -> str:
    bits = ["latest India fintech regulatory updates", _sector_label_list(sectors),
            "RBI SEBI MeitY NPCI circular notification directions"]
    if query:
        bits.append(query)
    return " ".join(bits)


def _format_results(results: list[search.SearchResult]) -> str:
    return "\n\n".join(
        f"Title: {r.title or ''}\nURL: {r.url}\nSnippet: {r.snippet or ''}"
        for r in results
    )


def _structure_system(sectors: list[str], client: ClientProfile | None) -> str:
    sector_ids = ", ".join(SECTORS.keys())
    tailoring = ""
    if client and client.business_types:
        bt = ", ".join(label_for(s) for s in client.business_types)
        name = client.name or "the client"
        tailoring = (
            f" The reader advises {name}, whose business involves: {bt}. Where an "
            "item is relevant, make the action_items specific to them."
        )
    return (
        "You turn web search results about Indian fintech regulation into a "
        "structured list. Respond with ONLY a JSON object (no prose, no code "
        "fences) of this shape:\n"
        '{"items":[{"title":"...","regulator":"RBI|SEBI|MeitY|NPCI|IRDAI|FIU-IND|CERT-In|Other",'
        '"date":"YYYY-MM-DD","status":"notified|draft|consultation|enforcement",'
        '"sectors":["<sector id>"],"summary":"...","impact_level":"high|medium|low",'
        '"affected_entities":["..."],"action_items":["..."],'
        '"source_url":"...","source_title":"..."}]}\n'
        f"Valid sector ids: {sector_ids}. Only include real developments supported "
        "by the results; do not invent anything. Keep summaries short and plain." + tailoring
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

    def scan(self, sectors, lookback_days, query, client, max_uses):
        results = search.web_search(
            _search_query(sectors, query),
            max_results=SEARCH_MAX_RESULTS,
            tavily_key=self.tavily_key,
        )
        sources, seen = [], set()
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                sources.append(Source(url=r.url, title=r.title))
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
                    {"role": "system", "content": _structure_system(sectors, client)},
                    {"role": "user", "content": "Search results:\n\n" + _format_results(results)
                     + "\n\nReturn the JSON now."},
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_items(content), sources


# --------------------------------------------------------------------------- #
# Demo engine (sample data)
# --------------------------------------------------------------------------- #
class DemoLLM:
    name = "demo"

    def scan(self, sectors, lookback_days, query, client, max_uses):
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
