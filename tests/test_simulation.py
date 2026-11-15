import json
import unittest
from pathlib import Path
from copy import deepcopy
from ragent_openfire.simulation import duel, run_suite, lookup, balance_violations
from ragent_openfire.agent import optimize, _change
from ragent_openfire.reports import format_detail_rate, format_json, format_rate, format_seconds, proposal_html_report
from ragent_openfire.web import apply_proposed_changes, evaluate_proposal

ROOT=Path(__file__).resolve().parents[1]
WEAPONS=json.loads((ROOT/'tests/fixtures/simulation_weapons.json').read_text())['weapons']
POLICY=json.loads((ROOT/'tests/fixtures/simulation_policy.json').read_text())
class SimulationTests(unittest.TestCase):
    def test_report_formats_decimal_values_to_four_places(self):
        self.assertEqual(format_rate(0.123456), '12.35%')
        self.assertEqual(format_detail_rate(0.123456), '12.3456%')
        self.assertEqual(format_seconds(0.123456), '0.1235')
        self.assertEqual(format_json({'rate': 0.123456}), '{\n  "rate": "0.1235"\n}')

    def test_duels_are_deterministic_and_seeded(self):
        x=duel(WEAPONS,'rifle','smg',15,'aggressive',42,'a',True)
        self.assertEqual(x,duel(WEAPONS,'rifle','smg',15,'aggressive',42,'a',True))
        self.assertTrue(x['events'])
        self.assertTrue(all('time_s' in e for e in x['events']))

    def test_metrics_include_all_requested_values(self):
        p=dict(POLICY,ranges=[15],strategies=['aggressive'],weapons=['rifle','smg','shotgun'])
        result=run_suite(WEAPONS,p,range(4))
        self.assertEqual(result['summary']['duels'],3*8)
        for row in result['rows']:
            self.assertAlmostEqual(row['a_win_rate']+row['b_win_rate'],1.0)
            self.assertIn('first_shooter_advantage',row)
            self.assertIn('median_ttk_s',row)
        self.assertIn('max_matchup_spread',result['summary'])
        self.assertTrue(0<=lookup(result['rows'],'rifle','smg',15,'aggressive')<=1)

    def test_guardrails_are_independent(self):
        p=dict(POLICY)
        p['neutral_matchups']=[dict(a='rifle',b='smg',range=15,strategy='aggressive',min_rate=.99,max_rate=1.)]
        r=run_suite(WEAPONS,dict(p,weapons=['rifle','smg'],ranges=[15],strategies=['aggressive']),range(3))
        self.assertTrue(balance_violations(r,p))

    def test_out_of_bounds_or_unknown_edit_rejected(self):
        with self.assertRaises(ValueError):
            _change(WEAPONS,'smg.fire_rate',500,POLICY['allowed_parameters'])
        with self.assertRaises(ValueError):
            _change(WEAPONS,'rifle.fire_rate',9,POLICY['allowed_parameters'])

    def test_agent_retests_with_independent_seeds(self):
        planted=deepcopy(WEAPONS)
        planted['smg']['fire_rate']=21.0
        p=dict(POLICY, search_seeds=24,verification_seeds=48)
        report=optimize(planted,p)
        self.assertIsNotNone(report['chosen'])
        self.assertEqual(report['candidate_accepted'], report['verification']['passed'])
        self.assertEqual(report['agent_mode'],'heuristic_no_llm')
        self.assertLess(report['patched_weapons']['smg']['fire_rate'],21.0)
        self.assertGreaterEqual(report['verification']['final_seeds']['start'], 200000)

    def test_developer_change_is_bounded_and_does_not_mutate_baseline(self):
        original=deepcopy(WEAPONS)
        changed=apply_proposed_changes(WEAPONS,{'smg':{'fire_rate':16.0}},POLICY['allowed_parameters'])
        self.assertEqual(changed['smg']['fire_rate'],16.0)
        self.assertEqual(WEAPONS,original)
        with self.assertRaises(ValueError):
            apply_proposed_changes(WEAPONS,{'smg':{'fire_rate':500}},POLICY['allowed_parameters'])
        with self.assertRaises(ValueError):
            apply_proposed_changes(WEAPONS,{'rifle':{'damage':25}},POLICY['allowed_parameters'])

    def test_developer_evaluation_reports_heldout_comparison(self):
        policy=dict(POLICY,weapons=['rifle','smg'],ranges=[15],strategies=['aggressive'])
        progress=[]
        report=evaluate_proposal(WEAPONS,policy,{'smg':{'fire_rate':16.0}},2,progress.append)
        self.assertEqual(report['after']['summary']['duels'],4)
        self.assertEqual(report['verification']['training']['seed_count'],2)
        self.assertEqual(report['verification']['held_out']['seed_count'],2)
        self.assertEqual(len(report['before']['rows']),1)
        self.assertTrue(any(message.startswith('Training baseline') for message in progress))
        self.assertTrue(progress[-1].startswith('Agent recommendation verification'))
        recommendation=report['recommendation']
        self.assertEqual(recommendation['agent_mode'],'heuristic_no_llm')
        self.assertIn('fire_rate',recommendation['final_stats']['smg'])
        self.assertEqual(recommendation['verification']['heldout_seed_count'],POLICY['verification_seeds'])
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path=proposal_html_report(report,Path(directory)/'report.html')
            content=path.read_text()
            self.assertIn(f"{report['after']['summary']['mean_ttk_s']:.2f}s",content)
            self.assertIn(f"{report['after']['rows'][0]['median_ttk_s']:.4f}",content)
            self.assertIn('Final agent recommendation',content)

if __name__=='__main__':unittest.main()
