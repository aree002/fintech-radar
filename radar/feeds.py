"""Authoritative regulatory feeds: RBI and SEBI RSS.

We pull directly from the regulators' own RSS feeds, so every item is real,
dated, and linked to its exact page. The language model then summarises and
scores these known items, instead of trying to *discover* regulation from
general web search (which was unreliable and sometimes cited junk sources).

RSS exposes only the most recent items (RBI ~10 per feed, SEBI ~30), so this
covers current regulation well but does not reach deep into history.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime

from pydantic import BaseModel

_UA = {"User-Agent": "Mozilla/5.0 (compatible; FintechRegulatoryRadar/1.0)"}
_TIMEOUT = 30

# (regulator, default item type or None, feed url).
# SEBI's single feed carries several item types, derived per-item from the URL.
FEEDS: list[tuple[str, str | None, str]] = [
    ("RBI", "notification", "https://rbi.org.in/notifications_rss.xml"),
    ("RBI", "press release", "https://rbi.org.in/pressreleases_rss.xml"),
    ("SEBI", None, "https://www.sebi.gov.in/sebirss.xml"),
]

# SEBI item types skipped by default: case-by-case recovery actions against
# named parties are noise for a regulatory radar.
_SEBI_SKIP = {"recovery"}


class FeedItem(BaseModel):
    regulator: str
    source_type: str
    title: str
    url: str
    summary: str = ""
    published: date | None = None
    date_str: str = ""


def _clean(text: str | None) -> str:
    t = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", t).strip()


def _parse_date(s: str | None) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).date()
    except Exception:
        pass
    for fmt in ("%d %b, %Y %z", "%d %b %Y %z", "%d %b, %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _sebi_type(url: str) -> str:
    u = url.lower()
    if "/legal/circulars/" in u:
        return "circular"
    if "press-releases" in u:
        return "press release"
    if "/enforcement/orders/" in u:
        return "order"
    if "recovery-proceedings" in u:
        return "recovery"
    if "/legal/" in u:
        return "regulation"
    return "update"


def fetch_feeds(regulators: list[str] | None = None) -> list[FeedItem]:
    """Fetch and parse the RBI/SEBI feeds into a flat, de-duplicated list."""
    import requests

    wanted = {r.upper() for r in regulators} if regulators else None
    out: list[FeedItem] = []
    seen: set[str] = set()
    for reg, default_type, url in FEEDS:
        if wanted and reg.upper() not in wanted:
            continue
        try:
            resp = requests.get(url, headers=_UA, timeout=_TIMEOUT)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception:
            continue  # a single feed being down should not sink the whole scan
        for node in root.findall(".//item"):
            link = (node.findtext("link") or "").strip()
            if not link or link in seen:
                continue
            stype = default_type or _sebi_type(link)
            if stype in _SEBI_SKIP:
                continue
            seen.add(link)
            out.append(FeedItem(
                regulator=reg,
                source_type=stype,
                title=_clean(node.findtext("title")) or link,
                url=link,
                summary=_clean(node.findtext("description")),
                published=_parse_date(node.findtext("pubDate")),
                date_str=(node.findtext("pubDate") or "").strip(),
            ))
    return out
