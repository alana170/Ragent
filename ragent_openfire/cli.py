"""RAGENT OpenFire stat-bridge CLI. stdlib-only, no external installs needed."""
import argparse
from copy import deepcopy
import difflib
import json
import re
from pathlib import Path
from .weapon_export import export_file, extract_weapons, _dicts
from .simulation import run_suite, balance_violations
from .agent import optimize
from .reports import html_report


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def save(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def update_weapon_db(source,patch):
    """Produce a patchable GDScript source copy; don't mutate Git submodule."""
    old=Path(source).read_text(encoding='utf-8')
    original=extract_weapons(old)
    if set(patch)-set(original): raise ValueError('Unexpected weapon')
    new=old
    for block in _dicts(old):
        m=re.search(r'"id"\s*:\s*"([^"\\]+)"',block)
        if not m: continue
        wid=m.group(1)
        if wid not in patch: continue
        updated=block
        for key,value in patch[wid].items():
            if key not in original[wid] or value==original[wid][key]:continue
            if not isinstance(value,(int,float)):raise ValueError('Non-numeric patch')
            pattern=r'("'+re.escape(key)+r'"\s*:\s*)(-?\d+(?:\.\d+)?)'
            updated,n=re.subn(pattern,lambda found: found.group(1)+str(value),updated,count=1)
            if n!=1: raise ValueError(f'Cannot patch {wid}.{key}')
        new=new.replace(block,updated,1)
    return old,new


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('export');q.add_argument('--source',required=True);q.add_argument('--output',default='results/openfire_weapons.json')
    q=sub.add_parser('plant');q.add_argument('--weapons',required=True);q.add_argument('--output',default='results/planted_weapons.json');q.add_argument('--factor',type=float,default=1.5)
    q=sub.add_parser('simulate');q.add_argument('--weapons',required=True);q.add_argument('--policy',required=True);q.add_argument('--matches',type=int,default=24);q.add_argument('--output',default='results/openfire_simulation.json')
    q=sub.add_parser('optimize');q.add_argument('--weapons',required=True);q.add_argument('--policy',required=True);q.add_argument('--output',default='results/openfire_agent.json');q.add_argument('--html',default='results/openfire_report.html');q.add_argument('--patched',default='results/verified_stats.json')
    q=sub.add_parser('gd-patch');q.add_argument('--source',required=True);q.add_argument('--weapons',required=True);q.add_argument('--output',default='results/patched_weapon_db.gd');q.add_argument('--diff',default='results/weapon_db.diff')
    args=p.parse_args()
    if args.command=='export':
        w=export_file(args.source,args.output);print(f'Extracted {len(w)} weapon configurations into {args.output}')
    elif args.command=='plant':
        data=load(args.weapons);data=deepcopy(data)
        data['weapons']['smg']['fire_rate']=round(data['weapons']['smg']['fire_rate']*args.factor,4)
        data['source']='OpenFire exported stats + deliberately planted SMG fire-rate imbalance'
        save(args.output,data);print(f'Wrote deliberately imbalanced configuration to {args.output}')
    elif args.command=='simulate':
        if args.matches<1: p.error('--matches must be >=1')
        policy=load(args.policy);w=load(args.weapons)['weapons']
        report=run_suite(w,policy,range(args.matches))
        report['violations']=balance_violations(report,policy)
        save(args.output,report);print(json.dumps(report['summary'],indent=2))
    elif args.command=='optimize':
        policy=load(args.policy);w=load(args.weapons)['weapons']
        report=optimize(w,policy);save(args.output,report)
        save(args.patched,{'source':'RAGENT verified candidate (not applied to upstream)','weapons':report['patched_weapons']})
        html_report(report,args.html)
        print(f'Agent={report["agent_mode"]}; candidates={report["search_budget"]}; held-out={report["verification"]["passed"]}; report={args.html}')
    elif args.command=='gd-patch':
        old,new=update_weapon_db(args.source,load(args.weapons)['weapons'])
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        Path(args.output).write_text(new,encoding='utf-8')
        diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/scripts/autoload/weapon_db.gd',tofile='b/scripts/autoload/weapon_db.gd'))
        Path(args.diff).write_text(diff,encoding='utf-8')
        print(f'Generated {args.output} and {args.diff} (review before applying to game)')

if __name__=='__main__':main()
