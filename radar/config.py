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
FEED_SUMMARY_CHARS = 280     # trim each feed item's description in the prompt

# Groq (OpenAI-compatible endpoint), free tier, no credit card.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 2500       # per enrichment call
