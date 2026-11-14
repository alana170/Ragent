"""Ability state transitions."""

def use(player, name, now, config, stats, smokes, target=None):
    if now < player['ability_ready'][name]:
        return False
    spec = config['abilities'][name]
    if name == 'heal':
        if player['health'] <= 0 or player['health'] >= config['health']:
            return False
        player['heal_remaining'] = spec['amount']
        player['heal_until'] = now + spec['duration']
    elif name == 'dash':
        player['dash_until'] = now + spec['duration']
    elif name == 'smoke':
        if target is None:
            return False
        smokes.append({'pos': list(target), 'radius': spec['radius'], 'until': now + spec['duration']})
    else:
        raise ValueError('unknown ability: ' + name)
    player['ability_ready'][name] = now + spec['cooldown']
    stats['uses'] += 1
    return True
