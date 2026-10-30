"""The summarising / scoring layer.

A live scan pulls dated items from the RBI and SEBI RSS feeds (see `feeds.py`),
then uses Groq to summarise, score the impact of, and tag each one. The feed
supplies the authoritative title, date, regulator and link; the model only adds
judgement. `DemoLLM` returns the built-in sample dataset with no key.

Groq is reached over plain HTTP with `requests` (its API is OpenAI-compatible);
we avoid the OpenAI SDK because it pulls in a compiled extension that some
locked-down Windows machines block.

Every engine returns the same thing: (list[LLMRadarItem], list[Source]).
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Protocol

from .config import (
    ENRICH_CAP, ENRICH_CHUNK, FEED_SUMMARY_CHARS, GROQ_BASE_URL,
    GROQ_MAX_TOKENS, GROQ_MODEL,
)
from .sample_data import SAMPLE_ITEMS
from .schemas import ClientProfile, Impact, LLMRadarItem, Source, Status
from .sectors import SECTORS, VALID_SECTORS, label_for


class LLM(Protocol):
    name: str
    def scan(self, sectors: list[str], start_date: str, end_date: str, query: str | None,
             client: ClientProfile | None, max_uses: int) -> tuple[list[LLMRadarItem], list[Source]]: ...


# --------------------------------------------------------------------------- #
# Enrichment prompt / parsing
# --------------------------------------------------------------------------- #
_VALID_STATUS = {s.value for s in Status}
_VALID_IMPACT = {i.value for i in Impact}


def _enrich_system(client: ClientProfile | None) -> str:
    sector_ids = ", ".join(SECTORS.keys())
    tailoring = ""
    if client and client.business_types:
        bt = ", ".join(label_for(s) for s in client.business_types)
        name = client.name or "the client"
        tailoring = (
            f" The reader advises {name}, whose business involves: {bt}. Where an "
            "item is relevant to them, make the action_items specific to them."
        )
    return (
        "You are a legal analyst summarising Indian financial-regulation items "
        "(from RBI or SEBI) for a lawyer. For EACH numbered item, return a concise "
        "structured entry. Respond with ONLY a JSON object (no prose, no code "
        "fences) of this shape:\n"
        '{"items":[{"index":<number>,"summary":"2-3 plain sentences on what it is '
        'and what changed","impact_level":"high|medium|low",'
        '"status":"notified|draft|consultation|enforcement",'
        '"sectors":["<id>"],"affected_entities":["..."],"action_items":["..."]}]}\n'
        f"Valid sector ids: {sector_ids}. Pick the ids that fit each item (one or more).\n"
        "Score impact_level using these signals, in order of importance:\n"
        "1. The single most important items are the RELEASE OF A NEW guideline, regulation, "
        "master direction, framework, scheme or set of directions — score these high. An "
        "amendment, review, corrigendum, extension of a timeline, or a narrow change to an "
        "existing rule is less important — usually medium.\n"
        "2. Longer, more detailed releases tend to be more significant; very short notices "
        "(about half a page, a low word count) are usually routine — lean lower for those.\n"
        "3. Routine or administrative items are low: securities/treasury auctions, "
        "sanctions-list or UAPA updates, district reorganisation, and individual "
        "enforcement / adjudication / recovery actions against named parties.\n"
        "Base each summary only on the title and description provided; do not invent "
        "specifics. Return one entry per item, keyed by its index." + tailoring
    )


def _format_feed_items(items: list) -> str:
    lines = []
    for i, f in enumerate(items):
        desc = (f.summary or "")[:FEED_SUMMARY_CHARS]
        lines.append(f"[{i}] Regulator: {f.regulator} | Type: {f.source_type} | "
                     f"Length: ~{f.word_count} words\n"
                     f"Title: {f.title}\nDescription: {desc}")
    return "\n\n".join(lines)


def _parse_enrichment(text: str | None) -> dict[int, dict]:
    if not text:
        return {}
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start:end + 1]
    try:
        data = json.loads(t)
    except Exception:
        return {}
    out: dict[int, dict] = {}
    for entry in data.get("items", []):
        if isinstance(entry, dict) and isinstance(entry.get("index"), int):
            out[entry["index"]] = entry
    return out


def _as_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        return date.today()


def _is_auth_error(exc: Exception) -> bool:
    """True for a 401/403 (bad or missing key) — worth telling the user about."""
    resp = getattr(exc, "response", None)
    return getattr(resp, "status_code", None) in (401, 403)


# Impact heuristics from practising lawyers: a brand-new guideline/regulation is
# the most important; amendments and routine/administrative notices much less so;
# longer documents tend to matter more. Encoded as rules so scoring is consistent.
_LOW_TITLE = re.compile(
    r"\b(auction|treasury bill|t-bill|sanctions?\s+list|UAPA|UNSC|premature redemption|"
    r"sovereign gold bond|\bSGB\b|money market operation|liquidity adjustment|"
    r"reference rate|reorganisation of districts|re-organisation of districts|"
    r"forex reserves|ways and means)\b", re.I)
_NEW_TITLE = re.compile(
    r"\b(master direction|guidelines?|framework|scheme|directions?|regulations?)\b", re.I)
_AMEND_TITLE = re.compile(
    r"\b(amendment|review|corrigendum|extension|modif\w*|rationalis\w*)\b", re.I)


def _score_impact(feed_item, llm_impact: str) -> str:
    """Final impact: domain rules first, the model's view where rules are silent."""
    title = feed_item.title or ""
    # Individual enforcement against named parties is not a regulatory change.
    if feed_item.source_type in ("order", "recovery"):
        return "low"
    if _LOW_TITLE.search(title):
        return "low"
    is_amend = bool(_AMEND_TITLE.search(title))
    if _NEW_TITLE.search(title) and not is_amend:
        base = "high"                      # release of a new guideline / regulation
    elif is_amend:
        base = "medium"                    # amendments matter less than new rules
    else:
        base = llm_impact if llm_impact in _VALID_IMPACT else "medium"
    # Length as a secondary signal: a long, detailed release is likely significant.
    if base == "medium" and (feed_item.word_count or 0) >= 1500:
        base = "high"
    return base


def _merge(feed_item, enrich: dict | None) -> LLMRadarItem:
    """Combine the feed's authoritative fields with the model's judgement."""
    enrich = enrich or {}
    status = enrich.get("status")
    if status not in _VALID_STATUS:
        status = "enforcement" if feed_item.source_type == "order" else "notified"
    impact = enrich.get("impact_level")
    if impact not in _VALID_IMPACT:
        impact = "medium"
    impact = _score_impact(feed_item, impact)
    sectors = [s for s in (enrich.get("sectors") or []) if s in VALID_SECTORS]
    summary = (enrich.get("summary") or "").strip() or feed_item.summary or feed_item.title
    actions = [str(a) for a in (enrich.get("action_items") or []) if str(a).strip()]
    entities = [str(a) for a in (enrich.get("affected_entities") or []) if str(a).strip()]
    item_date = feed_item.published.isoformat() if feed_item.published else (feed_item.date_str or "")
    return LLMRadarItem(
        title=feed_item.title,
        regulator=feed_item.regulator,
        date=item_date,
        status=status,
        sectors=sectors,
        summary=summary,
        impact_level=impact,
        affected_entities=entities,
        action_items=actions,
        source_url=feed_item.url,
        source_title=feed_item.title,
    )


# --------------------------------------------------------------------------- #
# Groq (OpenAI-compatible) over the RBI / SEBI feeds
# --------------------------------------------------------------------------- #
class GroqLLM:
    name = "groq"

    def __init__(self, api_key: str, model: str = GROQ_MODEL, max_tokens: int = GROQ_MAX_TOKENS):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def scan(self, sectors, start_date, end_date, query, client, max_uses):
        from . import feeds

        sd, ed = _as_date(start_date), _as_date(end_date)
        items = []
        for f in feeds.fetch_feeds():
            if f.published is not None and not (sd <= f.published <= ed):
                continue
            if query and query.lower() not in (f.title + " " + f.summary).lower():
                continue
            items.append(f)
        items.sort(key=lambda f: (f.published or date.min), reverse=True)
        items = items[:ENRICH_CAP]

        sources = [Source(url=f.url, title=f.title) for f in items]
        if not items:
            return [], sources

        feeds.hydrate(items)  # measure a fair document length for short-text items
        enriched = self._enrich(items, client)
        if sectors:
            want = set(sectors)
            enriched = [it for it in enriched if set(it.sectors) & want]
        return enriched, sources

    def _enrich(self, feed_items, client):
        import time

        system = _enrich_system(client)
        out: list[LLMRadarItem] = []
        chunks = [feed_items[i:i + ENRICH_CHUNK] for i in range(0, len(feed_items), ENRICH_CHUNK)]
        for n, chunk in enumerate(chunks):
            try:
                enriched = self._enrich_chunk(chunk, system)
            except Exception as exc:
                # A bad or missing key should be reported; a rate limit or hiccup
                # should not sink the scan — fall back to the feed's own text.
                if _is_auth_error(exc):
                    raise
                enriched = {}
            for j, f in enumerate(chunk):
                out.append(_merge(f, enriched.get(j)))
            if n < len(chunks) - 1:
                time.sleep(0.6)  # ease the free-tier request rate
        return out

    def _enrich_chunk(self, chunk, system) -> dict[int, dict]:
        import time

        import requests

        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": "Items:\n\n" + _format_feed_items(chunk)
                 + "\n\nReturn the JSON now."},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        resp = None
        for attempt in range(3):
            resp = requests.post(f"{GROQ_BASE_URL}/chat/completions",
                                 headers=headers, json=body, timeout=60)
            if resp.status_code == 429 and attempt < 2:
                wait = resp.headers.get("retry-after")
                time.sleep(min(float(wait), 12) if wait else 2.0 * (attempt + 1))
                continue
            break
        resp.raise_for_status()
        return _parse_enrichment(resp.json()["choices"][0]["message"]["content"])


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
            model: str | None = None) -> LLM:
    if provider == "groq" and groq_key:
        return GroqLLM(groq_key, model or GROQ_MODEL)
    return DemoLLM()
