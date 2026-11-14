"""Round-weighted experiment summaries."""
def aggregate(results):
    groups = {}
    for result in results:
        group = groups.setdefault(result['scenario_id'], {'scenario_id': result['scenario_id'], 'matches': 0, 'rounds': 0, 'attacker_round_wins': 0.0})
        group['matches'] += 1
        group['rounds'] += result['rounds']
        group['attacker_round_wins'] += result['metrics']['attacker_win_rate'] * result['rounds']
    for group in groups.values():
        group['attacker_win_rate'] = group['attacker_round_wins'] / group['rounds']
        group['defender_win_rate'] = 1 - group['attacker_win_rate']
    return list(groups.values())
