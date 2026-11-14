"""Human-readable offline report for DevHacks demonstration."""
import html
import json
from pathlib import Path
from .run_store import atomic_write

STYLE='''
*{box-sizing:border-box}body{margin:0;background:#f2efe9;color:#181818;font:16px/1.5 Arial,sans-serif}
header{background:#bf1433;color:white;padding:40px 5vw}h1{font-size:54px;margin:0;letter-spacing:-2px}h2{margin:22px 0 12px}
.tag{font-size:13px;letter-spacing:.13em;text-transform:uppercase}main{padding:24px 5vw;max-width:1450px;margin:auto}
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.kpi{border:1px solid #bbb6af;background:#fff;padding:18px}.kpi strong{font-size:28px;display:block}
.note{font-size:13px;color:#555}.warn{color:#a20a29;font-weight:bold}
section{margin-top:32px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;background:#fff;font-size:14px}
th,td{border-bottom:1px solid #d6d1c9;padding:8px 12px;text-align:left}th{background:#e4dfd7}
.rate{font-weight:700;text-align:center}.good{background:#d5f1e7}.hot{background:#f9ced6}.cold{background:#f4dfc8}
pre{padding:16px;background:#1c1c1c;color:#fff;white-space:pre-wrap;word-break:break-word}
footer{padding:25px 5vw;background:#1c1c1c;color:#ddd;margin-top:36px}
'''

def format_rate(x):
    return f'{100*x:.2f}%'


def format_detail_rate(x):
    return f'{100*x:.4f}%'


def format_seconds(value):
    return '—' if value is None else f'{value:.4f}'


def display_json(value):
    if isinstance(value, float):
        return f'{value:.4f}'
    if isinstance(value, dict):
        return {key: display_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [display_json(item) for item in value]
    return value


def format_json(value):
    return json.dumps(display_json(value), indent=2)


def html_report(report,path):
    before=report['before']; after=report['after']; chosen=report.get('chosen') or {}
    by_after={(r['a'],r['b'],r['range_m'],r['strategy']):r for r in after['rows']}
    rows=[]
    for b in before['rows']:
        a=by_after[(b['a'],b['b'],b['range_m'],b['strategy'])]
        rate=a['a_win_rate']; css='hot' if rate>.6 else 'cold' if rate<.4 else 'good'
        rows.append(f"<tr><td>{html.escape(b['a'])} vs {html.escape(b['b'])}</td><td>{b['range_m']}m</td><td>{html.escape(b['strategy'])}</td>"
                    f"<td class='rate'>{format_detail_rate(b['a_win_rate'])}</td><td class='rate {css}'>{format_detail_rate(rate)}</td>"
                    f"<td>{format_seconds(b['median_ttk_s'])}</td><td>{format_seconds(a['median_ttk_s'])}</td></tr>")
    def stat(label,value):return f'<div class="kpi"><small>{label}</small><strong>{value}</strong></div>'
    verification='PASSED' if report.get('candidate_accepted') else 'NOT VERIFIED'
    before_kpis=before['summary']; after_kpis=after['summary']
    cards=''.join([
        stat('Before: max matchup spread',format_rate(before_kpis['max_matchup_spread'])),
        stat('After: max matchup spread',format_rate(after_kpis['max_matchup_spread'])),
        stat('Before: first-shooter advantage',format_rate(before_kpis['first_shooter_advantage'])),
        stat('After: first-shooter advantage',format_rate(after_kpis['first_shooter_advantage'])),
        stat('Before: mean TTK',f"{before_kpis['mean_ttk_s']:.2f}s"),
        stat('After: mean TTK',f"{after_kpis['mean_ttk_s']:.2f}s"),
        stat('Verification',verification)])
    patch=format_json(chosen.get('changes',{}))
    details=format_json(report['verification'])
    content=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAGENT Balance Report</title><style>{STYLE}</style></head>
    <body><header><div class="tag">THE RAGENTS / DEVHACKS 2026</div><h1>RAGENT</h1><p>Less Rage. More GG. / Agentic balance QA</p></header><main>
    <p class="warn">Results come from synthetic stat-level duels. Not Riot gameplay data and not proof of player retention.</p>
    <p>Agent mode: <strong>{html.escape(report['agent_mode'])}</strong> · Tested {after_kpis['duels']} held-out duels · Candidate status: <strong>{verification}</strong></p>
    <section><h2>Before vs after — five QA metrics</h2><div class="summary">{cards}</div></section>
    <section><h2>Patch + independent verification</h2><p>Patch candidates tested: {report['search_budget']} · Different search and verification seeds.</p>
    <div class="summary"><div><h3>Proposed change</h3><pre>{html.escape(patch)}</pre></div><div><h3>Held-out checks</h3><pre>{html.escape(details)}</pre></div></div></section>
    <section><h2>Per-matchup win rate + time-to-kill</h2><div class="scroll"><table><thead><tr><th>Weapon pairing</th><th>Range</th><th>Bot style</th><th>Before A win%</th><th>After A win%</th><th>Before TTK (s)</th><th>After TTK (s)</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
    <section><h2>Design interpretation</h2><p>A narrow 40–60% policy is applied only to explicitly designated peer matchups. Shotguns and sniper rifles are not required to win half of every range-dependent encounter. Every outcome depends on this simplified aim-and-movement model; human retention must be evaluated separately.</p></section>
    </main><footer>RAGENT · GitHub workflow proof · Synthetic evaluation · Do not present illustration as measured Riot data.</footer></body></html>'''
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);atomic_write(target, content)
    return target


def proposal_html_report(report,path):
    before=report['before']; after=report['after']
    verification=report['verification']
    recommendation=report['recommendation']
    rows=[]
    after_rows={(r['a'],r['b'],r['range_m'],r['strategy']):r for r in after['rows']}
    for old in before['rows']:
        new=after_rows[(old['a'],old['b'],old['range_m'],old['strategy'])]
        rate=new['a_win_rate']
        css='hot' if rate>.6 else 'cold' if rate<.4 else 'good'
        ttk_before=format_seconds(old['median_ttk_s'])
        ttk_after=format_seconds(new['median_ttk_s'])
        rows.append(f"<tr><td>{html.escape(old['a'])} vs {html.escape(old['b'])}</td>"
                    f"<td>{old['range_m']}m</td><td>{html.escape(old['strategy'])}</td>"
                    f"<td>{format_detail_rate(old['a_win_rate'])}</td><td class='rate {css}'>{format_detail_rate(rate)}</td>"
                    f"<td>{ttk_before}</td><td>{ttk_after}</td></tr>")
    def stat(label,value):
        return f'<div class="kpi"><small>{label}</small><strong>{value}</strong></div>'
    before_summary=before['summary']; after_summary=after['summary']
    status='PASSED' if verification['passed'] else 'NEEDS REVIEW'
    cards=''.join([
        stat('Before: max matchup spread',format_rate(before_summary['max_matchup_spread'])),
        stat('After: max matchup spread',format_rate(after_summary['max_matchup_spread'])),
        stat('Before: first-shooter advantage',format_rate(before_summary['first_shooter_advantage'])),
        stat('After: first-shooter advantage',format_rate(after_summary['first_shooter_advantage'])),
        stat('Before: mean TTK',f"{before_summary['mean_ttk_s']:.2f}s"),
        stat('After: mean TTK',f"{after_summary['mean_ttk_s']:.2f}s"),
        stat('Guardrails',status)])
    changes=html.escape(format_json(report['changes']))
    details=html.escape(format_json(verification))
    recommended_changes=html.escape(format_json(recommendation['changes']))
    final_stats=html.escape(format_json(recommendation['final_stats']))
    recommendation_details=html.escape(format_json(recommendation['verification']))
    recommendation_status='PASSED' if recommendation['candidate_accepted'] else 'NEEDS REVIEW'
    explanation = html.escape(format_json(report.get('explanation', {})))
    model_status = html.escape(format_json(report.get('explanation_model', {})))
    content=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAGENT Proposed Change Report</title><style>{STYLE}</style></head>
    <body><header><div class="tag">THE RAGENTS / DEVHACKS 2026</div><h1>RAGENT</h1><p>Proposed change evaluation</p></header><main>
    <p class="warn">Synthetic stat-level simulation only. This is not OpenFire 3D gameplay, Riot gameplay data, or proof of player retention.</p>
    <p>Developer-proposed changes · {report['matches']} paired seeds per matchup · {after_summary['duels']} held-out duels · Guardrails: <strong>{status}</strong></p>
    <section><h2>Before vs after — QA metrics</h2><div class="summary">{cards}</div></section>
    <section><h2>Developer proposal and verification</h2><div class="summary"><div><h3>Proposed stat changes</h3><pre>{changes}</pre></div><div><h3>Training + held-out guardrails</h3><pre>{details}</pre></div></div></section>
    <section><h2>Final agent recommendation</h2><p>Agent mode: <strong>{html.escape(recommendation['agent_mode'])}</strong> · {recommendation['search_budget']} bounded candidates tested · Recommendation: <strong>{recommendation_status}</strong></p><div class="summary"><div><h3>Additional adjustment to developer proposal</h3><pre>{recommended_changes}</pre></div><div><h3>Recommended final stats</h3><pre>{final_stats}</pre></div><div><h3>Recommendation held-out checks</h3><pre>{recommendation_details}</pre></div></div><p>Final stats are the developer's proposed values plus the selected agent adjustment. An empty adjustment means the agent selected no additional change.</p></section>
    <section><h2>Per-matchup win rate and median TTK</h2><div class="scroll"><table><thead><tr><th>Weapon pairing</th><th>Range</th><th>Bot style</th><th>Before A win%</th><th>After A win%</th><th>Before median TTK (s)</th><th>After median TTK (s)</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
    <section><h2>Explanation and model status</h2><pre>{explanation}</pre><pre>{model_status}</pre></section>
    <section><h2>Metric definitions</h2><ul><li>Win rate: A wins plus half of draws, divided by duels, with both starting orders paired for each seed.</li><li>Median TTK: median elimination time among decisive duels in each matchup; summary mean is the mean of matchup medians.</li><li>First-shooter advantage: absolute distance of each matchup's first-shooter win rate from 50%, averaged across matchups.</li><li>Maximum matchup spread: largest range between weapon win rates within any fixed distance and bot style.</li><li>Guardrails check configured neutral-matchup bands, first-shooter threshold, and off-target regression limit.</li></ul></section>
    </main><footer>RAGENT · Developer-proposed change QA · Approximate seeded simulation only.</footer></body></html>'''
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);atomic_write(target, content)
    return target
