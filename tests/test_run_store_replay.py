import json

from ragent_openfire.replay import make_replays
from ragent_openfire.run_store import load_runs, save_run
from ragent_openfire.simulation import duel


def test_saved_run_reload_and_interrupted_state(tmp_path):
    complete = {'id': 'a' * 32, 'status': 'complete', 'events': [{'message': 'done'}],
                'result': {'candidate': 1}}
    running = {'id': 'b' * 32, 'status': 'running', 'events': []}
    save_run(tmp_path, complete)
    save_run(tmp_path, running)
    (tmp_path / 'run_bad.json').write_text('{bad', encoding='utf-8')
    restored = load_runs(tmp_path)
    assert restored[complete['id']] == complete
    assert restored[running['id']]['status'] == 'interrupted'
    assert json.loads((tmp_path / ('run_' + running['id'] + '.json')).read_text())['status'] == 'interrupted'


def test_replays_match_direct_duel_and_include_reconstructable_events():
    weapon = {'damage': 1, 'fire_rate': 5, 'mag_size': 1, 'pellets': 1,
              'range': 50, 'spread_deg': 1, 'reload_time': 0.2}
    baseline = {'a': dict(weapon), 'b': dict(weapon)}
    proposal = {'a': dict(weapon, damage=2), 'b': dict(weapon)}
    policy = {'weapons': ['a', 'b'], 'ranges': [5], 'strategies': ['aggressive']}
    bundle = make_replays(baseline, proposal, proposal, policy, seed=17)
    trace = bundle['traces']['proposal']['trace']
    assert trace == duel(proposal, **bundle['scenario'], include_events=True)
    assert trace['events'][0]['type'] == 'initial'
    assert trace['events'][-1]['type'] == 'terminal'
    assert any(e['type'] == 'reload' and e['complete_s'] >= e['time_s'] for e in trace['events'])
    assert all('ammo' in e for e in trace['events'] if e['type'] == 'shot')
    assert bundle['traces']['baseline']['config_sha256'] != bundle['traces']['proposal']['config_sha256']
