"""Budgeted baseline, proposal, validation, paired evaluation and feedback loop."""
import argparse
import json
import math
import shlex
from pathlib import Path
from .evaluator import aggregate
from .schemas import AgentReport, BalanceGoal, Finding
from .proposer import provider
from .reporter import markdown
from .tools import Tools, simulator_adapter

SCENARIOS = [
    {'id': 'baseline'},
    {'id': 'attacker_flank', 'policies': {'attackers': ['flank', 'flank', 'flank']}},
    {'id': 'attacker_push', 'policies': {'attackers': ['aggressive', 'aggressive', 'aggressive']}},
    {'id': 'defender_flank', 'policies': {'defenders': ['flank', 'flank', 'flank']}},
    {'id': 'rifle_attack', 'loadouts': {'attackers': ['rifle', 'rifle', 'rifle']}},
    {'id': 'suppressed_attack', 'loadouts': {'attackers': ['suppressed_rifle', 'suppressed_rifle', 'suppressed_rifle']}},
]

def issues(rows, config):
    findings=[]
    for r in rows:
        try:
            rate = float(r['metrics']['attacker_win_rate'])
            rounds = float(r['rounds'])
            if not math.isfinite(rate) or not 0 <= rate <= 1 or not math.isfinite(rounds) or rounds <= 0: raise ValueError('invalid rate or round count')
            defense = float(r['metrics'].get('defender_win_rate', 1-rate))
            if not math.isfinite(defense) or abs(rate+defense-1)>1e-6: raise ValueError('side rates do not sum to one')
            if r.get('winner') not in ('attackers', 'defenders'): raise ValueError('invalid winner')
            if rate in (0,1): findings.append(Finding(kind='extreme_observation', message='A match had a one-sided round rate; investigate with more samples.', seed=r.get('seed'), scenario_id=r.get('scenario_id'), repro_config=config))
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(Finding(kind='invariant_violation', message=str(exc), seed=r.get('seed'), scenario_id=r.get('scenario_id'), repro_config=config))
    return findings

def run(config, goal, runner=None, mode=None, proposer=None, reproduction='python -m agents.orchestrator'):
    if runner is None: runner, mode = simulator_adapter()
    mode = mode or 'provided simulator'
    proposer = proposer or provider(); tools = Tools(runner, mode)
    config = tools.inspect_config(config)
    # Each scenario/seed pair is one match. Reserve equal paired samples for every
    # possible candidate (four per iteration), so execution cannot exceed budget.
    slots = 1 + 4 * goal.iterations
    per_run = goal.matches // slots
    if per_run < 1: raise ValueError(f'budget must allow at least {slots} matches for {goal.iterations} iterations')
    scenarios = SCENARIOS[:min(len(SCENARIOS), per_run)]
    seed_count = max(1, per_run // len(scenarios))
    seeds = list(range(seed_count)); used_per_run = len(seeds)*len(scenarios)
    findings=[]; candidates=[]; baseline_rows=[]; baseline={}; feedback=[]
    try:
        baseline_rows = tools.run_patch_experiment(config, scenarios, seeds)
        findings.extend(issues(baseline_rows, config))
        if len(baseline_rows) != used_per_run: raise ValueError('baseline returned an incomplete experiment')
        baseline = tools.analyze_baseline(baseline_rows)
    except Exception as exc:
        findings.append(Finding(kind='baseline_failure', message=f'{type(exc).__name__}: {exc}'))
    if baseline:
        for iteration in range(goal.iterations):
            try: proposals = tools.propose_patch(proposer, config, goal, feedback, iteration)[:4]
            except Exception as exc:
                findings.append(Finding(kind='proposal_failure', message=f'{type(exc).__name__}: {exc}')); break
            for proposal in proposals:
                entry={'iteration':iteration+1, 'proposal':proposal.model_dump(), 'status':'rejected'}
                try:
                    patched=tools.validate_patch(config, proposal, goal.constraints)
                    rows=tools.run_patch_experiment(patched, scenarios, seeds)
                    findings.extend(issues(rows, patched))
                    if len(rows) != used_per_run: raise ValueError('candidate returned an incomplete experiment')
                    metrics=aggregate(rows); comparison=tools.compare_results(baseline_rows, rows)
                    if comparison['paired_matches'] != used_per_run: raise ValueError('candidate did not return the expected matched observations')
                    max_regression=float(goal.constraints.get('max_scenario_regression', .05))
                    regressions={k: abs(v['attacker_rate_delta']) for k,v in comparison['scenario_effects'].items() if abs(v['attacker_rate_delta']) > max_regression}
                    disruption=sum(abs(float(c.value)-float(_get(config,c.path)))/max(abs(float(_get(config,c.path))),1) for c in proposal.changes if isinstance(c.value,(int,float)) and not isinstance(c.value,bool))
                    target=float(goal.constraints.get('target_attacker_win_rate', .5))
                    loss=abs(metrics['attacker_win_rate']-target)
                    reg=sum(regressions.values())
                    breaking=any(f.kind == 'invariant_violation' for f in issues(rows, patched))
                    w=goal.scoring
                    score= -w.get('target',1)*loss-w.get('regression',2)*reg-w.get('disruption',.1)*disruption-w.get('breaking',10)*int(breaking)
                    baseline_loss=abs(baseline['attacker_win_rate']-target)
                    # A candidate must beat the unmodified baseline objective.
                    status = 'evaluated' if not regressions and not breaking and score > -w.get('target',1)*baseline_loss else 'rejected'
                    entry.update(status=status, metrics=metrics, comparison=comparison, score=score, regressions=regressions, disruption=disruption)
                except Exception as exc: entry['error']=f'{type(exc).__name__}: {exc}'
                candidates.append(entry)
            feedback=candidates[-len(proposals):] if proposals else []
    eligible=[c for c in candidates if c['status']=='evaluated']
    recommendation=max(eligible,key=lambda x:x['score']) if eligible else None
    report=AgentReport(goal=goal, mode=mode, baseline=baseline, candidates=candidates, recommendation=recommendation, findings=findings, caveats=['Mock results are synthetic, not observations.' if mode=='mock' else 'Results reflect only the supplied scenarios and seeds.', 'Each match/scenario is a paired bootstrap unit; intervals are omitted for fewer than 10 pairs.', 'These policy and loadout scenarios do not cover every game situation; timeout/hang isolation is not provided.', 'Weapon and ability statistics are recorded as counts per round.'], reproduction=reproduction)
    return tools.generate_report(report)

def _get(config,path):
    for part in path.split('.'): config=config[part]
    return config

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--goal',required=True); p.add_argument('--matches',type=int,default=100); p.add_argument('--iterations',type=int,default=2); p.add_argument('--constraints', help='JSON file with allowed_paths, bounds, prohibited_paths and thresholds'); p.add_argument('--output',default='results/agent_report.json')
    args=p.parse_args(); config=json.loads(Path(args.config).read_text())
    constraints=json.loads(Path(args.constraints).read_text()) if args.constraints else {'bounds':{'weapons.sniper.damage':[0,200], 'abilities.smoke.duration':[0,60]}}
    goal=BalanceGoal(goal=args.goal,matches=args.matches,iterations=args.iterations,constraints=constraints)
    command='python -m agents.orchestrator '+ ' '.join(shlex.quote(x) for x in __import__('sys').argv[1:])
    report=run(config,goal,reproduction=command); output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(report.model_dump_json(indent=2)+'\n'); output.with_suffix('.md').write_text(markdown(report)); print(f'Wrote {output} and {output.with_suffix(".md")} (source: {report.mode})')
if __name__=='__main__': main()
