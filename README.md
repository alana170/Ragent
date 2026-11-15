# Ragent
DevHacks 2026

## Headless simulator

Run from the repository root with Python 3.9 or newer (standard library only):

```sh
python3 -m experiments.runner --config configs/baseline.json --scenarios configs/scenarios.json --matches 100 --workers 4 --output results/baseline.json --csv results/summary.csv
python3 -m unittest discover -s tests
```

`--matches` is the number of seeds per scenario; results are ordered by scenario
then seed. The command writes individual match records and optionally a
round-weighted CSV summary. The API, units, configuration and modeling
assumptions are described in [the simulator contract](docs/simulator_contract.md).

To watch a top-down replay in a browser, generate a self-contained HTML file:

```sh
python3 -m experiments.replay --scenario baseline --seed 0 --output results/replay.html
```

Open the generated file in a browser. Change `--scenario` or `--seed` to watch
another match. Playback offers pause, speed, and timeline controls.

The developer dashboard includes three recorded VALORANT example runs in
`fixtures/starter_runs`. Select one from **Saved runs** to explore its results,
replay, and report. New runs are saved separately in the local `results/` folder.

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
