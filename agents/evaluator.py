"""Round-weighted metrics and matched observations, with paired bootstrap intervals."""
import random
from collections import defaultdict
from statistics import mean

def _rate(row):
    metrics = row.get('metrics', {})
    if 'attacker_win_rate' in metrics:
        return float(metrics['attacker_win_rate'])
    if row.get('rounds') == 1 and row.get('winner') in ('attackers', 'defenders'):
        return float(row['winner'] == 'attackers')
    raise ValueError('multi-round result requires metrics.attacker_win_rate')

def aggregate(rows):
    total = sum(float(r['rounds']) for r in rows)
    if not total:
        return {'matches': 0, 'rounds': 0, 'attacker_win_rate': None, 'defender_win_rate': None, 'weapon_performance': {}, 'ability_performance': {}}
    rate = sum(_rate(r) * float(r['rounds']) for r in rows) / total
    def combined(key):
        values = defaultdict(lambda: defaultdict(float))
        for r in rows:
            for name, fields in r.get('metrics', {}).get(key, {}).items():
                if isinstance(fields, dict):
                    for field, value in fields.items():
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            values[name][field] += value
                elif isinstance(fields, (int, float)) and not isinstance(fields, bool):
                    values[name]['value'] += fields * float(r['rounds'])
        return {name: {field: value / total for field, value in fields.items()} for name, fields in values.items()}
    return {'matches': len(rows), 'rounds': total, 'attacker_win_rate': rate, 'defender_win_rate': 1-rate, 'balance_score': 1-2*abs(rate-.5), 'weapon_performance': combined('weapon_performance'), 'ability_performance': combined('ability_performance')}

def compare(baseline, candidate, seed=314159):
    def index(rows):
        result = {}
        for r in rows:
            key = (r['scenario_id'], r['seed'])
            if key in result: raise ValueError(f'duplicate paired observation: {key}')
            result[key] = r
        return result
    a, b = index(baseline), index(candidate)
    keys = sorted(a.keys() & b.keys())
    pairs = [(_rate(b[k]) - _rate(a[k]), float(a[k]['rounds']), float(b[k]['rounds'])) for k in keys]
    def effect(items):
        return sum((_rate(b[k])*float(b[k]['rounds'])) for k in items)/sum(float(b[k]['rounds']) for k in items) - sum((_rate(a[k])*float(a[k]['rounds'])) for k in items)/sum(float(a[k]['rounds']) for k in items)
    delta = effect(keys) if keys else None
    interval = None
    if len(keys) >= 10:
        rng = random.Random(seed)
        samples = sorted(effect([rng.choice(keys) for _ in keys]) for _ in range(2000))
        interval = [samples[50], samples[1949]]
    by_scenario = {}
    for scenario in sorted({k[0] for k in keys}):
        selected = [k for k in keys if k[0] == scenario]
        by_scenario[scenario] = {'pairs': len(selected), 'attacker_rate_delta': effect(selected)}
    return {'paired_matches': len(keys), 'unmatched_baseline': len(a)-len(keys), 'unmatched_candidate': len(b)-len(keys), 'attacker_rate_delta': delta, 'confidence_interval_95': interval, 'scenario_effects': by_scenario, 'note': 'Paired bootstrap over match/scenario observations; interval omitted below 10 pairs. No significance claim.'}
