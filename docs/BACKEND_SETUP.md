# Backend demo setup

Use Python 3 with `pip`, and Node.js/npm for the existing React bundle. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
npm ci
npm run build
python -m ragent_openfire.web
```

Open http://127.0.0.1:8765. The existing OpenFire profile remains the default; select the VALORANT profile in the dashboard or API to use the pinned 10 m Vandal/Spectre demo. For the profile's source, exact damage context and simulator limitations, see [CONTENT_PROFILE.md](CONTENT_PROFILE.md). Rebuild the profile and asset manifest offline with `python scripts/ingest_valorant.py`.

Gemini is enabled by default and runs when `GEMINI_API_KEY` is available to the server, either in its environment or in a local `.env` file in the server's working directory. Keep that file private and out of version control. Never put credentials in a request payload. Set `gemini_enabled` to `false` in a run request to force fallback. The server uses `gemini-3.5-flash-lite` with bounded calls; missing credentials, a timeout, malformed response, or another provider failure uses deterministic suggestions and explanations and reports fallback status. Saved completed reports can be read without credentials. Model output suggests candidates and explains results; simulation, validation and verification remain in code.

Run backend checks with `python -m pytest`. The API's profile selection, model status, run persistence and replay fields are described in [DEMO_API.md](DEMO_API.md).
