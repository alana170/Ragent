"""Bounded search with programmatic eligibility and independent verification.

Optional model suggestions are hypotheses; deterministic code validates and scores
all candidates, and a disjoint holdout determines the final verdict.
"""
from __future__ import annotations
from copy import deepcopy
import math
from .simulation import run_suite, balance_violations, lookup, regression_violations


def _change(weapons,path,value,bounds):
    weapon,field=path.split('.',1)
    if path not in bounds or weapon not in weapons or field not in weapons[weapon]:
        raise ValueError(f'Unapproved parameter: {path}')
    lo,hi=bounds[path]
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f'Invalid value {path}: {value}')
    original=weapons[weapon][field]
    if isinstance(original,int):
        if int(value)!=value: raise ValueError(f'{path} expects integer')
        value=int(value)
    return value


def _heuristic_candidates(weapons,policy):
    targets=set(policy.get('target_weapons',[policy.get('target_weapon')]))
    candidates=[]
    for factor in (.95,1.05,.9,1.1,.85,1.2,.8,.79,.78,.77,.76,.75,.7):
        for path,(lo,hi) in policy['allowed_parameters'].items():
            weapon,field=path.split('.',1)
            if weapon not in targets: continue
            old=weapons[weapon][field]
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


def optimize(weapons, policy, progress=None, allow_llm=True, suggestion_provider=None,
             original_baseline=None, seed_offset=0):
    """Search discovery data, freeze the eligible choice, then verify independently."""
    baseline = deepcopy(weapons)
    original = deepcopy(original_baseline if original_baseline is not None else weapons)
    count = int(policy.get('search_seeds', 24))
    heldout_count = int(policy.get('verification_seeds', 48))
    train_seeds = range(seed_offset, seed_offset + count)
    holdout_start = seed_offset + int(policy.get('final_verification_seed_offset', 200000))
    heldout_seeds = range(holdout_start, holdout_start + heldout_count)
    if set(train_seeds).intersection(heldout_seeds):
        raise ValueError('Discovery and final verification seeds must be disjoint')
    original_train = run_suite(original, policy, train_seeds, trace_one=False)
    proposal_train = run_suite(baseline, policy, train_seeds, trace_one=False)
    metadata = {'status': 'fallback', 'reason': 'disabled' if not allow_llm else 'unavailable'}
    suggestions = []
    if allow_llm and suggestion_provider:
        try:
            suggestions, metadata = suggestion_provider(deepcopy(baseline), deepcopy(policy), deepcopy(proposal_train))
            if not isinstance(suggestions, list) or not isinstance(metadata, dict):
                raise ValueError('Invalid suggestion response')
            suggestions = suggestions[:4]
        except Exception as exc:
            suggestions = []
            metadata = {'status': 'fallback', 'reason': type(exc).__name__}
    mode = 'gemini' if metadata.get('status') == 'live' else 'heuristic_no_llm'
    proposals = [dict(c, source='gemini') if isinstance(c, dict) else c for c in suggestions]
    proposals += [dict(c, source='heuristic') for c in _heuristic_candidates(baseline, policy)]
    proposals.insert(0, {'changes': {}, 'rationale': 'Unchanged proposal comparator.', 'source': 'comparator'})
    attempts, seen = [], set()
    budget = max(1, min(28, int(policy.get('candidate_budget', 28))))
    evaluated_count = 0
    for candidate in proposals:
        if evaluated_count >= budget:
            break
        index = len(attempts) + 1
        entry = {'id': f'candidate-{index}', 'source': candidate.get('source', 'gemini') if isinstance(candidate, dict) else 'gemini',
                 'changes': candidate.get('changes') if isinstance(candidate, dict) else None,
                 'rationale': candidate.get('rationale', '') if isinstance(candidate, dict) else '', 'eligible': False}
        counted = False
        try:
            changes = entry['changes']
            if not isinstance(changes, dict) or (not changes and entry['source'] != 'comparator'):
                raise ValueError('Candidate changes must be a non-empty object')
            if not isinstance(entry['rationale'], str):
                raise ValueError('Candidate rationale must be text')
            patch, normalized = deepcopy(baseline), {}
            for path, value in changes.items():
                if not isinstance(path, str) or '.' not in path:
                    raise ValueError('Invalid parameter path')
                value = _change(baseline, path, value, policy['allowed_parameters'])
                w, k = path.split('.', 1)
                patch[w][k] = value
                normalized[path] = value
            key = tuple(sorted(normalized.items()))
            if key in seen:
                raise ValueError('Duplicate candidate')
            seen.add(key)
            evaluated_count += 1
            counted = True
            entry['changes'] = normalized
            report = proposal_train if not normalized else run_suite(patch, policy, train_seeds, trace_one=False)
            issues = balance_violations(report, policy)
            regress = _regression(original_train, report, policy)
            proposal_regress = _regression(proposal_train, report, policy)
            midpoint_error = sum(abs(lookup(report['rows'], t['a'], t['b'], t['range'], t['strategy']) - (t['min_rate'] + t['max_rate']) / 2) for t in policy['neutral_matchups'])
            score = 10 * _violation_cost(report, policy) + 2 * len(regress) + 2 * midpoint_error + 0.08 * _distance(normalized, baseline)
            entry.update(score=round(score, 6), search_violations=issues, search_regressions=regress,
                         proposal_search_regressions=proposal_regress, metrics=report,
                         eligible=not issues and not regress and not proposal_regress)
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            # Invalid model values must not poison JSON persistence with NaN/Infinity.
            entry['changes'] = {str(k): (v if isinstance(v, (str, bool, int)) or
                                isinstance(v, float) and math.isfinite(v) else repr(v))
                                for k, v in changes.items()} if isinstance(changes, dict) else None
            if not isinstance(entry['rationale'], str):
                entry['rationale'] = ''
            entry['error'] = str(exc)
        attempts.append(entry)
        if counted and progress:
            progress(f'Agent search {evaluated_count}/{budget} candidates')
    if metadata.get('status') == 'live':
        metadata['validated_response'] = [{'id': a['id'], 'changes': a['changes'], 'rationale': a['rationale']}
                                          for a in attempts if a['source'] == 'gemini' and 'error' not in a]
    if metadata.get('status') == 'live' and not metadata.get('validated_response'):
        metadata.update(status='fallback', reason='invalid_model_output')
        mode = 'heuristic_no_llm'
    comparator = attempts[0]
    viable = [a for a in attempts[1:] if a['eligible'] and
              (not comparator['eligible'] or a['score'] < comparator['score'])]
    viable.sort(key=lambda item: item['score'])
    chosen = viable[0] if viable else None
    modified = deepcopy(baseline)
    if chosen:
        for path, val in chosen['changes'].items():
            w, k = path.split('.', 1)
            modified[w][k] = val
    if progress:
        progress('Agent held-out verification: running independent seeds')
    original_verify = run_suite(original, policy, heldout_seeds, trace_one=False)
    proposal_verify = run_suite(baseline, policy, heldout_seeds, trace_one=False)
    candidate_verify = run_suite(modified, policy, heldout_seeds, trace_one=False)
    issues = balance_violations(candidate_verify, policy)
    regress = _regression(original_verify, candidate_verify, policy)
    proposal_regress = _regression(proposal_verify, candidate_verify, policy)
    approved = bool(chosen and not issues and not regress and not proposal_regress)
    if progress:
        progress(f'Agent recommendation verification {"PASSED" if approved else "NEEDS REVIEW"}')
    return {'agent_mode': mode, 'llm_error': metadata.get('reason'), 'model_status': metadata,
            'search_budget': evaluated_count, 'chosen': chosen, 'candidate_accepted': approved,
            'verification': {'passed': approved, 'violations': issues, 'regressions': regress,
                             'proposal_regressions': proposal_regress,
                             'search_seed_count': len(train_seeds), 'heldout_seed_count': len(heldout_seeds),
                             'discovery_seeds': {'start': train_seeds.start, 'end_exclusive': train_seeds.stop},
                             'final_seeds': {'start': heldout_seeds.start, 'end_exclusive': heldout_seeds.stop}},
            'before': original_verify, 'proposal_before': proposal_verify, 'after': candidate_verify,
            'patched_weapons': modified, 'candidates': attempts,
            'caveat': 'Approximate seeded FPS duels, not real VALORANT or OpenFire 3D navigation tests.'}
