"""Run deterministic scenario/seed matrices locally or in worker processes."""
import argparse
import csv
import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from simulator.engine import simulate_match
from .metrics import aggregate
from .scenarios import load_scenarios


def _run(job):
    config, scenario, seed = job
    try:
        return simulate_match(config, seed, scenario)
    except Exception as exc:
        raise RuntimeError(f"simulation failed for scenario={scenario.get('id')!r}, seed={seed!r}: {exc}") from exc


def run_experiments(config: dict, scenarios: list[dict], seeds: list[int], workers: int = 1) -> list[dict]:
    if workers < 1:
        raise ValueError('workers must be at least 1')
    jobs = [(config, scenario, seed) for scenario in scenarios for seed in seeds]
    if workers == 1:
        return [_run(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
        return list(pool.map(_run, jobs, chunksize=max(1, len(jobs) // (workers * 4))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--scenarios', required=True)
    parser.add_argument('--matches', type=int, default=100, help='seeds per scenario, starting at zero')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--output', required=True)
    parser.add_argument('--csv', help='optional aggregated CSV path')
    args = parser.parse_args()
    if args.matches < 1:
        parser.error('--matches must be positive')
    with open(args.config, encoding='utf-8') as source:
        config = json.load(source)
    results = run_experiments(config, load_scenarios(args.scenarios), list(range(args.matches)), args.workers)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    if args.csv:
        rows = aggregate(results)
        path = Path(args.csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', newline='', encoding='utf-8') as out:
            if rows:
                writer = csv.DictWriter(out, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    print(json.dumps(aggregate(results), indent=2))


if __name__ == '__main__':
    main()
