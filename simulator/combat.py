"""Weapon fire and bounded damage."""
from .maps import distance


def fire(shooter, target, weapon, now, rng, stats):
    if now < shooter['ready']:
        return None
    if shooter['ammo'] <= 0:
        shooter['ammo'] = weapon['ammo']
        shooter['ready'] = now + weapon['reload']
        return None
    shooter['ammo'] -= 1
    shooter['ready'] = now + weapon['interval']
    stats['shots'] += 1
    dist = distance(shooter['pos'], target['pos'])
    chance = max(0.0, min(1.0, weapon['accuracy'] * (1 if dist <= weapon['range'] else weapon['falloff'])))
    if rng.random() >= chance:
        return 0.0
    damage = min(target['health'], weapon['damage'] * (1 if dist <= weapon['range'] else weapon['falloff']))
    target['health'] = max(0.0, target['health'] - damage)
    stats['hits'] += 1
    stats['damage'] += damage
    if target['health'] == 0:
        stats['kills'] += 1
    return damage
