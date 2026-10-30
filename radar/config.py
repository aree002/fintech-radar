"""Defaults and constants for the radar engine.

No environment reading here — the Streamlit app supplies the keys it needs and
passes the knobs. The live scan does its own web search (DuckDuckGo or Tavily)
and uses Groq to summarise and structure the results.
"""
from __future__ import annotations

# Date-window controls (the UI lets you pick a start/end window).
DEFAULT_WINDOW_DAYS = 30     # default span pre-selected in the picker
MAX_WINDOW_DAYS = 30         # the window can be at most this wide
MAX_HISTORY_DAYS = 730       # and can reach back about two years

# How many developments to show, and how many web results to pull.
DEFAULT_MAX_CARDS = 10
SEARCH_MAX_RESULTS = 12      # per scan, merged across the query angles below
MAX_SEARCH_QUERIES = 4       # at most this many search angles per scan

# Groq (OpenAI-compatible endpoint), free tier, no credit card.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 4000
