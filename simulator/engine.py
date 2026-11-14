"""Fixed-step, local-RNG tactical simulation."""
import copy
import random
from . import abilities, bots, combat, maps, objectives


def merge(base, updates):
    result = copy.deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def simulate_match(config: dict, seed: int, scenario: dict) -> dict:
    cfg = merge(config, scenario.get('overrides', {}))
    dt = cfg['tick_seconds']
    if dt <= 0 or cfg['rounds'] < 1 or cfg['max_ticks'] < 1 or cfg['round_time'] <= 0:
        raise ValueError('rounds, tick_seconds, max_ticks and round_time must be positive')
    rng = random.Random(seed)
    events = []
    weapon_stats = {w: {'shots': 0, 'hits': 0, 'damage': 0.0, 'kills': 0} for w in cfg['weapons']}
    ability_stats = {a: {'uses': 0, 'healing': 0.0} for a in cfg['abilities']}
    wins = {'attackers': 0, 'defenders': 0}
    durations = []
    for round_no in range(1, cfg['rounds'] + 1):
        players = []
        selected_site = rng.randrange(len(cfg['map']['sites']))
        for team in ('attackers', 'defenders'):
            loadout = scenario.get('loadouts', {}).get(team, ['rifle', 'suppressed_rifle', 'sniper'])
            policies = scenario.get('policies', {}).get(team, ['aggressive', 'aggressive', 'flank'] if team == 'attackers' else ['hold', 'hold', 'hold'])
            for i, spawn in enumerate(cfg['map'][team[:-1] + '_spawns']):
                weapon = loadout[i]
                players.append({'id': team[0] + str(i), 'team': team, 'health': float(cfg['health']),
                                'pos': list(spawn), 'weapon': weapon, 'ammo': cfg['weapons'][weapon]['ammo'],
                                'ready': 0.0, 'ability_ready': {a: 0.0 for a in cfg['abilities']},
                                'dash_until': 0.0, 'heal_until': 0.0, 'heal_remaining': 0.0, 'policy': policies[i],
                                'site': selected_site if team == 'attackers' else i % len(cfg['map']['sites'])})
        state = {'planted': None, 'detonation': None, 'action': None, 'progress': 0.0, 'time': 0.0}
        smokes = []
        winner, reason = 'defenders', 'tick_limit'
        def event(kind, now, **data):
            events.append({'round': round_no, 'time': round(now, 6), 'type': kind, **data})
        for tick in range(cfg['max_ticks']):
            now = tick * dt
            state['time'] = now
            smokes[:] = [s for s in smokes if now < s['until']]
            for p in players:
                if p['health'] <= 0:
                    continue
                if now < p['heal_until'] and p['heal_remaining'] > 0:
                    amount = min(p['heal_remaining'], cfg['health'] - p['health'], cfg['abilities']['heal']['amount'] * dt / cfg['abilities']['heal']['duration'])
                    p['health'] += amount
                    p['heal_remaining'] -= amount
                    ability_stats['heal']['healing'] += amount
                enemies = [e for e in players if e['team'] != p['team'] and e['health'] > 0]
                target = bots.nearest_visible(p, enemies, cfg['map'], smokes)
                if p['health'] <= cfg['health'] * 0.65 and abilities.use(p, 'heal', now, cfg, ability_stats['heal'], smokes):
                    event('heal', now, player=p['id'], health=p['health'])
                if target:
                    hit = combat.fire(p, target, cfg['weapons'][p['weapon']], now, rng, weapon_stats[p['weapon']])
                    if hit is not None and hit > 0:
                        event('damage', now, player=p['id'], target=target['id'], weapon=p['weapon'], damage=hit, health=target['health'])
                        if target['health'] == 0:
                            event('death', now, player=target['id'], killer=p['id'])
                    continue
                dest = bots.destination(p, cfg, state['planted'])
                if maps.distance(p['pos'], dest) > 10 and abilities.use(p, 'dash', now, cfg, ability_stats['dash'], smokes):
                    event('dash', now, player=p['id'])
                # Attackers occasionally smoke the crossing, once they approach it.
                if p['team'] == 'attackers' and 30 < p['pos'][0] < 40 and abilities.use(p, 'smoke', now, cfg, ability_stats['smoke'], smokes, [50, 30]):
                    event('smoke', now, player=p['id'], pos=[50, 30])
                multiplier = cfg['abilities']['dash']['multiplier'] if now < p['dash_until'] else 1
                p['pos'] = maps.move(p['pos'], dest, cfg['speed'] * multiplier * dt, cfg['map'])
            if scenario.get('record_frames', False):
                event('frame', now, players=[{'id': p['id'], 'team': p['team'], 'pos': [round(v, 3) for v in p['pos']], 'health': p['health'], 'weapon': p['weapon']} for p in players], smokes=[{'pos': s['pos'], 'radius': s['radius']} for s in smokes], planted=state['planted'])
            alive_a = any(p['health'] > 0 for p in players if p['team'] == 'attackers')
            alive_d = any(p['health'] > 0 for p in players if p['team'] == 'defenders')
            if not alive_d:
                winner, reason = 'attackers', 'elimination'
                break
            if not alive_a and state['planted'] is None:
                winner, reason = 'defenders', 'elimination'
                break
            transition = objectives.update(state, players, cfg, dt)
            if transition:
                kind, actor, site = transition
                event(kind, now, player=actor, site=site)
                if kind == 'defuse':
                    winner, reason = 'defenders', 'defuse'
                    break
            if state['planted'] is not None and now >= state['detonation']:
                winner, reason = 'attackers', 'explosion'
                break
            if state['planted'] is None and now + dt >= cfg['round_time']:
                winner, reason = 'defenders', 'timeout'
                break
        duration = min((tick + 1) * dt, cfg['max_ticks'] * dt)
        wins[winner] += 1
        durations.append(duration)
        event('round_end', duration, winner=winner, reason=reason)
    return {'seed': seed, 'scenario_id': scenario['id'], 'winner': 'attackers' if wins['attackers'] > wins['defenders'] else 'defenders',
            'rounds': cfg['rounds'], 'round_duration': sum(durations) / len(durations), 'players': players, 'events': events,
            'metrics': {'attacker_win_rate': wins['attackers'] / cfg['rounds'], 'defender_win_rate': wins['defenders'] / cfg['rounds'],
                        'weapon_performance': weapon_stats, 'ability_performance': ability_stats}}
