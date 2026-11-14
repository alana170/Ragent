import json

def markdown(report):
    r = report.model_dump() if hasattr(report, 'model_dump') else report
    lines = ['# Balance analysis', '', f"**Data source: {r['mode']}**", '', f"Goal: {r['goal']['goal']}", '', '## Baseline', '', '```json', json.dumps(r['baseline'], indent=2), '```', '', '## Candidates', '']
    for c in r['candidates']:
        lines += [f"### {c['proposal']['name']}", '', c['proposal']['rationale'], '', f"Status: {c['status']}", '', '```json', json.dumps({k:v for k,v in c.items() if k != 'proposal'}, indent=2), '```', '']
    lines += ['## Recommendation', '', '```json', json.dumps(r['recommendation'], indent=2), '```', '', '## QA findings', '']
    lines += [f"- {f['kind']}: {f['message']} (scenario: {f.get('scenario_id')}, seed: {f.get('seed')})" for f in r['findings']] or ['No issues detected in completed observations.']
    lines += ['', '## Caveats', ''] + [f'- {c}' for c in r['caveats']] + ['', '## Reproduction', '', '```sh', r['reproduction'], '```', '']
    return '\n'.join(lines)
