"""Small reproducible traces from the same duel engine used for metrics."""
from __future__ import annotations

import hashlib
import json
from itertools import combinations

from .simulation import duel


def make_replays(baseline, proposal, recommendation, policy, seed=200000):
    """Return paired single-duel examples; this is not an aggregate result."""
    weapons = policy.get('weapons', list(baseline))
    pair = next(combinations(weapons, 2), None)
    if pair is None:
        raise ValueError('A replay requires at least two weapons')
    a, b = pair
    distance = policy.get('ranges', [5, 15, 35])[0]
    strategy = policy.get('strategies', ['aggressive'])[0]
    scenario = {'a': a, 'b': b, 'range_m': distance, 'strategy': strategy,
                'seed': seed, 'first': 'a'}
    traces = {}
    for name, config in [('baseline', baseline), ('proposal', proposal), ('recommendation', recommendation)]:
        digest = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        trace = duel(config, **scenario, include_events=True)
        traces[name] = {'config_sha256': digest, 'weapons': config, 'trace': trace}
    return {'description': 'One simulated seeded duel per configuration; not an aggregate result.',
            'scenario': scenario, 'traces': traces}
