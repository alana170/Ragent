import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { api, normalizeReplays } from './api.js';
import DuelReplay from './replay.jsx';
import {
  Activity, ArrowDownToLine, ArrowRight, Check, CheckCircle2, ChevronDown, ChevronRight,
  CircleHelp, Clock3, Crosshair, FileBarChart2, FlaskConical, Gauge, LoaderCircle,
  Radio, RotateCcw, ShieldAlert, ShieldCheck, Sparkles, Swords, Target, Terminal,
  TrendingUp, WandSparkles, XCircle,
} from 'lucide-react';

const cn = (...parts) => parts.filter(Boolean).join(' ');
const formatPercent = value => `${(value * 100).toFixed(2)}%`;
const formatDetailPercent = value => `${(value * 100).toFixed(4)}%`;
const formatSeconds = value => value == null ? '—' : `${value.toFixed(4)}s`;
const displayValue = value => typeof value === 'number' && !Number.isInteger(value) ? value.toFixed(4) : String(value);
const prettify = value => value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());

function Panel({ children, className = '', ...props }) {
  return <section className={cn('panel', className)} {...props}>{children}</section>;
}

function SectionHeading({ eyebrow, title, description, action }) {
  return <div className="section-heading">
    <div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2>{description && <p>{description}</p>}</div>
    {action}
  </div>;
}

function MetricTile({ icon: Icon, label, value, note, tone = 'violet' }) {
  return <div className="metric-tile">
    <div className={`metric-icon ${tone}`}><Icon size={17} strokeWidth={2} /></div>
    <div className="metric-label">{label}</div><div className="metric-value">{value}</div>
    {note && <div className="metric-note">{note}</div>}
  </div>;
}

function StatusPill({ passed, children }) {
  return <span className={cn('status-pill', passed ? 'passed' : 'review')}>
    {passed ? <CheckCircle2 size={14} /> : <ShieldAlert size={14} />}{children}
  </span>;
}

function JsonValue({ value }) {
  if (typeof value === 'number') return <span className="json-number">{displayValue(value)}</span>;
  if (typeof value === 'boolean') return <span className={cn('json-bool', value ? 'true' : 'false')}>{String(value)}</span>;
  if (value === null) return <span className="json-null">null</span>;
  if (typeof value === 'string') return <span className="json-string">{value}</span>;
  return null;
}

function JsonTree({ data, depth = 0 }) {
  const entries = Array.isArray(data) ? data.map((value, index) => [String(index), value]) : Object.entries(data || {});
  return <div className={cn('json-tree', depth > 0 && 'json-nested')}>
    {entries.map(([key, value]) => {
      const expandable = value && typeof value === 'object';
      return <JsonTreeRow key={`${key}-${depth}`} label={key} value={value} expandable={expandable} depth={depth} />;
    })}
  </div>;
}

function JsonTreeRow({ label, value, expandable, depth }) {
  const [open, setOpen] = useState(depth < 1);
  const object = value && typeof value === 'object';
  return <div className="json-row">
    <div className={cn('json-line', expandable && 'json-toggle')} role={expandable ? "button" : undefined} tabIndex={expandable ? 0 : undefined} aria-expanded={expandable ? open : undefined} onKeyDown={event => { if (expandable && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); setOpen(!open); } }} onClick={() => expandable && setOpen(!open)}>
      {expandable ? (open ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span className="json-spacer" />}
      <span className="json-key">{prettify(label)}</span>
      {object ? <span className="json-count">{Array.isArray(value) ? `${value.length} items` : `${Object.keys(value).length} stats`}</span> : <JsonValue value={value} />}
    </div>
    {expandable && open && <JsonTree data={value} depth={depth + 1} />}
  </div>;
}

function JsonCard({ title, subtitle, icon: Icon = FileBarChart2, data, accent = 'violet' }) {
  return <div className={`json-card ${accent}`}>
    <div className="json-card-head"><span className="json-card-icon"><Icon size={16} /></span><div><h4>{title}</h4>{subtitle && <p>{subtitle}</p>}</div></div>
    <JsonTree data={data} />
  </div>;
}

function MatchupTable({ before, after }) {
  const [range, setRange] = useState('all');
  const [strategy, setStrategy] = useState('all');
  const [expanded, setExpanded] = useState(false);
  const afterRows = useMemo(() => new Map(after.rows.map(row => [`${row.a}|${row.b}|${row.range_m}|${row.strategy}`, row])), [after]);
  const rows = before.rows.map(old => ({ old, next: afterRows.get(`${old.a}|${old.b}|${old.range_m}|${old.strategy}`) }))
    .filter(({ old }) => (range === 'all' || String(old.range_m) === range) && (strategy === 'all' || old.strategy === strategy));
  const visible = expanded ? rows : rows.slice(0, 8);
  return <Panel className="table-panel">
    <SectionHeading eyebrow="Scenario breakdown" title="Matchup results" description={`${rows.length} scenarios · Detailed values rounded to four decimal places`}
      action={<div className="filters">
        <select value={range} onChange={event => setRange(event.target.value)} aria-label="Filter by range">
          <option value="all">All ranges</option>{[...new Set(before.rows.map(row => row.range_m))].map(item => <option key={item} value={item}>{item}m</option>)}
        </select>
        <select value={strategy} onChange={event => setStrategy(event.target.value)} aria-label="Filter by style">
          <option value="all">All styles</option>{[...new Set(before.rows.map(row => row.strategy))].map(item => <option key={item} value={item}>{prettify(item)}</option>)}
        </select>
      </div>} />
    <div className="table-scroll"><table className="matchup-table">
      <thead><tr><th>Weapon matchup</th><th>Range</th><th>Playstyle</th><th>Baseline win rate</th><th>Proposed win rate</th><th>Baseline TTK</th><th>Proposed TTK</th></tr></thead>
      <tbody>{visible.map(({ old, next }) => {
        if (!next) return null;
        const rate = next.a_win_rate, balance = rate > .6 ? 'high' : rate < .4 ? 'low' : 'balanced';
        return <tr key={`${old.a}-${old.b}-${old.range_m}-${old.strategy}`}>
          <td><span className="matchup-name">{prettify(old.a)} <span>vs</span> {prettify(old.b)}</span></td>
          <td>{old.range_m}<small>m</small></td><td><span className="style-chip">{prettify(old.strategy)}</span></td>
          <td className="numeric">{formatDetailPercent(old.a_win_rate)}</td>
          <td className="numeric"><span className={`rate-chip ${balance}`}>{formatDetailPercent(rate)}</span></td>
          <td className="numeric muted-cell">{formatSeconds(old.median_ttk_s)}</td><td className="numeric">{formatSeconds(next.median_ttk_s)}</td>
        </tr>;
      })}</tbody>
    </table></div>
    {rows.length > 8 && <button className="text-button expand-table" onClick={() => setExpanded(!expanded)}>
      {expanded ? 'Show fewer scenarios' : `View all ${rows.length} scenarios`}<ChevronDown className={expanded ? 'rotate' : ''} size={15} />
    </button>}
  </Panel>;
}

function RunLog({ events, running }) {
  const bottom = useRef(null);
  useEffect(() => {
    if (bottom.current) bottom.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [events.length]);
  const recent = events.slice(-120);
  return <Panel className="log-panel">
    <div className="log-heading"><div><div className="eyebrow">SIMULATION CONSOLE</div><h3>Live run log</h3></div>
      <span className={cn('live-dot', running && 'active')}>{running && <i />} {running ? 'LIVE' : 'READY'}</span>
    </div>
    <div className="terminal"><div className="terminal-bar"><span /><span /><span /><b><Terminal size={12} /> ragent · local</b></div>
      <div className="terminal-lines">{recent.map((event, index) => <div className="terminal-line" key={`${event.time}-${index}`}>
        <span className="terminal-time">{new Date(event.time).toLocaleTimeString()}</span><span>{event.message}</span>
      </div>)}{running && <div className="terminal-cursor">▍</div>}<div ref={bottom} /></div>
    </div>
  </Panel>;
}

function WeaponArt({ asset, name }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [asset?.url]);
  return asset?.url && !failed ? <img className="weapon-art" src={asset.url} alt={`${prettify(name)} weapon artwork`} onError={() => setFailed(true)} /> : <div className="asset-missing">Weapon artwork unavailable</div>;
}
function EvidencePanel({ run, recorded }) {
  const explanation = run.explanation || run.result?.explanation || run.recommendation?.explanation;
  const model = run.result?.explanation_model || run.recommendation?.explanation_model;
  const status = model?.status === 'live' || model?.status === 'success' ? `${recorded ? 'Recorded Gemini run' : 'Gemini live'}${model.model ? ` · ${model.model}` : ''}` : model ? `Deterministic fallback${model.reason ? ` · ${model.reason}` : ''}` : 'Explanation status unavailable';
  return <Panel className="evidence-panel"><SectionHeading eyebrow="EVIDENCE & INTERPRETATION" title="What the results mean" action={<span className="model-status">{status}</span>} />
    {explanation ? <div className="evidence-copy"><p>{explanation.summary}</p><p><strong>Tradeoffs</strong> {explanation.tradeoffs}</p><p><strong>Limitations</strong> {explanation.limitations}</p>{explanation.evidence_ids?.length > 0 && <small>Evidence: {explanation.evidence_ids.join(' · ')}</small>}</div> : <p className="muted">No grounded explanation was supplied for this run.</p>}
  </Panel>;
}
function CandidatePanel({ recommendation }) {
  const candidates = recommendation?.candidates;
  if (!Array.isArray(candidates)) return <Panel className="empty-state"><h3>Candidate inspection unavailable</h3><p>This run does not contain candidate records.</p></Panel>;
  return <Panel className="candidate-panel"><SectionHeading eyebrow="SEARCH AUDIT" title="Candidates tested" description="Sources and outcomes are recorded by the search; only verified candidates can become recommendations." />
    {candidates.length ? <div className="table-scroll"><table className="matchup-table"><thead><tr><th>Candidate</th><th>Source</th><th>Changes</th><th>Outcome</th></tr></thead><tbody>{candidates.map((candidate, index) => <tr key={candidate.id || index}><td>{candidate.id || `Candidate ${index + 1}`}</td><td>{candidate.source || 'Unavailable'}</td><td><code>{JSON.stringify(candidate.changes || {})}</code></td><td>{candidate.eligible === false ? 'Ineligible' : candidate.eligible === true ? 'Eligible' : 'See details'}{candidate.score != null && <small className="candidate-detail">Search score: {candidate.score}</small>}{candidate.metrics?.summary && <small className="candidate-detail">Mean TTK: {candidate.metrics.summary.mean_ttk_s?.toFixed(2) ?? '—'}s · Max spread: {candidate.metrics.summary.max_matchup_spread != null ? formatPercent(candidate.metrics.summary.max_matchup_spread) : '—'}</small>}{candidate.rationale && <small className="candidate-detail">{candidate.rationale}</small>}{candidate.error && <small className="candidate-detail">{candidate.error}</small>}{['search_violations', 'search_regressions', 'proposal_search_regressions'].flatMap(key => (candidate[key] || []).map(item => typeof item === 'string' ? item : JSON.stringify(item))).map((reason, i) => <small className="candidate-detail" key={i}>{typeof reason === 'string' ? reason : JSON.stringify(reason)}</small>)}</td></tr>)}</tbody></table></div> : <p>No candidates were recorded.</p>}
  </Panel>;
}
function App() {
  const [config, setConfig] = useState(null);
  const [form, setForm] = useState({});
  const [matches, setMatches] = useState(24);
  const [events, setEvents] = useState([]);
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('proposal');
  const [profile, setProfile] = useState('valorant');
  const [savedRuns, setSavedRuns] = useState([]);
  const [content, setContent] = useState(null);
  const [savedError, setSavedError] = useState('');
  const [recorded, setRecorded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setConfig(null); setError('');
    api.config(profile).then(data => {
      if (cancelled) return;
      setConfig(data); setMatches(data.default_matches);
      const defaults = {};
      Object.entries(data.allowed_parameters).forEach(([path]) => {
        const [weapon, field] = path.split('.');
        defaults[weapon] = { ...defaults[weapon], [field]: data.weapons[weapon][field] };
      });
      if (data.profile === 'valorant' && defaults.spectre && 'damage' in defaults.spectre) {
        defaults.spectre.damage = 27;
      } else if (data.profile === 'openfire' && defaults.smg && 'damage' in defaults.smg) {
        defaults.smg.damage = 13;
      }
      setForm(defaults);
    }).catch(reason => { if (!cancelled) setError(reason.message); });
    return () => { cancelled = true; };
  }, [profile]);
  const refreshRuns = () => api.runs().then(items => { setSavedRuns(items); setSavedError(''); }).catch(() => setSavedError('Saved runs are unavailable on this server.'));
  useEffect(() => { refreshRuns(); api.content().then(setContent).catch(() => setContent(null)); }, []);
  const openRun = async id => {
    if (!id) return;
    try {
      const selected = await api.run(id);
      setProfile(selected.profile || 'openfire'); setRun(selected); setEvents(selected.events || []); setError(''); setRecorded(true);
      if (selected.status !== 'complete' && selected.status !== 'failed' && selected.status !== 'interrupted') { setBusy(true); await pollRun(id); }
    } catch (reason) { setBusy(false); setError(reason.message); }
  };

  const proposals = useMemo(() => Object.entries(form).flatMap(([weapon, stats]) =>
    Object.entries(stats).filter(([field, value]) => value !== config?.weapons?.[weapon]?.[field])
      .map(([field, value]) => ({ weapon, field, value, baseline: config?.weapons?.[weapon]?.[field] }))), [form, config]);

  const pollRun = async runId => {
    while (true) {
      const state = await api.run(runId);
      setEvents(Array.isArray(state.events) ? state.events : []);
      setRun(state);
      if (['complete', 'failed', 'interrupted'].includes(state.status)) {
        refreshRuns();
        setBusy(false);
        if (state.status !== 'complete') throw new Error(state.error || 'Simulation failed');
        return;
      }
      await new Promise(resolve => window.setTimeout(resolve, 300));
    }
  };

  const updateValue = (weapon, field, value) => setForm(current => ({
    ...current, [weapon]: { ...current[weapon], [field]: value === '' ? '' : Number(value) },
  }));
  const reset = () => {
    if (!config) return;
    const defaults = {};
    Object.entries(config.allowed_parameters).forEach(([path]) => {
      const [weapon, field] = path.split('.');
      defaults[weapon] = { ...defaults[weapon], [field]: config.weapons[weapon][field] };
    });
    setForm(defaults); setRun(null); setEvents([]); setError(''); setRecorded(false);
  };
  const launchRun = async event => {
    event.preventDefault(); setError('');
    if (!proposals.length) { setError('Adjust at least one stat before starting a simulation.'); return; }
    if (proposals.some(item => item.value === '' || !Number.isFinite(item.value))) { setError('Enter a valid number for every edited stat.'); return; }
    const changes = {};
    proposals.forEach(({ weapon, field, value }) => { changes[weapon] = { ...changes[weapon], [field]: value }; });
    setBusy(true); setEvents([]); setRun(null); setRecorded(false);
    try {
      const data = await api.start({ changes, matches: Number(matches), ...(profile ? { profile } : {}) });
      setRun(data); setEvents(data.events || []);
      await pollRun(data.id);
    } catch (reason) { setError(reason.message); setBusy(false); }
  };

  const recommendation = run?.recommendation;
  const replayTraces = useMemo(() => {
    const traces = normalizeReplays(run?.replays || run?.result?.replays);
    if (!traces) return {};
    if (!run?.recommendation?.candidate_accepted) delete traces.recommendation;
    return traces;
  }, [run]);
  const summary = run?.summary;
  const recSummary = recommendation?.summary;
  const options = useMemo(() => config ? Object.keys(config.allowed_parameters).reduce((acc, path) => {
    const [weapon, field] = path.split('.'); acc[weapon] = [...(acc[weapon] || []), { field, bounds: config.allowed_parameters[path] }]; return acc;
  }, {}) : {}, [config]);

  if (!config) return <div className="loading-screen"><div className="brand-mark"><Crosshair size={24} /></div><p>{error || 'Preparing the balance lab…'}</p>{error && <span>{error}</span>}</div>;

  return <div className="app-shell">
    <header className="topbar"><a href="/" className="brand"><span className="brand-mark"><Crosshair size={21} /></span><span>RAGENT<span className="brand-dot">.</span></span></a>
      <div className="topbar-right"><span className="env-label"><span className="env-dot" /> LOCAL DEV ENVIRONMENT</span><span className="topbar-divider" /><span className="avatar">QA</span></div>
    </header>
    <main className="workspace">
      <div className="page-intro"><div><div className="eyebrow">GAME BALANCE QUALITY ASSURANCE</div><h1>Balance Lab</h1><p>Explore a proposed change, test the ripple effects, and leave with a verified recommendation.</p></div>
        <div className="run-badge"><FlaskConical size={16} /><span>Stat-level simulation</span></div>
      </div>
      <div className="context-bar"><label>Content profile <select value={profile || config.profile || ''} disabled={busy} onChange={event => { setRun(null); setEvents([]); setProfile(event.target.value); }}>
        {(config.profiles || [config.profile || 'openfire']).map(item => <option key={item} value={item}>{prettify(item)}</option>)}
      </select></label><label>Saved runs <select value={run?.id || ''} disabled={busy} onChange={event => openRun(event.target.value)}><option value="">Select a run</option>{savedRuns.map(item => <option key={item.id} value={item.id}>{item.profile || 'openfire'} · {item.status} · {item.id.slice(0, 8)}</option>)}</select></label><span>{savedError || (content && (profile || config.profile) === 'valorant' ? `${content.source} · ${content.version || 'version unavailable'} · retrieved ${content.retrieved_at || 'unknown'}` : 'Simulation profile and source data supplied by the server.')}</span></div>
      {config.source && <details className="source-details"><summary>Profile source and model assumptions</summary><p>{config.source.source || 'Source unavailable'} {config.source.version && `· ${config.source.version}`} {config.source.retrieved_at && `· retrieved ${config.source.retrieved_at}`}</p>{config.source.damage_context && <p>Damage context: {config.source.damage_context}</p>}{config.source.assumptions?.length > 0 && <ul>{config.source.assumptions.map(item => <li key={item}>{item}</li>)}</ul>}</details>}
      <div className="scope-banner"><div className="scope-icon"><CircleHelp size={17} /></div><p><strong>Model scope</strong><span>Seeded weapon-stat duels approximate aim, cadence, damage, reload, range, and movement. This is not a full 3D OpenFire match or player-retention measurement.</span></p><span className="scope-detail">{Object.keys(config.weapons).length} weapons <i /> {config.ranges.join(' / ')}m <i /> {config.strategies.length} playstyles</span></div>

      <div className="dashboard-grid">
        <div className="main-column">
          <Panel className="proposal-panel">
            <SectionHeading eyebrow="01 · PROPOSE A CHANGE" title="What are you tuning?" description="Edit the values you want to test. We’ll compare against today’s baseline and check a separate set of seeds." />
            <form onSubmit={launchRun}>
              <div className="weapon-grid">{Object.entries(options).map(([weapon, fields]) =>
                <div className="weapon-card" key={weapon}>
                  <div className="weapon-card-head"><div className="weapon-icon"><Swords size={17} /></div><div><h3>{prettify(weapon)}</h3><span>{fields.length} tunable {fields.length === 1 ? 'stat' : 'stats'}</span></div></div>
                  {(profile || config.profile) === 'valorant' && <WeaponArt asset={content?.assets?.[weapon]} name={weapon} />}
                  {fields.map(({ field, bounds }) => {
                    const changed = form[weapon]?.[field] !== config.weapons[weapon][field];
                    return <label className={cn('stat-input', changed && 'is-changed')} key={field}>
                      <span className="stat-label">{prettify(field)}<small>Current {displayValue(config.weapons[weapon][field])}</small></span>
                      <span className="input-wrap"><input type="number" step={Number.isInteger(config.weapons[weapon][field]) ? '1' : 'any'} min={bounds[0]} max={bounds[1]}
                        value={form[weapon]?.[field] ?? ''} onChange={event => updateValue(weapon, field, event.target.value)} aria-label={`${prettify(weapon)} ${prettify(field)}`} />
                        {changed && <span className="changed-mark"><Check size={12} /></span>}</span>
                      <small className="stat-bounds">Allowed {bounds[0]}–{bounds[1]}</small>
                    </label>;
                  })}
                </div>
              )}</div>
              <div className="form-footer"><label className="seed-control"><span>Seeds per scenario</span><input type="number" min="1" max="100" value={matches} onChange={event => setMatches(event.target.value === '' ? '' : Number(event.target.value))} /><small>Both starting-player orders</small></label>
                <div className="form-actions">{(profile || config.profile) === 'valorant' && <button type="button" className="button button-quiet" disabled={busy} onClick={() => { reset(); updateValue('spectre', 'damage', 27); }}>Load demo preset</button>}<button type="button" className="button button-quiet" onClick={reset}><RotateCcw size={15} /> Reset</button>
                  <button type="submit" className="button button-primary" disabled={busy}>{busy ? <><LoaderCircle className="spin" size={16} /> Running…</> : <><Sparkles size={16} /> Run balance check <ArrowRight size={15} /></>}</button></div>
              </div>
            </form>
            {error && <div className="form-error"><XCircle size={16} />{error}</div>}
          </Panel>

          {run?.status === 'complete' && <div className="results-stack">
            {recorded && <Panel className="empty-state"><strong>Recorded run</strong><p>Reopened saved results; these are not a new live simulation or model call.</p></Panel>}
            <div className={cn('result-banner', run.passed ? 'success' : 'caution')}>
              <div className="result-banner-icon">{run.passed ? <ShieldCheck size={20} /> : <ShieldAlert size={20} />}</div>
              <div><strong>{run.passed ? 'Proposed change passed configured guardrails' : 'Proposed change needs a designer’s review'}</strong>
                <p>{run.passed ? 'The result held up on independent seeds. Review matchup detail before accepting.' : 'At least one configured fairness or regression check did not pass.'}</p></div>
              <StatusPill passed={run.passed}>{run.passed ? 'VERIFIED' : 'REVIEW'}</StatusPill>
            </div>
            <div className="results-title"><div><div className="eyebrow">02 · THE RESULTS</div><h2>Impact at a glance</h2></div>
              <a className="button button-quiet download-link" href={run.json_url}><ArrowDownToLine size={15} /> Download run data</a></div>
            <div className="metric-grid">
              <MetricTile icon={Target} label="Mean matchup TTK" value={`${summary.mean_ttk_s.toFixed(2)}s`} note={`Baseline ${run.before.summary.mean_ttk_s.toFixed(2)}s`} />
              <MetricTile icon={Activity} label="First-shooter edge" value={formatPercent(summary.first_shooter_advantage)} note={`Baseline ${formatPercent(run.before.summary.first_shooter_advantage)}`} tone="blue" />
              <MetricTile icon={Gauge} label="Maximum matchup spread" value={formatPercent(summary.max_matchup_spread)} note={`Baseline ${formatPercent(run.before.summary.max_matchup_spread)}`} tone="orange" />
              <MetricTile icon={ShieldCheck} label="Training + held-out" value={run.passed ? 'Passed' : 'Needs review'} note="Configured guardrails" tone={run.passed ? 'green' : 'orange'} />
            </div>
            <Panel className="candidate-panel"><SectionHeading eyebrow="CHANGESET" title="Values across the decision" description="Original profile values, submitted values, and verified final values." /><div className="table-scroll"><table className="matchup-table"><thead><tr><th>Parameter</th><th>Original baseline</th><th>Developer proposal</th><th>Final recommendation</th></tr></thead><tbody>{Object.entries(recommendation?.final_stats || run.changes || {}).flatMap(([weapon, fields]) => Object.keys(fields).map(field => { const baseline = run.profile_source?.weapons?.[weapon]?.[field] ?? run.result?.profile_source?.weapons?.[weapon]?.[field]; const value = run.changes?.[weapon]?.[field] ?? baseline; return <tr key={`${weapon}.${field}`}><td>{prettify(weapon)} · {prettify(field)}</td><td>{baseline ?? 'Unavailable'}</td><td>{value ?? 'Unavailable'}</td><td>{recommendation?.candidate_accepted ? (recommendation.final_stats?.[weapon]?.[field] ?? value) : 'No verified recommendation'}</td></tr>; }))}</tbody></table></div></Panel>
            <DuelReplay traces={replayTraces} assets={content?.assets || {}} />
            <EvidencePanel run={run} recorded={recorded} />
            <CandidatePanel recommendation={recommendation} />
            <Panel className="report-panel">
              <div className="report-heading"><div><div className="eyebrow">DEVELOPER REPORT</div><h3>Proposal and verification</h3><p>Readable summary of the edit, guardrails, and independent retest.</p></div><a href={run.report_url} target="_blank" rel="noreferrer" className="button button-outline"><FileBarChart2 size={15} /> Open full report <ArrowRight size={14} /></a></div>
              <div className="tab-list"><button className={activeTab === 'proposal' ? 'active' : ''} onClick={() => setActiveTab('proposal')}>Your proposal</button><button className={activeTab === 'checks' ? 'active' : ''} onClick={() => setActiveTab('checks')}>Verification checks</button></div>
              {activeTab === 'proposal' ? <div className="json-cards">
                <JsonCard title="Developer changes" subtitle="Your submitted values" icon={WandSparkles} data={run.changes} />
                <JsonCard title="Guardrail outcome" subtitle="Training and independent test seeds" icon={ShieldCheck} data={run.verification} accent="blue" />
              </div> : <div className="check-list">
                {['training', 'held_out'].map(key => {
                  const check = run.verification[key], passed = !check.violations.length && !check.regressions.length;
                  return <div className="check-row" key={key}><span className={cn('check-icon', passed ? 'good' : 'bad')}>{passed ? <Check size={15} /> : <XCircle size={15} />}</span>
                    <div><strong>{key === 'held_out' ? 'Independent held-out seeds' : 'Search/training seeds'}</strong><span>{check.seed_count} seeds · {check.violations.length} balance violations · {check.regressions.length} regressions</span></div><StatusPill passed={passed}>{passed ? 'PASSED' : 'REVIEW'}</StatusPill></div>;
                })}
              </div>}
            </Panel>
            {recommendation?.candidate_accepted && recSummary && <Panel className="recommendation-panel">
              <div className="recommendation-top"><div className="recommendation-spark"><Sparkles size={19} /></div>
                <div className="recommendation-heading"><div className="eyebrow">03 · AGENT RECOMMENDATION</div><h2>Best next move</h2><p>The local agent searched bounded adjustments around your proposed stats and tested the selected combination on fresh seeds.</p></div>
                <StatusPill passed={recommendation.candidate_accepted}>{recommendation.candidate_accepted ? 'HELD-OUT PASSED' : 'NEEDS REVIEW'}</StatusPill>
              </div>
              <div className="recommendation-callout"><Sparkles size={15} /><span>{recommendation.rationale || 'The best tested option is to keep your proposed values without an additional adjustment.'}</span></div>
              <div className="recommendation-metrics"><MetricTile icon={Target} label="Recommended mean TTK" value={`${recSummary.mean_ttk_s.toFixed(2)}s`} note={`Your proposal ${recommendation.baseline_summary.mean_ttk_s.toFixed(2)}s`} tone="green" />
                <MetricTile icon={TrendingUp} label="First-shooter edge" value={formatPercent(recSummary.first_shooter_advantage)} note={`Your proposal ${formatPercent(recommendation.baseline_summary.first_shooter_advantage)}`} tone="blue" />
                <MetricTile icon={Gauge} label="Maximum spread" value={formatPercent(recSummary.max_matchup_spread)} note={`Your proposal ${formatPercent(recommendation.baseline_summary.max_matchup_spread)}`} tone="orange" />
              </div>
              <div className="json-cards">
                <JsonCard title="Suggested adjustment" subtitle={`${recommendation.search_budget} bounded combinations evaluated`} icon={WandSparkles} data={recommendation.changes} />
                <JsonCard title="Recommended final stats" subtitle="Your proposal plus the agent’s adjustment" icon={Crosshair} data={recommendation.final_stats} accent="green" />
              </div>
              <div className="recommendation-footer"><span><Radio size={14} /> {recommendation.agent_mode || 'Search mode unavailable'}</span>
                <span>{recommendation.verification?.heldout_seed_count ?? '—'} verification seeds</span></div>
            </Panel>}
            {recommendation && !recommendation.candidate_accepted && <Panel className="empty-state"><h3>No verified recommendation</h3><p>The tested candidates did not produce a verified final recommendation. Inspect the candidate evidence and proposal checks before deciding what to test next.</p></Panel>}
            {run.before && run.after && <MatchupTable before={run.before} after={run.after} />}
          </div>}
        </div>
        <aside className="side-column"><RunLog events={events} running={busy} />
          <Panel className="method-panel"><div className="method-icon"><FlaskConical size={17} /></div><h3>How to read this</h3>
            <ul><li><strong>Summary tiles</strong><span>Rounded to two decimal places for a quick scan.</span></li>
              <li><strong>Matchup details</strong><span>Four decimal places preserve precision on smaller differences.</span></li>
              <li><strong>Recommendation</strong><span>A passing result is not a guarantee of fun or player retention.</span></li></ul>
            <div className="method-foot"><Clock3 size={14} /> Seeded, repeatable runs</div>
          </Panel>
        </aside>
      </div>
      <footer className="page-footer"><span><Crosshair size={15} /> RAGENT <i /> DevHacks 2026</span><span>For developer QA · Synthetic simulation only</span></footer>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
