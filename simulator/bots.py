"""Deterministic policy targets."""
from .maps import distance


def destination(player, config, planted):
    sites = config['map']['sites']
    site = sites[player['site']]
    if planted is not None:
        site = sites[planted]
    if player['team'] == 'defenders' and player['policy'] == 'hold' and planted is None:
        return site
    if player['policy'] == 'flank' and player['pos'][0] < 48:
        return [50, 30]
    return site


def nearest_visible(player, enemies, geometry, smokes):
    from .maps import visible
    candidates = [e for e in enemies if e['health'] > 0 and visible(player['pos'], e['pos'], geometry, smokes)]
    return min(candidates, key=lambda e: (distance(player['pos'], e['pos']), e['id'])) if candidates else None
