"""Validated tools and an explicitly synthetic simulator adapter."""
import copy
import datetime
import math
import random
from .evaluator import aggregate, compare

class Tools:
    def __init__(self, runner, mode): self.runner, self.mode, self.log = runner, mode, []
    def record(self, name, **kwargs):
        # Log only explicitly selected non-secret metadata, never config or provider input.
        self.log.append({'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'tool': name, 'arguments': kwargs})
    def inspect_config(self, config):
        self.record('inspect_config', top_level_keys=list(config))
        return copy.deepcopy(config)
    def analyze_baseline(self, rows):
        self.record('analyze_baseline', matches=len(rows))
        return aggregate(rows)
    def propose_patch(self, proposer, config, goal, feedback, iteration):
        self.record('propose_patch', iteration=iteration)
        return proposer.propose(config, goal, feedback, iteration)
    def validate_patch(self, config, proposal, constraints):
        self.record('validate_patch', proposal=proposal.name, paths=[c.path for c in proposal.changes])
        result = copy.deepcopy(config); seen = set()
        allowed = constraints.get('allowed_paths')
        prohibited = constraints.get('prohibited_paths', [])
        bounds = constraints.get('bounds', {})
        for change in proposal.changes:
            path = change.path
            if path in seen: raise ValueError('duplicate path: '+path)
            seen.add(path)
            if (allowed is not None and path not in allowed) or any(path == p or path.startswith(p+'.') for p in prohibited): raise ValueError('prohibited path: '+path)
            parts = path.split('.'); node = result
            for part in parts[:-1]:
                if not isinstance(node, dict) or part not in node: raise ValueError('unknown path: '+path)
                node = node[part]
            if not isinstance(node, dict) or parts[-1] not in node or isinstance(node[parts[-1]], (dict, list)): raise ValueError('unknown or non-leaf path: '+path)
            old = node[parts[-1]]; value = change.value
            if type(value) is not type(old): raise ValueError('invalid type: '+path)
            if isinstance(value, (int,float)) and not isinstance(value, bool):
                if not math.isfinite(value): raise ValueError('non-finite value: '+path)
                if path not in bounds: raise ValueError('missing bounds: '+path)
                low, high = bounds[path]
                if not low <= value <= high: raise ValueError('out of bounds: '+path)
            node[parts[-1]] = value
        return result
    def run_patch_experiment(self, config, scenarios, seeds):
        self.record('run_patch_experiment', scenarios=[s['id'] for s in scenarios], seeds=seeds, mode=self.mode)
        return self.runner(config, scenarios, seeds, workers=1)
    def compare_results(self, baseline, candidate):
        self.record('compare_results', baseline_matches=len(baseline), candidate_matches=len(candidate))
        return compare(baseline, candidate)
    def generate_report(self, report):
        self.record('generate_report')
        report.tool_log = list(self.log)
        return report

def mock_runner(config, scenarios, seeds, workers=1):
    rows=[]
    for scenario in scenarios:
        for seed in seeds:
            rng=random.Random(f"{seed}:{scenario['id']}")
            damage=config.get('weapons',{}).get('sniper',{}).get('damage',80)
            smoke=config.get('abilities',{}).get('smoke',{}).get('duration',10)
            rate=max(0,min(1, .48-(damage-80)*.003+(smoke-10)*.002+rng.uniform(-.15,.15)))
            rows.append({'seed':seed,'scenario_id':scenario['id'],'winner':'attackers' if rng.random()<rate else 'defenders','rounds':20,'round_duration':40,'players':[],'events':[], 'metrics':{'attacker_win_rate':rate,'defender_win_rate':1-rate,'weapon_performance':{'sniper':damage/100},'ability_performance':{'smoke':smoke/20}}})
    return rows

def simulator_adapter():
    try:
        from experiments.runner import run_experiments
    except ModuleNotFoundError as exc:
        if exc.name not in ('experiments', 'experiments.runner'): raise
        return mock_runner, 'mock'
    return run_experiments, 'simulator'
