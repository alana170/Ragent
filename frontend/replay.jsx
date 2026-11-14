import React, { useEffect, useRef, useState } from 'react';
import replayState from './replay-state.cjs';

const { reconstruct, duration, comparable } = replayState;
const labels = { baseline: 'Original baseline', proposal: 'Developer proposal', recommendation: 'Final recommendation' };
const title = value => String(value || 'Unknown').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());

function ReplayCanvas({ trace, time, assets, label, reducedMotion }) {
  const canvas = useRef(null);
  const [images, setImages] = useState({});
  useEffect(() => {
    let cancelled = false;
    const loaded = {};
    const entries = [trace.a, trace.b].map(key => [key, assets?.[key]]).concat(['a', 'b'].map(side => [`portrait_${side}`, assets?.portraits?.[side]])).filter(([, value]) => value);
    Promise.all(entries.map(([key, value]) => new Promise(resolve => {
      const img = new Image();
      img.onload = () => { loaded[key] = img; resolve(); };
      img.onerror = resolve;
      img.src = typeof value === 'string' ? value : value.url || value.image || value.displayIcon || '';
    }))).then(() => { if (!cancelled) setImages(loaded); });
    return () => { cancelled = true; };
  }, [trace.a, trace.b, assets]);
  const state = reconstruct(trace, Math.min(time, duration(trace)));
  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx) return;
    const w = 720, h = 280;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#121d25'; ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#263640'; ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 48) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x - 90, h); ctx.stroke(); }
    ctx.fillStyle = '#192a34'; ctx.fillRect(0, 206, w, 74);
    ctx.strokeStyle = '#3b505b'; ctx.beginPath(); ctx.moveTo(0, 206); ctx.lineTo(w, 206); ctx.stroke();
    ctx.textAlign = 'center'; ctx.fillStyle = '#9aabb4'; ctx.font = 'bold 11px sans-serif';
    ctx.fillText(`${state.distance == null ? '—' : state.distance.toFixed(1) + ' M'}  /  RECORDED RANGE`, w / 2, 37);
    ['a', 'b'].forEach((side, index) => {
      const x = index ? 566 : 154, player = state[side], weapon = trace[side], img = images[weapon];
      const color = index ? '#ff6b72' : '#80d8c9';
      ctx.save(); ctx.globalAlpha = player.eliminated ? .35 : 1;
      ctx.fillStyle = '#2d424d'; ctx.beginPath(); ctx.arc(x, 105, 29, 0, Math.PI * 2); ctx.fill();
      const portrait = images[`portrait_${side}`];
      if (portrait) { ctx.save(); ctx.beginPath(); ctx.arc(x, 105, 29, 0, Math.PI * 2); ctx.clip(); ctx.drawImage(portrait, x - 29, 76, 58, 58); ctx.restore(); }
      else { ctx.fillStyle = color; ctx.font = 'bold 19px sans-serif'; ctx.fillText(side.toUpperCase(), x, 112); }
      ctx.fillStyle = '#344a55'; ctx.beginPath(); ctx.moveTo(x - 48, 201); ctx.lineTo(x - 36, 166); ctx.lineTo(x + 36, 166); ctx.lineTo(x + 48, 201); ctx.fill();
      if (img) {
        const ratio = Math.min(150 / img.width, 55 / img.height);
        const iw = img.width * ratio, ih = img.height * ratio;
        ctx.drawImage(img, x - iw / 2, 141 - ih / 2, iw, ih);
      } else {
        ctx.fillStyle = '#d8e1e2'; ctx.font = 'bold 12px sans-serif'; ctx.fillText(title(weapon), x, 151);
      }
      ctx.restore();
      if (!reducedMotion && player.lastShot != null && time - player.lastShot < .12) {
        ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.beginPath();
        ctx.moveTo(index ? x - 65 : x + 65, 145); ctx.lineTo(index ? 260 : 460, 145); ctx.stroke();
      }
      if (player.lastDamage && time - player.lastDamage.at < .55 && !reducedMotion) {
        ctx.fillStyle = '#ff7a7f'; ctx.font = 'bold 17px sans-serif'; ctx.fillText(`−${Math.round(player.lastDamage.amount)}`, x, 87);
      }
      ctx.fillStyle = '#e7efef'; ctx.font = 'bold 13px sans-serif'; ctx.fillText(title(weapon), x, 231);
      ctx.fillStyle = '#647984'; ctx.fillRect(x - 76, 241, 152, 5);
      ctx.fillStyle = color; ctx.fillRect(x - 76, 241, 152 * Math.max(0, Math.min(100, player.hp)) / 100, 5);
      ctx.fillStyle = '#c7d3d5'; ctx.font = '11px sans-serif';
      ctx.fillText(`${Math.ceil(player.hp)} HP  ·  ${player.eliminated ? 'ELIMINATED' : player.reloading ? 'RELOADING' : player.ammo == null ? 'AMMO NOT RECORDED' : player.ammo + ' ROUNDS'}`, x, 264);
    });
    if (state.ended) {
      ctx.fillStyle = '#e5eded'; ctx.font = 'bold 12px sans-serif';
      ctx.fillText(state.winner === 'draw' ? 'DRAW' : `${title(trace[state.winner])} WINS`, w / 2, 192);
    }
  }, [trace, time, images, reducedMotion, state.distance, state.winner, state.ended]);
  return <div className="duel-stage"><div className="duel-stage-label">{label}</div><canvas ref={canvas} width="720" height="280" role="img" aria-label={`${label}: ${title(trace.a)} ${Math.ceil(state.a.hp)} health, ${title(trace.b)} ${Math.ceil(state.b.hp)} health${state.ended ? `, ${state.winner === 'draw' ? 'draw' : title(trace[state.winner]) + ' wins'}` : ''}`} /></div>;
}

export default function DuelReplay({ traces = {}, assets = {} }) {
  const baseline = traces.baseline;
  const available = ['proposal', 'recommendation'].filter(key => traces[key]);
  const [selected, setSelected] = useState(available[0] || 'proposal');
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [reduced, setReduced] = useState(() => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
  const active = available.includes(selected) ? selected : available[0];
  const chosen = traces[active];
  const valid = comparable(baseline, chosen);
  const end = valid ? Math.max(duration(baseline), duration(chosen)) : 0;
  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!query) return;
    const update = () => setReduced(query.matches);
    query.addEventListener?.('change', update); return () => query.removeEventListener?.('change', update);
  }, []);
  useEffect(() => { setTime(0); setPlaying(false); }, [baseline, chosen]);
  useEffect(() => {
    if (!playing || !valid || !end) return;
    let frame, previous;
    const tick = stamp => {
      if (previous != null) setTime(current => {
        const next = Math.min(end, current + (stamp - previous) / 1000 * speed);
        if (next >= end) setPlaying(false);
        return next;
      });
      previous = stamp; frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick); return () => cancelAnimationFrame(frame);
  }, [playing, speed, end, valid]);
  return <section className="duel-replay" aria-labelledby="duel-replay-title">
    <style>{`.duel-replay{margin:28px 0;padding:24px;background:#17242d;border:1px solid #34434b;color:#edf3f1}.duel-replay-head{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:18px}.duel-replay h2{margin:4px 0;font-size:22px}.duel-replay p{color:#acb9bc;margin:6px 0;line-height:1.5}.duel-overline{font-size:11px;letter-spacing:.15em;color:#ff777c;font-weight:700;text-transform:uppercase}.duel-stages{display:grid;grid-template-columns:1fr 1fr;gap:12px}.duel-stage{background:#101a21;border:1px solid #354650;min-width:0}.duel-stage-label{padding:10px 14px;font-size:11px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;color:#b9c9ca;border-bottom:1px solid #354650}.duel-stage canvas{display:block;width:100%;height:auto}.duel-controls{display:flex;align-items:center;gap:12px;margin-top:16px;flex-wrap:wrap}.duel-controls button,.duel-controls select,.duel-replay-head select{background:#263740;color:#edf3f1;border:1px solid #52646b;padding:9px 12px;font:inherit}.duel-controls button{cursor:pointer}.duel-controls input{flex:1;min-width:160px;accent-color:#ff6b72}.duel-controls output{font-variant-numeric:tabular-nums;font-size:12px;color:#cad5d5}.duel-replay :focus-visible{outline:3px solid #ff777c;outline-offset:3px}.duel-note{font-size:12px}.duel-empty{padding:24px;border:1px dashed #52646b;color:#bdcacb}@media(max-width:800px){.duel-stages{grid-template-columns:1fr}.duel-replay-head{align-items:start;flex-direction:column}}`}</style>
    <div className="duel-replay-head"><div><div className="duel-overline">Simulation / single seed</div><h2 id="duel-replay-title">Duel replay</h2><p>One recorded duel, shown alongside the original baseline. This example is not an aggregate result.</p></div>
      {available.length > 0 && <label>Compare <select value={active} onChange={event => setSelected(event.target.value)}>{available.map(key => <option key={key} value={key}>{labels[key]}</option>)}</select></label>}</div>
    {!baseline || !available.length ? <div className="duel-empty">Recorded comparison traces are not available for this run.</div> : !valid ? <div className="duel-empty">These traces cannot be synchronized: matching seed, starting order, weapons, range and strategy are required.</div> : <>
      <div className="duel-stages"><ReplayCanvas trace={baseline} time={time} assets={assets} label={labels.baseline} reducedMotion={reduced} /><ReplayCanvas trace={chosen} time={time} assets={assets} label={labels[active]} reducedMotion={reduced} /></div>
      <div className="duel-controls"><button type="button" onClick={() => { if (time >= end) setTime(0); setPlaying(!playing); }}>{playing ? 'Pause' : 'Play'}</button><button type="button" onClick={() => { setPlaying(false); setTime(0); }}>Restart</button><input type="range" min="0" max={end || 0} step="0.01" value={Math.min(time, end)} aria-label="Replay time" onChange={event => { setPlaying(false); setTime(Number(event.target.value)); }} /><output>{time.toFixed(2)} / {end.toFixed(2)}s</output><label>Speed <select value={speed} onChange={event => setSpeed(Number(event.target.value))}><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option></select></label></div>
      <p className="duel-note">Seed {baseline.seed} · {baseline.first?.toUpperCase()} starts · {baseline.range_m} m · {title(baseline.strategy)}. {reduced ? 'Reduced motion is enabled; transient effects are hidden.' : 'Shots, damage and reloads appear only when recorded.'}</p>
    </>}
  </section>;
}
