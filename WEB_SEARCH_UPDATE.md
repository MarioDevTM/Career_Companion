# Web search update

## Apply to your existing project
Stop Streamlit and back up your project. Copy src/services/gemini_service.py,
src/ui/assistant_view.py, and src/config.py from this package into the matching
locations in your project. Keep your existing .env and data directory.
Install dependencies using python -m pip install -r requirements.txt, then
restart using python -m streamlit run app.py.

In AI Assistant choose Sources:
- Combine my materials + web (default): selected context plus Google Search.
- Search the web: excludes selected documents, profile, and prior conversation;
  your typed prompt is still sent.
- My materials (no web search): previous behavior, with no search tool.

Tutor/mock interview responses stream. Structured modes research with Google
Search first, then format and validate using the existing schema. This requires
two API calls. Search activity is displayed when reported by stream events.
Provider citation links and search suggestions persist with saved messages.
A source list indicates provider attribution, not verification of every claim.
Search may be skipped by Gemini; the app explicitly reports missing evidence.

Search-enabled requests allow 180 seconds. Structured formatting still uses the
existing Quick/Detailed budget. This update does not diagnose or eliminate the
previous latency issue. Search can increase latency and API usage.

The package contains source only: no API credentials, database, uploaded
personal documents, environment, or IDE files. A credential-like placeholder
comparison in config.py has been replaced with generic placeholder checks.

Validation: 26 focused tests passed with mocked Gemini calls. No live request
or complete interactive browser test was performed.
