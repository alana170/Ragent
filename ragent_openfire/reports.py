"""Human-readable offline report for DevHacks demonstration."""
import html
import json
from pathlib import Path
from .run_store import atomic_write

STYLE='''
*{box-sizing:border-box}body{margin:0;background:#0a0a0a;color:#f5f0e8;font:14px/1.6 Inter,system-ui,sans-serif}header{background:linear-gradient(115deg,#151515,#291a1c);border-bottom:1px solid #363030;padding:42px max(5vw,24px)}header p{color:#aaa39d;margin:6px 0}h1{font-size:38px;margin:4px 0;letter-spacing:-1.5px}h2{font-size:21px;letter-spacing:-.5px;margin:0 0 16px}h3{font-size:13px;margin:0 0 10px}.tag{font:600 10px monospace;letter-spacing:.14em;color:#ff4655;text-transform:uppercase}main{padding:26px 5vw;max-width:1450px;margin:auto}.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.kpi{border:1px solid #363030;background:#151515;border-radius:10px;padding:19px;box-shadow:0 8px 25px #00000000}.kpi small{color:#aaa39d}.kpi strong{font-size:24px;letter-spacing:-.6px;display:block;margin-top:5px}.note{font-size:13px;color:#aaa39d}.warn{color:#f1b0b5;background:#291a1c;border:1px solid #533236;border-radius:10px;padding:14px 17px;font-size:13px}section{margin-top:32px}section>p,li{color:#bcb3ad}.scroll{overflow-x:auto;background:#151515;border:1px solid #363030;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:12px;white-space:nowrap}th,td{border-bottom:1px solid #333;padding:12px;text-align:left}th{background:#202020;color:#aaa39d;font-size:11px}tr:last-child td{border-bottom:0}.rate{font-weight:700}.good{color:#26845d;background:#eaf7f0}.hot{color:#bc5b54;background:#1515150ef}.cold{color:#ad7938;background:#1515155e8}pre{margin:0;padding:16px;border:1px solid #363030;border-radius:10px;background:#151515;color:#e7d5d5;white-space:pre-wrap;word-break:break-word;font:12px/1.7 monospace}footer{padding:25px 5vw;border-top:1px solid #363030;color:#aaa39d;margin-top:36px;font-size:11px}@media print{body{background:#151515}header{padding:20px 0}main{padding:10px 0}.scroll{overflow:visible}section{break-inside:avoid}footer{padding:15px 0}}

header{background:radial-gradient(ellipse at 80% 30%,#38191d,transparent 55%),#111}h1,h2{font-family:'Bebas Neue',Impact,sans-serif;text-transform:uppercase;letter-spacing:.03em}h1{font-size:48px}h2{font-size:28px}.kpi,.scroll,.data-card,.warn,pre{border-radius:0}.good{background:#19302a;color:#a2ddc3}.hot,.cold{background:#392528;color:#ffadb2}@media print{body{background:#fff;color:#111}header{background:#fff;color:#111}.kpi,.data-card,.scroll{background:#fff;color:#111} .data-list dd{color:#111}}
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


def readable_data(value):
    """Render report data as labeled fields instead of serialized JSON."""
    if isinstance(value, dict):
        if not value:
            return '<p class="empty-data">No additional changes.</p>'
        return '<dl class="data-list">' + ''.join(
            f'<div><dt>{html.escape(str(key).replace("_", " ").replace(".", " · ").title())}</dt><dd>{readable_data(item)}</dd></div>'
            for key, item in value.items()) + '</dl>'
    if isinstance(value, (list, tuple)):
        if not value:
            return '<span class="data-empty">None</span>'
        return '<ul class="data-items">' + ''.join(f'<li>{readable_data(item)}</li>' for item in value) + '</ul>'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if value is None:
        return '—'
    if isinstance(value, float):
        return f'{value:.4f}'
    return html.escape(str(value))


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
    changes=readable_data(report['changes'])
    details=readable_data(verification)
    recommended_changes=readable_data(recommendation['changes'])
    final_stats=readable_data(recommendation['final_stats'])
    recommendation_details=readable_data(recommendation['verification'])
    recommendation_status='PASSED' if recommendation['candidate_accepted'] else 'NEEDS REVIEW'
    explanation = html.escape(format_json(report.get('explanation', {})))
    model_status = html.escape(format_json(report.get('explanation_model', {})))
    content=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAGENT Proposed Change Report</title><style>{STYLE}</style></head>
    <body><header><div class="tag">THE RAGENTS / DEVHACKS 2026</div><h1>RAGENT</h1><p>Proposed change evaluation</p></header><main>
    <p class="warn">Synthetic stat-level simulation only. This is not OpenFire 3D gameplay, Riot gameplay data, or proof of player retention.</p>
    <p>Developer-proposed changes · {report['matches']} paired seeds per matchup · {after_summary['duels']} held-out duels · Guardrails: <strong>{status}</strong></p>
    <section><h2>Before vs after — QA metrics</h2><div class="summary">{cards}</div></section>
    <section><h2>Developer proposal and verification</h2><div class="summary"><div><h3>Proposed stat changes</h3><div class="data-card">{changes}</div></div><div><h3>Training + held-out guardrails</h3><div class="data-card">{details}</div></div></div></section>
    <section><h2>Final agent recommendation</h2><p>Agent mode: <strong>{html.escape(recommendation['agent_mode'])}</strong> · {recommendation['search_budget']} bounded candidates tested · Recommendation: <strong>{recommendation_status}</strong></p><div class="summary"><div><h3>Additional adjustment to developer proposal</h3><div class="data-card">{recommended_changes}</div></div><div><h3>Recommended final stats</h3><div class="data-card">{final_stats}</div></div><div><h3>Recommendation held-out checks</h3><div class="data-card">{recommendation_details}</div></div></div><p>Final stats are the developer's proposed values plus the selected agent adjustment. An empty adjustment means the agent selected no additional change.</p></section>
    <section><h2>Per-matchup win rate and median TTK</h2><div class="scroll"><table><thead><tr><th>Weapon pairing</th><th>Range</th><th>Bot style</th><th>Before A win%</th><th>After A win%</th><th>Before median TTK (s)</th><th>After median TTK (s)</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
    <section><h2>Explanation and model status</h2><pre>{explanation}</pre><pre>{model_status}</pre></section>
    <section><h2>Metric definitions</h2><ul><li>Win rate: A wins plus half of draws, divided by duels, with both starting orders paired for each seed.</li><li>Median TTK: median elimination time among decisive duels in each matchup; summary mean is the mean of matchup medians.</li><li>First-shooter advantage: absolute distance of each matchup's first-shooter win rate from 50%, averaged across matchups.</li><li>Maximum matchup spread: largest range between weapon win rates within any fixed distance and bot style.</li><li>Guardrails check configured neutral-matchup bands, first-shooter threshold, and off-target regression limit.</li></ul></section>
    </main><footer>RAGENT · Developer-proposed change QA · Approximate seeded simulation only.</footer></body></html>'''
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);atomic_write(target, content)
    return target
