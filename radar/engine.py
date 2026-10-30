"""The radar pipeline — turn a scan into an enriched, filtered, sorted result."""
from __future__ import annotations

from datetime import date, datetime, timezone

from .config import DEFAULT_MAX_CARDS
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
    start_date: date,
    end_date: date,
    query: str | None = None,
    client: ClientProfile | None = None,
    max_cards: int = DEFAULT_MAX_CARDS,
    max_uses: int = 6,
) -> RadarResult:
    sectors = [s for s in (sectors or []) if s in VALID_SECTORS]

    try:
        raw_items, sources = llm.scan(
            sectors=sectors, start_date=start_date.isoformat(),
            end_date=end_date.isoformat(), query=query, client=client, max_uses=max_uses,
        )
    except Exception as exc:  # surface a clean message instead of crashing the app
        raise RuntimeError(f"The scan could not be completed: {exc}") from exc

    items = [_enrich(ri, idx, client) for idx, ri in enumerate(raw_items)]

    # Rank by client relevance, then impact (high first), then recency, and keep
    # the top max_cards. Important items lead, but routine ones still appear to
    # fill the view rather than vanishing — so it stays thorough.
    items = _sort(items)[:max_cards]

    return RadarResult(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        engine=getattr(llm, "name", "unknown"),
        web_search_used=getattr(llm, "name", "") != "demo" and bool(sources),
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
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
            -_recency(it.date),
        ),
    )


def _parse_date(date_str: str) -> date | None:
    s = (date_str or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%d %B %Y", "%d %b %Y", "%B %Y", "%b %Y", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:  # last resort: a leading YYYY-MM-DD
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _recency(date_str: str) -> int:
    """Ordinal of the item's date; 0 (oldest) when it cannot be parsed."""
    d = _parse_date(date_str)
    return d.toordinal() if d else 0


def _stats(items: list[RadarItem]) -> dict[str, int]:
    return {
        "total": len(items),
        "high": sum(1 for i in items if i.impact_level == Impact.high),
        "medium": sum(1 for i in items if i.impact_level == Impact.medium),
        "low": sum(1 for i in items if i.impact_level == Impact.low),
        "client_relevant": sum(1 for i in items if i.relevance_score > 0),
    }
