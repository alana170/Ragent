"""Generate a self-contained browser replay of a simulated match."""
import argparse
import json
from pathlib import Path
from simulator.engine import merge, simulate_match
from .scenarios import load_scenarios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/baseline.json')
    parser.add_argument('--scenarios', default='configs/scenarios.json')
    parser.add_argument('--scenario', default='baseline')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--output', default='results/replay.html')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    scenarios = load_scenarios(args.scenarios)
    scenario = next((s for s in scenarios if s['id'] == args.scenario), None)
    if scenario is None:
        parser.error('unknown scenario')
    scenario = {**scenario, 'record_frames': True}
    result = simulate_match(config, args.seed, scenario)
    data = {'match': result, 'config': merge(config, scenario.get('overrides', {}))}
    template = Path(__file__).with_name('replay_template.html').read_text(encoding='utf-8')
    html = template.replace('/* REPLAY_DATA */', json.dumps(data, allow_nan=False).replace('<', '\\u003c'))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(f'Replay saved to {out.resolve()}')


if __name__ == '__main__':
    main()
