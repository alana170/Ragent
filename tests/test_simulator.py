import copy
import json
import unittest
from pathlib import Path
from simulator import abilities, maps, objectives
from simulator.engine import simulate_match
from experiments.runner import run_experiments
from experiments.metrics import aggregate

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'configs/baseline.json').read_text())
SCENARIOS = json.loads((ROOT / 'configs/scenarios.json').read_text())


class SimulatorTests(unittest.TestCase):
    def test_replay_and_json_contract(self):
        a = simulate_match(CONFIG, 42, SCENARIOS[0])
        b = simulate_match(CONFIG, 42, SCENARIOS[0])
        self.assertEqual(json.dumps(a, allow_nan=False), json.dumps(b, allow_nan=False))
        self.assertTrue({'seed', 'scenario_id', 'winner', 'rounds', 'round_duration', 'players', 'events', 'metrics'} <= a.keys())
        self.assertIn(a['winner'], ('attackers', 'defenders'))
        self.assertEqual(len(a['players']), 6)
        self.assertEqual(a['rounds'], CONFIG['rounds'])
        self.assertAlmostEqual(a['metrics']['attacker_win_rate'] + a['metrics']['defender_win_rate'], 1)
        self.assertTrue(all(0 <= p['health'] <= CONFIG['health'] for p in a['players']))
        for event in a['events']:
            if event['type'] == 'damage':
                self.assertGreater(event['damage'], 0)
                self.assertLessEqual(event['damage'], CONFIG['weapons'][event['weapon']]['damage'])
                self.assertGreaterEqual(event['health'], 0)
        for stats in a['metrics']['weapon_performance'].values():
            self.assertLessEqual(stats['hits'], stats['shots'])
            self.assertLessEqual(stats['kills'], stats['hits'])

    def test_parallel_order_and_inputs(self):
        c, s = copy.deepcopy(CONFIG), copy.deepcopy(SCENARIOS)
        serial = run_experiments(c, s, [4, 1], 1)
        self.assertEqual(serial, run_experiments(c, s, [4, 1], 2))
        self.assertEqual([(r['scenario_id'], r['seed']) for r in serial], [(x['id'], i) for x in s for i in (4, 1)])
        self.assertEqual(c, CONFIG)
        self.assertEqual(s, SCENARIOS)

    def test_sniper_advantage(self):
        summaries = aggregate(run_experiments(CONFIG, SCENARIOS, list(range(30))))
        self.assertGreater(summaries[1]['attacker_win_rate'], summaries[0]['attacker_win_rate'] + 0.1)
        control = copy.deepcopy(SCENARIOS[1])
        control['id'] = 'sniper_control'
        control.pop('overrides')
        compared = aggregate(run_experiments(CONFIG, [control, SCENARIOS[1]], list(range(30))))
        self.assertGreater(compared[1]['attacker_win_rate'], compared[0]['attacker_win_rate'] + 0.1)

    def test_objective_transitions(self):
        cfg = copy.deepcopy(CONFIG)
        state = {'planted': None, 'detonation': None, 'action': None, 'progress': 0, 'time': 0}
        p = {'id': 'a0', 'team': 'attackers', 'health': 100, 'pos': cfg['map']['sites'][0], 'site': 0}
        self.assertIsNone(objectives.update(state, [p], cfg, 1))
        self.assertEqual(objectives.update(state, [p], cfg, 1)[0], 'plant')
        self.assertEqual(state['planted'], 0)
        d = {'id': 'd0', 'team': 'defenders', 'health': 100, 'pos': p['pos'], 'site': 0}
        self.assertIsNone(objectives.update(state, [d], cfg, 1))
        self.assertIsNone(objectives.update(state, [], cfg, 1))
        self.assertIsNone(objectives.update(state, [d], cfg, 2))
        self.assertEqual(objectives.update(state, [d], cfg, 1)[0], 'defuse')

    def test_abilities_and_geometry(self):
        p = {'health': 50, 'ability_ready': {'heal': 0, 'smoke': 0, 'dash': 0}, 'dash_until': 0}
        stats = {'uses': 0, 'healing': 0}
        smoke = []
        self.assertTrue(abilities.use(p, 'heal', 0, CONFIG, stats, smoke))
        self.assertEqual(p['heal_remaining'], 35)
        self.assertFalse(abilities.use(p, 'heal', 1, CONFIG, stats, smoke))
        self.assertTrue(abilities.use(p, 'dash', 0, CONFIG, stats, smoke))
        self.assertGreater(p['dash_until'], 0)
        self.assertTrue(abilities.use(p, 'smoke', 0, CONFIG, stats, smoke, [5, 5]))
        self.assertFalse(maps.visible([0, 5], [10, 5], {'cover': []}, smoke))
        self.assertTrue(maps.visible([0, 5], [10, 5], {'cover': []}, []))
        self.assertEqual(maps.move([0, 0], [10, 0], 20, {'width': 20, 'height': 20, 'cover': [[4, -1, 5, 1]]}), [0, 0])
        result = simulate_match(CONFIG, 42, SCENARIOS[0])
        self.assertGreater(result['metrics']['ability_performance']['heal']['healing'], 0)

    def test_tick_limit_and_error_context(self):
        cfg = copy.deepcopy(CONFIG)
        cfg.update({'rounds': 1, 'max_ticks': 1})
        result = simulate_match(cfg, 0, SCENARIOS[0])
        self.assertEqual(result['events'][-1]['reason'], 'tick_limit')
        with self.assertRaisesRegex(RuntimeError, 'scenario=.*seed=7'):
            run_experiments({'rounds': 0, 'tick_seconds': 1, 'max_ticks': 1, 'round_time': 1}, [{'id': 'bad'}], [7])


if __name__ == '__main__':
    unittest.main()
