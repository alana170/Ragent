import copy
import pytest
from pydantic import ValidationError
from agents.schemas import BalanceGoal, PatchProposal
from agents.proposer import MockProposer
from agents.tools import Tools, mock_runner
from agents.evaluator import aggregate, compare
from agents.orchestrator import run

CONFIG={'weapons':{'sniper':{'damage':80.0}}, 'abilities':{'smoke':{'duration':10.0}}}
CONSTRAINTS={'bounds':{'weapons.sniper.damage':[0,100], 'abilities.smoke.duration':[0,20]}}

def test_schema_and_deterministic_proposals():
    with pytest.raises(ValidationError): BalanceGoal(goal='', matches=0)
    g=BalanceGoal(goal='balance',constraints=CONSTRAINTS)
    p=MockProposer()
    assert p.propose(CONFIG,g,[],0)==p.propose(CONFIG,g,[],0)

def test_patch_validation_and_copy():
    t=Tools(mock_runner,'mock'); original=copy.deepcopy(CONFIG)
    p=PatchProposal(name='x',changes=[{'path':'weapons.sniper.damage','value':75.0}],rationale='r',predicted_tradeoffs='t')
    changed=t.validate_patch(CONFIG,p,CONSTRAINTS)
    assert changed['weapons']['sniper']['damage']==75 and CONFIG==original
    for path,value in [('bad.path',1.0),('weapons.sniper.damage',200.0),('weapons.sniper.damage','75')]:
        p.changes[0].path=path; p.changes[0].value=value
        with pytest.raises(ValueError): t.validate_patch(CONFIG,p,CONSTRAINTS)

def row(seed, rounds, rate, scenario='s'):
    return {'seed':seed,'scenario_id':scenario,'rounds':rounds,'winner':'attackers','metrics':{'attacker_win_rate':rate,'defender_win_rate':1-rate}}

def test_round_weighted_and_paired():
    a=[row(1,10,.2),row(2,30,.6)]
    assert aggregate(a)['attacker_win_rate']==pytest.approx(.5)
    b=[row(1,10,.3),row(2,30,.7)]
    result=compare(a,b)
    assert result['attacker_rate_delta']==pytest.approx(.1)
    assert result['paired_matches']==2 and result['confidence_interval_95'] is None

def test_budget_feedback_and_mock_labels():
    calls=[]
    def runner(config, scenarios, seeds, workers=1):
        calls.append(len(scenarios)*len(seeds)); return mock_runner(config,scenarios,seeds,workers)
    report=run(CONFIG,BalanceGoal(goal='balance',constraints=CONSTRAINTS,matches=100,iterations=2),runner,'mock')
    assert sum(calls)<=100 and len(calls)==5
    assert {x['iteration'] for x in report.candidates}=={1,2}
    assert report.mode=='mock' and 'synthetic' in report.caveats[0]
    assert len([x for x in report.tool_log if x['tool']=='propose_patch'])==2

def test_regression_rejected():
    def runner(config,scenarios,seeds,workers=1):
        rows=mock_runner(config,scenarios,seeds,workers)
        if config != CONFIG:
            for r in rows:
                r['metrics']['attacker_win_rate']=.9; r['metrics']['defender_win_rate']=.1
        return rows
    report=run(CONFIG,BalanceGoal(goal='balance',constraints={**CONSTRAINTS,'max_scenario_regression':.01},matches=100,iterations=2),runner,'fixture')
    assert report.recommendation is None
    assert all(c['status']=='rejected' and c.get('regressions') for c in report.candidates)

def test_failure_and_no_secret(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','secret-for-test')
    def fail(*args,**kwargs): raise RuntimeError('simulator failed')
    report=run(CONFIG,BalanceGoal(goal='balance',constraints=CONSTRAINTS,matches=9,iterations=2),fail,'fixture',proposer=MockProposer())
    assert report.findings[0].kind=='baseline_failure'
    assert 'secret-for-test' not in report.model_dump_json()
