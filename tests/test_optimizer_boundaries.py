import json
from copy import deepcopy
from unittest.mock import patch

import pytest
from ragent_openfire import agent

WEAPONS = {'w': {'damage': 10, 'fire_rate': 10.0}}
POLICY = {'allowed_parameters': {'w.damage': [1, 20], 'w.fire_rate': [1, 20]},
          'target_weapons': ['w'], 'search_seeds': 2, 'verification_seeds': 2,
          'candidate_budget': 6, 'neutral_matchups': [], 'max_first_shooter_edge': 1}


def fake_suite(weapons, policy, seeds, **kwargs):
    return {'value': weapons['w']['damage'], 'seeds': list(seeds), 'rows': [], 'summary': {}}


def test_candidates_are_validated_and_seed_ranges_are_disjoint():
    suggestions = [
        {'changes': {'w.damage': True}, 'rationale': 'bad'},
        {'changes': {'w.damage': float('nan')}, 'rationale': 'bad'},
        {'changes': {'w.damage': 11.5}, 'rationale': 'bad integer'},
        {'changes': {'unknown.x': 3}, 'rationale': 'bad path'},
    ]
    with patch.object(agent, 'run_suite', side_effect=fake_suite), \
         patch.object(agent, 'balance_violations', return_value=[]), \
         patch.object(agent, '_regression', return_value=[]):
        result = agent.optimize(WEAPONS, POLICY, suggestion_provider=lambda *_: (suggestions, {'status': 'live'}))
    assert all(not c['eligible'] and 'error' in c for c in result['candidates'][1:5])
    assert result['model_status']['status'] == 'fallback'
    assert result['model_status']['reason'] == 'invalid_model_output'
    assert result['verification']['discovery_seeds']['end_exclusive'] <= result['verification']['final_seeds']['start']
    json.dumps(result, allow_nan=False)


def test_invalid_and_duplicate_candidates_do_not_consume_budget():
    suggestions = [
        {'changes': {'w.damage': 21}, 'rationale': 'out of bounds'},
        {'changes': {'w.damage': 11}, 'rationale': 'first valid candidate'},
        {'changes': {'w.damage': 11}, 'rationale': 'duplicate candidate'},
    ]
    paired_adjustment = {'changes': {'w.damage': 12, 'w.fire_rate': 12.0},
                         'rationale': 'paired heuristic adjustment'}
    with patch.object(agent, 'run_suite', side_effect=fake_suite), \
         patch.object(agent, 'balance_violations', return_value=[]), \
         patch.object(agent, '_regression', return_value=[]), \
         patch.object(agent, '_heuristic_candidates', return_value=[
             {'changes': {'w.fire_rate': 11.0}, 'rationale': 'unique heuristic adjustment'},
             paired_adjustment,
         ]):
        result = agent.optimize(
            WEAPONS,
            dict(POLICY, candidate_budget=4),
            suggestion_provider=lambda *_: (suggestions, {'status': 'live'}),
        )

    assert result['search_budget'] == 4
    assert sum('error' not in candidate and 'metrics' in candidate for candidate in result['candidates']) == 4
    assert [candidate['error'] for candidate in result['candidates'] if 'error' in candidate] == [
        'Invalid value w.damage: 21',
        'Duplicate candidate',
    ]
    assert any(candidate['changes'] == paired_adjustment['changes'] for candidate in result['candidates'])


def test_original_regression_blocks_candidate_and_no_eligible_is_selected():
    original = deepcopy(WEAPONS)
    original['w']['damage'] = 9
    def regression(before, after, policy):
        return ['original regression'] if before['value'] == 9 else []
    with patch.object(agent, 'run_suite', side_effect=fake_suite), \
         patch.object(agent, 'balance_violations', return_value=[]), \
         patch.object(agent, '_regression', side_effect=regression):
        result = agent.optimize(WEAPONS, POLICY, original_baseline=original)
    assert result['chosen'] is None
    assert not result['candidate_accepted']
    assert result['verification']['regressions'] == ['original regression']
    assert all(not c['eligible'] for c in result['candidates'])


def test_seed_overlap_is_rejected():
    with pytest.raises(ValueError, match='disjoint'):
        agent.optimize(WEAPONS, dict(POLICY, final_verification_seed_offset=1))


@pytest.mark.parametrize('field,value', [
    ('damage', True), ('fire_rate', float('nan')), ('reload_time', float('inf')),
    ('reload_time', 0), ('mag_size', 2.5), ('pellets', 1.5),
    ('spread_deg', -1), ('aim_spread_deg', False),
])
def test_weapon_validation_rejects_invalid_numeric_fields(field, value):
    from ragent_openfire.simulation import validate_weapons
    weapon = {'damage': 10, 'fire_rate': 5, 'mag_size': 10, 'pellets': 1,
              'range': 20, 'spread_deg': 1, 'reload_time': 1}
    weapon[field] = value
    with pytest.raises(ValueError):
        validate_weapons({'w': weapon})
