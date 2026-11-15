# Ragent
DevHacks 2026

## Developer dashboard

Build and run the local React dashboard from the repository root:

```sh
npm install
npm run build
python3 -m ragent_openfire.web
```

Open `http://127.0.0.1:8765`. The Saved runs menu includes a bundled
`Demo · Spectre damage tuning` report alongside runs saved locally.
The Developer Lab keeps seed count under collapsed Advanced settings; it
defaults to 24 seeds per scenario and tests both starting-player orders.

## Deploy a free demo on Render

1. Push this branch to GitHub, then create a [Render Blueprint](https://dashboard.render.com/blueprints) and connect the repository and branch. Render reads `render.yaml` and builds the Docker image.
2. Deploy the service and open its `onrender.com` URL. The image builds the React frontend and runs the Python server with Render's assigned `PORT`.
3. Optionally set `GEMINI_API_KEY` in the service's Environment settings. Without it, the agent uses deterministic fallback; a public service lets visitors consume any configured Gemini quota.

The free service sleeps after inactivity. Its filesystem is temporary, so new runs and reports can disappear on restart or redeploy; bundled examples remain available. Runs are shared by visitors, and only one simulation can run at a time. Use a paid service with persistent storage for durable results.
