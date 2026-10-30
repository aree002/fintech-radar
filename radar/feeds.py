"""Authoritative regulatory feeds: RBI and SEBI RSS.

We pull directly from the regulators' own RSS feeds, so every item is real,
dated, and linked to its exact page. The language model then summarises and
scores these known items, instead of trying to *discover* regulation from
general web search (which was unreliable and sometimes cited junk sources).

RSS exposes only the most recent items (RBI ~10 per feed, SEBI ~30), so this
covers current regulation well but does not reach deep into history.
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime

from pydantic import BaseModel

from .config import (
    HYDRATE_CAP, HYDRATE_MIN_WORDS, HYDRATE_TIMEOUT, HYDRATE_WORKERS,
    PDF_MAX_CHARS, PDF_MAX_PAGES,
)

_UA = {"User-Agent": "Mozilla/5.0 (compatible; FinancialRegulatoryRadar/1.0)"}
_TIMEOUT = 30

# pypdf is noisy about malformed PDFs we already handle; keep the logs quiet.
logging.getLogger("pypdf").setLevel(logging.ERROR)

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
    summary: str = ""            # short abstract from the feed (display fallback)
    content: str = ""            # full text used for the summary + length signal
    word_count: int = 0          # length of the document — a signal of importance
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
            desc = _clean(node.findtext("description"))
            out.append(FeedItem(
                regulator=reg,
                source_type=stype,
                title=_clean(node.findtext("title")) or link,
                url=link,
                summary=desc,
                content=desc,
                word_count=len(desc.split()),
                published=_parse_date(node.findtext("pubDate")),
                date_str=(node.findtext("pubDate") or "").strip(),
            ))
    return out


def _pdf_text(url: str) -> str:
    """Download a PDF and return its text (first few pages, bounded)."""
    import io

    import pypdf
    import requests

    resp = requests.get(url, headers=_UA, timeout=HYDRATE_TIMEOUT)
    resp.raise_for_status()
    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    parts, total = [], 0
    for page in reader.pages[:PDF_MAX_PAGES]:
        text = page.extract_text() or ""
        parts.append(text)
        total += len(text)
        if total >= PDF_MAX_CHARS:
            break
    return re.sub(r"\s+", " ", " ".join(parts)).strip()[:PDF_MAX_CHARS]


def _doc_content(page_url: str) -> str | None:
    """Fetch an item's page, find its attached PDF, and return the PDF's text.

    This is how SEBI (and RBI, when needed) expose the real document body — the
    HTML page itself is just a shell. Best-effort; returns None on any failure.
    """
    import requests

    try:
        resp = requests.get(page_url, headers=_UA, timeout=HYDRATE_TIMEOUT)
        resp.raise_for_status()
        # Prefer the actual document store (SEBI attachments / RBI docs) over any
        # other PDF on the page (accessibility statements, logos, etc.).
        m = (re.search(r'https?://[^"\'\s<>]+/(?:sebi_data/attachdocs|rdocs|content)/[^"\'\s<>]+\.pdf',
                       resp.text, re.I)
             or re.search(r'https?://[^"\'\s<>]+\.pdf', resp.text, re.I))
        if not m:
            return None
        return _pdf_text(m.group(0))
    except Exception:
        return None


def hydrate(items: list[FeedItem]) -> None:
    """Pull the real document text for items whose feed text is short (e.g. SEBI).

    Fetches the attached PDF, concurrently and best-effort: an item that fails to
    load keeps its feed text. Updates content and word_count in place. Limited to
    the newest HYDRATE_CAP short items so a scan stays reasonably fast.
    """
    from concurrent.futures import ThreadPoolExecutor

    short = [it for it in items if it.word_count < HYDRATE_MIN_WORDS][:HYDRATE_CAP]
    if not short:
        return
    with ThreadPoolExecutor(max_workers=HYDRATE_WORKERS) as pool:
        texts = pool.map(_doc_content, [it.url for it in short])
    for it, text in zip(short, texts):
        if text:
            it.content = text
            it.word_count = len(text.split())
