# Fintech Regulatory Radar

The Radar tracks recent Indian fintech regulations. You pick the areas you care about, run
a scan, and it comes back with the latest developments from RBI, SEBI, MeitY, NPCI and the other
regulators, each one summarised in plain language, tagged by sub-sector, scored for impact, and
paired with a short note on what the affected businesses need to do. You can also point it at a specific client's business to see which items would matter most to them.

It is a Streamlit app, so it runs as a single Python program and deploys to Streamlit Community
Cloud in a few clicks.

## What it does

- Scans for recent regulation across digital lending, payments, wallets, UPI, account aggregators,
  P2P lending, KYC and AML, crypto, insurtech, securities, cross-border and data protection.
- Summarises each development in a few plain sentences.
- Tags the sub-sectors it touches and scores it as high, medium or low impact.
- Lists who has to act and what they should do about it.
- Can tailor the results to one client's business, so the items they care about rise to the top.
- Uses real-time web search to find current regulation when connected to a live model, and shows
  the sources it used.

## Running it

You need Python 3.10 or newer.

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Streamlit opens the app in your browser, usually at http://localhost:8501.

### Demo mode and live mode

The app has two modes, set in the sidebar.

- **Demo** uses a built-in sample set of representative developments. It needs no key and makes no
  API calls, which is handy for showing the app or trying the interface.
- **Live scan** does the web search itself (DuckDuckGo, no key needed) and then uses Groq to
  summarise and structure the results. So all you need is a free Groq key.

Keeping the search and the model separate is deliberate: This is so the live scan never runs into a
provider's search-grounding quota.

### Locking the app behind a login

A deployed app is reachable by anyone with the link, and each scan uses your keys. To keep it to
yourself, set a username and password in secrets (locally in `.streamlit/secrets.toml`, or on
Streamlit Community Cloud under the app's Secrets settings):

```
APP_USERNAME = "..."
APP_PASSWORD = "..."
```

With both set, the app asks for them before anything else. Leave them unset and the app runs open,
which is convenient while developing locally.

## A note

The Radar is a monitoring aid for a qualified lawyer. It points at things worth a closer look. It
is not legal advice, and in live mode it is only as current as what it can find on the web.
