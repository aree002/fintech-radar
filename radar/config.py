"""Defaults and constants for the radar engine.

No environment reading here — the Streamlit app supplies the keys it needs and
passes the knobs. A live scan pulls items from the RBI and SEBI RSS feeds and
uses Groq to summarise, score and tag each of them.
"""
from __future__ import annotations

# Date-window controls (the UI lets you pick a start/end window).
DEFAULT_WINDOW_DAYS = 90     # default span pre-selected in the picker
MAX_HISTORY_DAYS = 730       # the picker can reach back about two years

# How many developments to show by default (the UI lets you change it).
DEFAULT_MAX_CARDS = 15

# Feed enrichment: the LLM summarises/scores items pulled from the feeds.
ENRICH_CAP = 36              # most feed items to process per scan (newest first)
ENRICH_CHUNK = 12            # items summarised per LLM call (fewer calls = fewer rate limits)
FEED_SUMMARY_CHARS = 700     # content per item fed to the model for the summary

# RBI feeds carry each notification's full text. SEBI feeds carry only the title,
# so for SEBI we fetch the circular's PDF to get its real text (for richer
# summaries) and a comparable length (for impact). Best-effort, concurrent, bounded.
HYDRATE_MIN_WORDS = 60       # hydrate items whose feed text is shorter than this
HYDRATE_CAP = 18             # hydrate at most this many items per scan (newest first)
HYDRATE_WORKERS = 8
HYDRATE_TIMEOUT = 20
PDF_MAX_PAGES = 4            # read at most this many PDF pages
PDF_MAX_CHARS = 5000         # and at most this much text

# Groq (OpenAI-compatible endpoint), free tier, no credit card.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 2500       # per enrichment call
