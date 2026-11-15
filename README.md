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
