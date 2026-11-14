"""Objective transition state."""
from .maps import distance


def update(state, players, config, dt):
    sites = config['map']['sites']
    alive = [p for p in players if p['health'] > 0]
    if state['planted'] is None:
        candidates = [p for p in alive if p['team'] == 'attackers' and distance(p['pos'], sites[p['site']]) <= config['site_radius']]
        actor = min(candidates, key=lambda p: p['id']) if candidates else None
        key = ('plant', actor['id'], actor['site']) if actor else None
        threshold = config['plant_time']
    else:
        candidates = [p for p in alive if p['team'] == 'defenders' and distance(p['pos'], sites[state['planted']]) <= config['site_radius']]
        actor = min(candidates, key=lambda p: p['id']) if candidates else None
        key = ('defuse', actor['id'], state['planted']) if actor else None
        threshold = config['defuse_time']
    if key != state['action']:
        state['action'], state['progress'] = key, 0.0
    if key:
        state['progress'] += dt
        if state['progress'] + 1e-9 >= threshold:
            state['action'], state['progress'] = None, 0.0
            if key[0] == 'plant':
                state['planted'] = key[2]
                state['detonation'] = state['time'] + config['bomb_time']
            return key[0], key[1], key[2]
    return None
