"""Fast, seeded weapon-stat duel approximation for RAGENT exploration.

This is intentionally NOT OpenFire's 3D physics, bot AI, or live netcode. It
models aim, reaction, shooting cadence, reload, movement and range; Godot headless
checks are a separate verification layer. Never present simulated retention data.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
from statistics import mean, median
import math
import random

STRATEGY = {
    'aggressive': {'reaction': 0.23, 'aim': 0.90, 'movement': 1.0, 'close_per_sec': 1.8},
    'defensive':  {'reaction': 0.30, 'aim': 1.10, 'movement': 0.65, 'close_per_sec': -0.6},
    'flanker':    {'reaction': 0.27, 'aim': 0.94, 'movement': 1.20, 'close_per_sec': 0.4},
}


def validate_weapons(weapons):
    if not isinstance(weapons, dict) or not weapons: raise ValueError('No weapons')
    for wid, w in weapons.items():
        for field in ('damage', 'fire_rate', 'mag_size', 'pellets', 'range', 'spread_deg'):
            if not isinstance(w.get(field), (float, int)) or w[field] <= 0:
                raise ValueError(f'{wid}.{field} must be positive')
        if w.get('reload_time', 1) < 0: raise ValueError(f'{wid}: negative reload')


def _hit_chance(w, distance, strat):
    # Toy accuracy model. Spread grows with range, exposure and lateral motion.
    aim = float(w.get('aim_spread_deg', w['spread_deg']))
    angle = math.radians(aim if strat == 'defensive' else (aim + w['spread_deg']) / 2)
    spread_radius = max(0, distance) * math.tan(angle)
    p = 0.92 * STRATEGY[strat]['aim'] * math.exp(-0.52 * (spread_radius / .85)**1.4)
    return max(0.04, min(0.96, p))


def duel(weapons, a, b, range_m, strategy, seed, first='a', include_events=False):
    if strategy not in STRATEGY: raise ValueError('Unknown strategy')
    if a not in weapons or b not in weapons: raise ValueError('Unknown weapon')
    rng = random.Random(f'{seed}|{a}|{b}|{range_m}|{strategy}|{first}')
    w = {'a': weapons[a], 'b': weapons[b]}
    hp = {'a': 100.0, 'b': 100.0}
    ammo = {k: int(v['mag_size']) for k,v in w.items()}
    behavior = STRATEGY[strategy]
    # First shooter is assigned randomly by the experiment; run both assignments
    # for every seed to reduce role/initiative confounding.
    reaction = {k: max(.06, behavior['reaction'] + rng.uniform(-.055, .055)) for k in w}
    reaction[first] = max(.02, reaction[first] - .10)
    next_shot = dict(reaction)
    events = []
    shot_index = {'a': 0, 'b': 0}
    time = 0.0
    distance = float(range_m)
    finish = None
    while time < 18.0:
        actor = min(next_shot, key=lambda k: (next_shot[k], k))
        time = next_shot[actor]
        if time > 18.0: break
        enemy = 'b' if actor == 'a' else 'a'
        if hp[actor] <= 0 or hp[enemy] <= 0: break
        distance = max(1.5, min(100.0, float(range_m) - time * behavior['close_per_sec']))
        weapon = w[actor]
        if ammo[actor] <= 0:
            next_shot[actor] = time + float(weapon.get('reload_time', 1.5))
            ammo[actor] = int(weapon['mag_size'])
            continue
        shot_index[actor] += 1
        ammo[actor] -= 1
        chance = _hit_chance(weapon, distance, strategy)
        damage = 0.0
        for _ in range(int(weapon['pellets'])):
            if rng.random() < chance:
                falloff = 1.0 if distance <= float(weapon['range']) else max(.35, float(weapon['range'])/distance)
                damage += float(weapon['damage']) * falloff
        hp[enemy] = max(0.0, hp[enemy] - damage)
        if include_events:
            events.append({'time_s': round(time, 4), 'type':'shot', 'attacker':actor,
                'weapon': a if actor=='a' else b, 'damage':round(damage, 3),
                'target_hp':round(hp[enemy],3), 'distance_m':round(distance,2),
                'positions': {'a':[0,0], 'b':[round(distance,2),0]}})
        next_shot[actor] = time + 1.0 / float(weapon['fire_rate'])
        if hp[enemy] <= 0:
            finish = actor
            if include_events: events.append({'time_s':round(time,4), 'type':'kill', 'winner':actor})
            break
    return {'winner':finish or 'draw', 'first':first, 'ttk_s':round(time,4) if finish else None,
            'shots':shot_index, 'seed':seed, 'range_m':range_m, 'strategy':strategy,
            'a':a, 'b':b, 'events':events}


def run_suite(weapons:dict, policy:dict, seeds, trace_one=True, progress=None):
    validate_weapons(weapons)
    chosen=policy.get('weapons', list(weapons))
    total=len(list(combinations(chosen,2)))*len(policy.get('ranges',[5,15,35]))*len(policy.get('strategies',['aggressive','defensive','flanker']))
    completed=0
    rows=[]; trace=None
    for a,b in combinations(chosen,2):
        for distance in policy.get('ranges',[5,15,35]):
            for strategy in policy.get('strategies',['aggressive','defensive','flanker']):
                duels=[]
                for seed in seeds:
                    for first in ('a','b'):
                        save = bool(trace_one and trace is None)
                        item = duel(weapons,a,b,distance,strategy,seed,first,include_events=save)
                        if save: trace=item
                        duels.append(item)
                a_wins=sum(d['winner']=='a' for d in duels)
                b_wins=sum(d['winner']=='b' for d in duels)
                draws=len(duels)-a_wins-b_wins
                decisive=a_wins+b_wins
                first_win=sum(d['winner']==d['first'] for d in duels)
                ttk=[d['ttk_s'] for d in duels if d['ttk_s'] is not None]
                rows.append({'a':a,'b':b,'range_m':distance,'strategy':strategy,'duels':len(duels),
                    'a_win_rate':(a_wins+.5*draws)/len(duels),
                    'b_win_rate':(b_wins+.5*draws)/len(duels),
                    'draw_rate':draws/len(duels),'median_ttk_s':median(ttk) if ttk else None,
                    'first_shooter_win_rate':(first_win+.5*draws)/len(duels),
                    'first_shooter_advantage':(first_win+.5*draws)/len(duels)-.5})
                completed+=1
                if progress:
                    progress(completed,total,rows[-1])
    # Spread among weapon matchup win probabilities, within each fixed context.
    by_context=defaultdict(list)
    for row in rows:
        context=(row['range_m'],row['strategy'])
        by_context[context].extend([row['a_win_rate'],row['b_win_rate']])
    spread=max((max(x)-min(x) for x in by_context.values()),default=0)
    return {'mode':'python_approximated_duels','rows':rows,
            'summary':{'duels':sum(r['duels'] for r in rows),
                       'mean_ttk_s':mean(r['median_ttk_s'] for r in rows if r['median_ttk_s'] is not None),
                       'first_shooter_advantage':mean(abs(r['first_shooter_advantage']) for r in rows),
                       'max_matchup_spread':spread},
            'example_trace':trace}


def lookup(rows, a,b,range_m,strategy):
    for r in rows:
        if r['range_m'] == range_m and r['strategy'] == strategy:
            if r['a']==a and r['b']==b: return r['a_win_rate']
            if r['a']==b and r['b']==a: return r['b_win_rate']
    raise ValueError(f'No matchup row for {a} vs {b} @ {range_m} {strategy}')


def balance_violations(report, policy):
    violations=[]
    for target in policy.get('neutral_matchups',[]):
        rate=lookup(report['rows'],target['a'],target['b'],target['range'],target['strategy'])
        if not target['min_rate'] <= rate <= target['max_rate']:
            violations.append({'type':'neutral_matchup','target':target,'observed':rate})
    edge=report['summary']['first_shooter_advantage']
    if edge > policy.get('max_first_shooter_edge',1):
        violations.append({'type':'first_shooter_edge','observed':edge})
    return violations


def regression_violations(baseline,candidate,policy):
    neutral={(t['a'],t['b'],t['range'],t['strategy']) for t in policy.get('neutral_matchups',[])}
    source={(r['a'],r['b'],r['range_m'],r['strategy']):r['a_win_rate'] for r in baseline['rows']}
    regression=[]
    for row in candidate['rows']:
        key=(row['a'],row['b'],row['range_m'],row['strategy'])
        reverse=(row['b'],row['a'],row['range_m'],row['strategy'])
        if key in neutral or reverse in neutral:
            continue
        delta=abs(row['a_win_rate']-source[key])
        if delta > policy.get('max_off_target_regression',.15):
            regression.append({'matchup':key,'shift':round(delta,4)})
    return regression
