"""Fintech Regulatory Radar — Streamlit app.

Run locally:   streamlit run streamlit_app.py
Deploy:        Streamlit Community Cloud, with GROQ_API_KEY set as a secret.
"""
from __future__ import annotations

import html
import os
from datetime import date, timedelta

import streamlit as st

from radar.config import (
    DEFAULT_MAX_CARDS, DEFAULT_WINDOW_DAYS, MAX_HISTORY_DAYS, MAX_WINDOW_DAYS,
)
from radar.engine import scan
from radar.llm import default_groq_model, get_llm, list_groq_models
from radar.schemas import ClientProfile, RadarItem, RadarResult
from radar.sectors import SECTORS, label_for

st.set_page_config(page_title="Fintech Regulatory Radar", layout="wide")

# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
      .block-container { max-width: 1180px; padding-top: 2rem; }
      .app-title { font-size: 1.9rem; font-weight: 650; letter-spacing: -0.01em; margin-bottom: .1rem; }
      .app-sub { color: #56554f; font-size: 1rem; margin-bottom: .4rem; }

      .card { border: 1px solid #e4e3dd; border-radius: 12px; padding: 18px 20px;
              margin-bottom: 14px; background: #ffffff; }
      .card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
      .card-title { font-size: 1.08rem; font-weight: 650; line-height: 1.3; }
      .meta { color: #6d6b67; font-size: .82rem; margin: 6px 0 10px; }
      .summary { font-size: .95rem; color: #2b2a27; line-height: 1.55; }
      .label { font-size: .72rem; font-weight: 650; text-transform: uppercase;
               letter-spacing: .05em; color: #86857d; margin: 12px 0 4px; }
      .entities { color: #56554f; font-size: .9rem; }
      .actions { margin: 4px 0 0 0; padding-left: 20px; }
      .actions li { font-size: .92rem; color: #2b2a27; margin-bottom: 3px; }
      .relevance { margin-top: 12px; padding: 8px 12px; border-radius: 8px;
                   background: #eaf0f7; color: #1f3a5f; font-size: .9rem; }
      .relevance.none { background: #f4f4f2; color: #6d6b67; }

      .badge { display: inline-block; font-size: .72rem; font-weight: 650;
               padding: 2px 9px; border-radius: 999px; white-space: nowrap; }
      .b-high { color: #b23b3b; background: #fbeaea; }
      .b-medium { color: #9a6a12; background: #faf1dd; }
      .b-low { color: #4f7a2e; background: #eef5e6; }
      .chip { display: inline-block; font-size: .74rem; padding: 2px 9px; margin: 2px 4px 2px 0;
              border-radius: 999px; background: #f2f2ef; border: 1px solid #e4e3dd; color: #56554f; }
      .reg { font-weight: 650; color: #1f3a5f; }
      .status { text-transform: capitalize; }
      a.src { color: #1f3a5f; font-size: .85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _secret(name: str) -> str | None:
    try:
        val = st.secrets.get(name, None)  # type: ignore[attr-defined]
    except Exception:
        val = None
    return val or os.getenv(name)


def groq_key() -> str | None:
    return _secret("GROQ_API_KEY")


def tavily_key() -> str | None:
    return _secret("TAVILY_API_KEY")


def e(s: str) -> str:
    return html.escape(str(s or ""))


def badge(impact: str) -> str:
    cls = {"high": "b-high", "medium": "b-medium", "low": "b-low"}.get(impact, "b-low")
    return f'<span class="badge {cls}">{e(impact)} impact</span>'


def render_card(item: RadarItem) -> str:
    chips = "".join(f'<span class="chip">{e(label_for(s))}</span>' for s in item.sectors)
    actions = "".join(f"<li>{e(a)}</li>" for a in item.action_items)
    entities = ", ".join(e(x) for x in item.affected_entities)
    src = ""
    if item.source_url:
        title = e(item.source_title or item.source_url)
        src = f'<div class="label">Source</div><a class="src" href="{e(item.source_url)}" target="_blank" rel="noopener">{title}</a>'
    relevance = ""
    if item.client_relevance:
        cls = "relevance" if item.relevance_score > 0 else "relevance none"
        relevance = f'<div class="{cls}">{e(item.client_relevance)}</div>'
    return f"""
    <div class="card">
      <div class="card-top">
        <div class="card-title">{e(item.title)}</div>
        <div>{badge(item.impact_level.value)}</div>
      </div>
      <div class="meta">
        <span class="reg">{e(item.regulator.value)}</span> &middot;
        {e(item.date)} &middot;
        <span class="status">{e(item.status.value)}</span>
      </div>
      <div>{chips}</div>
      <div class="label">Summary</div>
      <div class="summary">{e(item.summary)}</div>
      <div class="label">Who must act</div>
      <div class="entities">{entities}</div>
      <div class="label">What to do</div>
      <ul class="actions">{actions}</ul>
      {relevance}
      {src}
    </div>
    """


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown('<div class="app-title">Fintech Regulatory Radar</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-sub">Recent Indian fintech regulatory developments, summarised, '
    "tagged by sub-sector, scored for impact, with a short note on what to do. "
    "Optionally tailored to a client's business.</div>",
    unsafe_allow_html=True,
)

grq_key = groq_key()
tav_key = tavily_key()

# --------------------------------------------------------------------------- #
# Sidebar controls
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Scan settings")

    mode_options: list[tuple[str, str]] = []
    if grq_key:
        mode_options.append(("Live scan", "groq"))
    mode_options.append(("Demo (sample data)", "demo"))

    labels = [m[0] for m in mode_options]
    choice = st.radio(
        "Mode", labels, index=0,
        help="Live scan searches the web and uses Groq to summarise the results. "
             "Demo uses a built-in sample set.",
    )
    provider = dict(mode_options)[choice]
    if provider == "demo" and not grq_key:
        st.caption("Add a Groq key (in secrets) to enable a live scan.")

    chosen_model = None
    if provider == "groq":
        st.caption("Search: Tavily" if tav_key else "Search: DuckDuckGo (no key needed)")
        # Load the models this key actually has, so a retired default can't break it.
        if "groq_models" not in st.session_state:
            try:
                st.session_state["groq_models"] = list_groq_models(grq_key)
            except Exception:
                st.session_state["groq_models"] = []
        models = st.session_state["groq_models"]
        if models:
            default = default_groq_model(models)
            chosen_model = st.selectbox("Model", models, index=models.index(default))
        else:
            chosen_model = st.text_input("Model", value="llama-3.1-8b-instant",
                                         help="Could not list models; type one from console.groq.com.")

    sector_ids = list(SECTORS.keys())
    chosen_sectors = st.multiselect(
        "Sub-sectors", options=sector_ids, default=[],
        format_func=label_for,
        help="Leave empty to cover all areas.",
    )

    _today = date.today()
    _min_day = _today - timedelta(days=MAX_HISTORY_DAYS)
    window = st.date_input(
        "Date window",
        value=(_today - timedelta(days=DEFAULT_WINDOW_DAYS), _today),
        min_value=_min_day, max_value=_today, format="YYYY-MM-DD",
        help=f"Pick a start and end date, at most {MAX_WINDOW_DAYS} days apart, "
             "within the last two years.",
    )

    max_cards = st.number_input(
        "Max cards to show", min_value=5, max_value=20,
        value=DEFAULT_MAX_CARDS, step=1,
        help="When a scan finds more developments than this, the most recent and "
             "relevant ones are kept.",
    )

    keyword = st.text_input("Keyword filter (optional)", placeholder="e.g. KFS, escrow, DLG")

    st.divider()
    st.caption("Tailor to a client (optional)")
    client_name = st.text_input("Client name", placeholder="e.g. a digital lending startup")
    client_sectors = st.multiselect("Client's business", options=sector_ids,
                                    default=[], format_func=label_for,
                                    key="client_sectors")

    run = st.button("Run scan", type="primary", use_container_width=True)

# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #
if run:
    # Resolve the date window (date_input gives one date mid-selection, a pair once complete).
    if isinstance(window, (list, tuple)):
        start_date = window[0]
        end_date = window[1] if len(window) > 1 else window[0]
    else:
        start_date = end_date = window

    error = None
    if start_date > end_date:
        error = "The start date must be on or before the end date."
    elif (end_date - start_date).days > MAX_WINDOW_DAYS:
        error = f"Please choose a window of at most {MAX_WINDOW_DAYS} days."

    if error:
        st.error(error)
    else:
        client = ClientProfile(name=client_name or None, business_types=client_sectors) if client_sectors else None
        llm = get_llm(provider=provider, groq_key=grq_key, tavily_key=tav_key, model=chosen_model)
        spinner_msg = "Building the radar from the sample set..." if provider == "demo" \
            else "Searching for current regulation and building the radar..."
        try:
            with st.spinner(spinner_msg):
                result: RadarResult = scan(
                    llm=llm,
                    sectors=chosen_sectors,
                    start_date=start_date,
                    end_date=end_date,
                    query=keyword or None,
                    client=client,
                    max_cards=int(max_cards),
                )
            st.session_state["result"] = result
        except RuntimeError as exc:
            st.error(str(exc))

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
result: RadarResult | None = st.session_state.get("result")

if not result:
    st.info("Set your options in the sidebar and run a scan to see the radar.")
    st.stop()

engine_note = "sample data" if result.engine == "demo" else f"model: {result.engine}"
search_note = " · web search used" if result.web_search_used else ""
window_note = "full sample set" if result.engine == "demo" \
    else f"{result.start_date} to {result.end_date}"
st.caption(f"Generated {result.generated_at} · {engine_note}{search_note} · {window_note}")
if not result.sectors:
    st.caption("No sub-sector selected — showing the highest-impact updates across all areas.")

s = result.stats
cols = st.columns(5)
cols[0].metric("Developments", s.get("total", 0))
cols[1].metric("High impact", s.get("high", 0))
cols[2].metric("Medium", s.get("medium", 0))
cols[3].metric("Low", s.get("low", 0))
cols[4].metric("Client-relevant", s.get("client_relevant", 0))

st.write("")
flt = st.radio("Filter by impact", ["All", "High", "Medium", "Low"],
               horizontal=True, label_visibility="collapsed")

items = result.items
if flt != "All":
    items = [i for i in items if i.impact_level.value == flt.lower()]

if not items:
    st.info("No developments match this filter.")
else:
    for item in items:
        st.markdown(render_card(item), unsafe_allow_html=True)

if result.sources:
    with st.expander(f"Sources ({len(result.sources)})"):
        for src in result.sources:
            st.markdown(f"- [{e(src.title or src.url)}]({src.url})")

st.caption("This is a monitoring aid for a qualified lawyer. It is not legal advice.")
