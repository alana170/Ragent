# Ragent agent workflow

This repository contains the agent-side integration for a game balance simulator. It runs baseline and candidate experiments on matched scenario/seed pairs, validates structured proposals, and reports objective scores, regressions and uncertainty. All simulator observations are produced by Python tools; model text is never executed.

## Setup and demo

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m agents.orchestrator --config configs/baseline.json --goal 'Reduce sniper defensive advantage with minimal changes' --matches 100 --iterations 2 --output results/agent_report.json
streamlit run dashboard/app.py
pytest -q
```

Without `experiments.runner`, the built-in **mock** simulator returns synthetic data for demonstration, clearly labeled in the report and dashboard. Without `OPENAI_API_KEY`, a deterministic mock proposer is used. Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` to use the OpenAI proposal provider. Credentials are read from the environment and are not logged. Provider failures are reported; they do not silently become observed data.

Supply `--constraints constraints.json` for a real config. Numeric changes require explicit `bounds` keyed by dotted config path; optional `allowed_paths`, `prohibited_paths`, `target_attacker_win_rate`, and `max_scenario_regression` constrain evaluation. Scoring weights are configurable through the `BalanceGoal.scoring` API. The match budget includes baseline and all candidate matches; capacity is conservatively reserved for four candidates per iteration. Smaller budgets and a larger number of iterations reduce sample sizes.

## Simulator integration and limitations

The adapter imports `experiments.runner.run_experiments(config, scenarios, seeds, workers=1)` if available. Results must include `seed`, `scenario_id`, `winner`, `rounds`, and `metrics.attacker_win_rate`; side rates are interpreted as per-round rates and aggregated weighted by rounds. Numeric weapon and ability performance fields are also assumed to be per-round rates. Counts or nested metrics need an explicit simulator-specific adapter. Results are paired by scenario ID and seed, with a match-level paired bootstrap interval when at least 10 pairs exist. Scenario objects currently contain `id` and descriptive labels; align these with `docs/simulator_contract.md` when Developer 1 publishes it. No simulator files are modified.

QA checks returned results for invariants and extreme rates and records seed, scenario and configuration. Descriptive scenario labels alone do not guarantee the simulator implements those conditions. Simulator calls are synchronous and do not isolate hangs; exception findings do not identify a specific seed if the batch fails. Candidate regression thresholds currently measure absolute scenario win-rate changes, not a domain-specific notion of harm. Review scenario semantics, safe bounds, scoring weights and statistical power before using results to ship a balance patch.
