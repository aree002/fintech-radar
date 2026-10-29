"""The radar pipeline — turn a scan into an enriched, sorted result."""
from __future__ import annotations

from datetime import datetime, timezone

from .config import DEFAULT_LOOKBACK_DAYS
from .llm import LLM
from .schemas import (
    ClientProfile, Impact, LLMRadarItem, RadarItem, RadarResult, Source,
)
from .sectors import VALID_SECTORS, label_for

_IMPACT_ORDER = {Impact.high: 0, Impact.medium: 1, Impact.low: 2}


def scan(
    *,
    llm: LLM,
    sectors: list[str] | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    query: str | None = None,
    client: ClientProfile | None = None,
    max_uses: int = 6,
) -> RadarResult:
    sectors = [s for s in (sectors or []) if s in VALID_SECTORS]

    try:
        raw_items, sources = llm.scan(
            sectors=sectors, lookback_days=lookback_days, query=query,
            client=client, max_uses=max_uses,
        )
    except Exception as exc:  # surface a clean message instead of crashing the app
        raise RuntimeError(f"The scan could not be completed: {exc}") from exc

    items = _sort([_enrich(ri, idx, client) for idx, ri in enumerate(raw_items)])

    return RadarResult(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        engine=getattr(llm, "name", "unknown"),
        web_search_used=getattr(llm, "name", "") != "demo" and bool(sources),
        lookback_days=lookback_days,
        sectors=sectors,
        query=query,
        items=items,
        sources=[s for s in sources if s.url],
        stats=_stats(items),
    )


def _enrich(ri: LLMRadarItem, idx: int, client: ClientProfile | None) -> RadarItem:
    item = RadarItem(id=f"item-{idx + 1}", **ri.model_dump())
    if client and client.business_types:
        overlap = set(item.sectors) & set(client.business_types)
        if overlap:
            names = ", ".join(label_for(s) for s in overlap)
            score = 40 + 20 * len(overlap) + (20 if item.impact_level == Impact.high else 0)
            item.relevance_score = min(100, score)
            item.client_relevance = f"Relevant to this client through: {names}."
        else:
            item.relevance_score = 0
            item.client_relevance = "No direct overlap with this client's stated business."
    return item


def _sort(items: list[RadarItem]) -> list[RadarItem]:
    return sorted(
        items,
        key=lambda it: (
            -it.relevance_score,
            _IMPACT_ORDER.get(it.impact_level, 3),
            _date_sort_key(it.date),
        ),
    )


def _date_sort_key(date_str: str) -> str:
    # Newer first. Keep only digits, pad, and invert so a plain ascending sort
    # puts larger (more recent) dates earlier.
    digits = "".join(c for c in (date_str or "") if c.isdigit()).ljust(8, "0")
    return "".join(chr(255 - ord(c)) for c in digits)


def _stats(items: list[RadarItem]) -> dict[str, int]:
    return {
        "total": len(items),
        "high": sum(1 for i in items if i.impact_level == Impact.high),
        "medium": sum(1 for i in items if i.impact_level == Impact.medium),
        "low": sum(1 for i in items if i.impact_level == Impact.low),
        "client_relevant": sum(1 for i in items if i.relevance_score > 0),
    }
