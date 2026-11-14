# Ragent
DevHacks 2026

This repository contains the headless simulator and the agent-side balance workflow.
The agent runs baseline and candidate experiments on matched scenario/seed pairs,
validates structured proposals, and reports objective scores, regressions, and
uncertainty. All simulator observations are produced by Python tools; model text
is never executed.

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

## Agent workflow and dashboard

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m agents.orchestrator --config configs/baseline.json --goal 'Reduce sniper defensive advantage with minimal changes' --matches 100 --iterations 2 --output results/agent_report.json
streamlit run dashboard/app.py
pytest -q
```

Without `experiments.runner`, the built-in **mock** simulator returns synthetic
data for demonstration, clearly labeled in the report and dashboard. Without
`OPENAI_API_KEY`, a deterministic mock proposer is used. Set `OPENAI_API_KEY`
and optionally `OPENAI_MODEL` to use the OpenAI proposal provider. Credentials
are read from the environment and are not logged. Provider failures are
reported; they do not silently become observed data.

Supply `--constraints constraints.json` for a real config. Numeric changes
require explicit `bounds` keyed by dotted config path; optional `allowed_paths`,
`prohibited_paths`, `target_attacker_win_rate`, and
`max_scenario_regression` constrain evaluation. Scoring weights are configurable
through the `BalanceGoal.scoring` API. The match budget includes baseline and
all candidate matches; capacity is conservatively reserved for four candidates
per iteration. Smaller budgets and a larger number of iterations reduce sample
sizes.
