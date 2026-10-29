"""Defaults and constants for the radar engine.

No environment reading here — the Streamlit app supplies the keys it needs and
passes the knobs. The live scan does its own web search (DuckDuckGo or Tavily)
and uses Groq to summarise and structure the results.
"""
from __future__ import annotations

DEFAULT_LOOKBACK_DAYS = 90
SEARCH_MAX_RESULTS = 10

# Groq (OpenAI-compatible endpoint), free tier, no credit card.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 4000
