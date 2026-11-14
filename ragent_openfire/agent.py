"""Bounded agentic search, grounded in measured duels and held-out verification.

When OPENAI_API_KEY is set, an LLM generates bounded hypotheses. Without a key,
this uses a transparently labeled deterministic candidate generator, not an LLM.
Neither path is permitted to edit the verifier, thresholds, or arbitrary files.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
import os
import urllib.request
from .simulation import run_suite, balance_violations, lookup, regression_violations


def _change(weapons,path,value,bounds):
    weapon,field=path.split('.',1)
    if path not in bounds or weapon not in weapons or field not in weapons[weapon]:
        raise ValueError(f'Unapproved parameter: {path}')
    lo,hi=bounds[path]
    if not isinstance(value,(int,float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f'Invalid value {path}: {value}')
    original=weapons[weapon][field]
    if isinstance(original,int):
        if int(value)!=value: raise ValueError(f'{path} expects integer')
        value=int(value)
    return value


def _heuristic_candidates(weapons,policy):
    targets=set(policy.get('target_weapons',[policy.get('target_weapon')]))
    candidates=[]
    for path,(lo,hi) in policy['allowed_parameters'].items():
        weapon,field=path.split('.',1)
        if weapon not in targets: continue
        old=weapons[weapon][field]
        for factor in (.95,.9,.85,.8,.79,.78,.77,.76,.75,.7,1.05,1.1,1.2):
            val=min(hi,max(lo,old*factor))
            if isinstance(old,int): val=int(round(val))
            if val!=old: candidates.append({'changes':{path:val},'rationale':f'Test a {factor:.0%} scaling of {path}.'})
    # Bounded pairwise search (prunes unrelated weapon/stat combinations).
    fields=list(policy['allowed_parameters'])
    if len(fields)>=2:
        for p1 in fields:
            for p2 in fields:
                if p1>=p2 or p1.split('.')[0] not in targets or p2.split('.')[0] not in targets: continue
                x,y=weapons[p1.split('.')[0]][p1.split('.')[1]],weapons[p2.split('.')[0]][p2.split('.')[1]]
                xx=int(round(x*.9)) if isinstance(x,int) else x*.9
                yy=int(round(y*.95)) if isinstance(y,int) else y*.95
                candidates.append({'changes':{p1:xx,p2:yy},'rationale':'Test a small paired adjustment to interacting stats.'})
    unique={tuple(sorted(c['changes'].items())):c for c in candidates}
    return list(unique.values())


def _llm_candidates(weapons,policy,observed):
    api_key=os.getenv('OPENAI_API_KEY')
    if not api_key: return None
    prompt={'weapon_stats':weapons, 'policy':policy,'observed_neutral_matchup':observed,
        'task':'Return a JSON object with key candidates (array), each {changes: {"weapon.field": number}, rationale: string}. Propose up to 5 small and targeted balance edits; never modify policy, test code, or unauthorized parameters.'}
    body={'model':os.getenv('OPENAI_MODEL','gpt-4o-mini'),'response_format':{'type':'json_object'},
          'messages':[{'role':'system','content':'You are a game balance QA engineer. Output JSON only. Bounds are mandatory.'},
                      {'role':'user','content':json.dumps(prompt)}]}
    req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(body).encode(),
        headers={'Authorization':'Bearer '+api_key, 'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response: reply=json.load(response)
    return json.loads(reply['choices'][0]['message']['content'])['candidates'][:5]


def _regression(baseline,candidate,policy):
    return regression_violations(baseline,candidate,policy)


def _distance(changes,baseline):
    disruption=0
    for path,val in changes.items():
        w,k=path.split('.',1)
        old=baseline[w][k]
        disruption += abs(val-old) / max(1,abs(old))
    return disruption


def _violation_cost(report,policy):
    cost=0.0
    for v in balance_violations(report,policy):
        if v['type']=='neutral_matchup':
            t=v['target']; rate=v['observed']
            cost+=max(t['min_rate']-rate,rate-t['max_rate'],0)
        else:
            cost+=v['observed']-policy['max_first_shooter_edge']
    return cost


def optimize(weapons,policy,progress=None,allow_llm=True):
    baseline=deepcopy(weapons)
    train_seeds=range(int(policy.get('search_seeds',24)))
    heldout_seeds=range(int(policy.get('verification_seed_offset',100000)),
                        int(policy.get('verification_seed_offset',100000))+int(policy.get('verification_seeds',48)))
    original_train=run_suite(baseline,policy,train_seeds)
    observed=[{'target':t,'rate':lookup(original_train['rows'],t['a'],t['b'],t['range'],t['strategy'])} for t in policy['neutral_matchups']]
    mode='llm' if allow_llm and os.getenv('OPENAI_API_KEY') else 'heuristic_no_llm'
    try:
        proposals=_llm_candidates(baseline,policy,observed) if mode=='llm' else _heuristic_candidates(baseline,policy)
    except Exception as e:
        mode='heuristic_llm_failed'
        proposals=_heuristic_candidates(baseline,policy)
        error=f'LLM unavailable: {type(e).__name__}'
    else: error=None
    attempts=[]
    candidates=proposals[:28]
    for index,candidate in enumerate(candidates,1):
        try:
            patch=deepcopy(baseline)
            for path,value in candidate['changes'].items():
                value=_change(baseline,path,value,policy['allowed_parameters'])
                w,k=path.split('.',1);patch[w][k]=value
            report=run_suite(patch,policy,train_seeds,trace_one=False)
            issues=balance_violations(report,policy)
            regress=_regression(original_train,report,policy)
            # Aim for the middle of designer-approved neutral bands, leaving a buffer
            # against sampling noise. The constraints themselves stay independent.
            midpoint_error = sum(abs(lookup(report['rows'], t['a'],t['b'],t['range'],t['strategy']) - (t['min_rate']+t['max_rate'])/2) for t in policy['neutral_matchups'])
            score=10*_violation_cost(report,policy)+2*len(regress)+2*midpoint_error+0.08*_distance(candidate['changes'],baseline)
            attempts.append({'changes':candidate['changes'],'rationale':candidate.get('rationale',''),
                             'score':round(score,6),'search_violations':issues,'search_regressions':regress})
        except (ValueError, KeyError, TypeError) as exc:
            attempts.append({'changes':candidate.get('changes'),'error':str(exc),'score':math.inf})
        if progress:
            progress(f'Agent search {index}/{len(candidates)} candidates')
    viable=[a for a in attempts if math.isfinite(a.get('score',math.inf))]
    viable.sort(key=lambda item:item['score'])
    chosen=viable[0] if viable else None
    modified=deepcopy(baseline)
    if chosen:
        for path,val in chosen['changes'].items():
            w,k=path.split('.',1);modified[w][k]=val
    if progress:
        progress('Agent held-out verification: running independent seeds')
    original_verify=run_suite(baseline,policy,heldout_seeds,trace_one=False)
    candidate_verify=run_suite(modified,policy,heldout_seeds,trace_one=False)
    heldout_issues=balance_violations(candidate_verify,policy)
    heldout_regress=_regression(original_verify,candidate_verify,policy)
    approved=bool(chosen and not heldout_issues and not heldout_regress)
    if progress:
        progress(f'Agent recommendation verification {"PASSED" if approved else "NEEDS REVIEW"}')
    return {'agent_mode':mode,'llm_error':error,'search_budget':len(attempts),
            'chosen':chosen,'candidate_accepted':approved,
            'verification':{'passed':approved,'violations':heldout_issues,'regressions':heldout_regress,
                            'search_seed_count':len(train_seeds),'heldout_seed_count':len(heldout_seeds)},
            'before':original_verify,'after':candidate_verify,'patched_weapons':modified,
            'candidates':attempts,'caveat':'Approximate seeded FPS duels, not real VALORANT or OpenFire 3D navigation tests.'}
