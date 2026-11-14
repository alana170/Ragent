// Pure reconstruction of recorded duel events. No simulated actions are added here.
const number = value => typeof value === 'number' && Number.isFinite(value) ? value : null;
const eventTime = event => number(event.time_s) ?? number(event.time) ?? 0;
const actorOf = event => event.attacker || event.actor || event.player;
const opposite = actor => actor === 'a' ? 'b' : 'a';

function duration(trace) {
  if (!trace) return 0;
  return Math.max(0, number(trace.duration_s) ?? 0, number(trace.ttk_s) ?? 0,
    ...(trace.events || []).map(eventTime));
}
function initialPlayer(trace, side) {
  const init = trace.initial_state || trace.initial || {};
  const player = (init.players && init.players[side]) || init[side] || {};
  return { hp: number(player.hp) ?? number(player.health) ?? 100,
    ammo: number(player.ammo), magazine: number(player.magazine) ?? number(player.mag_size),
    reloading: false, eliminated: false, lastShot: null, lastDamage: null };
}
function reconstruct(trace, time) {
  const t = Math.max(0, number(time) ?? 0);
  const state = { a: initialPlayer(trace, 'a'), b: initialPlayer(trace, 'b'),
    distance: number(trace.range_m), winner: null, ended: false };
  const events = [...(trace.events || [])].sort((a, b) => eventTime(a) - eventTime(b));
  for (const event of events) {
    const at = eventTime(event);
    if (at > t) break;
    const actor = actorOf(event);
    const target = event.target || (actor === 'a' || actor === 'b' ? opposite(actor) : null);
    if (number(event.distance_m) != null) state.distance = event.distance_m;
    if (event.type === 'initial') {
      for (const side of ['a', 'b']) {
        state[side].hp = number(event.hp?.[side]) ?? state[side].hp;
        state[side].ammo = number(event.ammo?.[side]) ?? state[side].ammo;
        state[side].magazine = state[side].ammo;
      }
    } else if (event.type === 'shot' && state[actor] && state[target]) {
      state[actor].lastShot = at;
      const ammo = number(event.ammo_remaining) ?? number(event.ammo);
      if (ammo != null) state[actor].ammo = ammo;
      else if (state[actor].ammo != null) state[actor].ammo = Math.max(0, state[actor].ammo - 1);
      const hp = number(event.target_hp) ?? number(event.target_health);
      const damage = number(event.damage);
      if (hp != null) state[target].hp = Math.max(0, hp);
      else if (damage != null) state[target].hp = Math.max(0, state[target].hp - damage);
      if (damage > 0) state[target].lastDamage = { amount: damage, at };
      state[target].eliminated = state[target].hp <= 0;
    } else if ((event.type === 'reload' || event.type === 'reload_start') && state[actor]) {
      state[actor].reloading = number(event.complete_s) == null || t < event.complete_s;
      if (!state[actor].reloading) state[actor].ammo = number(event.ammo) ?? state[actor].magazine;
    } else if ((event.type === 'reload_end' || event.type === 'reload_complete') && state[actor]) {
      state[actor].reloading = false;
      state[actor].ammo = number(event.ammo) ?? number(event.ammo_remaining) ?? state[actor].magazine;
    } else if (event.type === 'kill' || event.type === 'elimination') {
      state.winner = event.winner || actor || null;
      if (state[state.winner]) state[opposite(state.winner)].eliminated = true;
      state.ended = true;
    } else if (event.type === 'terminal' || event.type === 'end') {
      state.winner = event.winner || trace.winner || 'draw';
      state.ended = true;
    }
  }
  // Older traces only carry their terminal result on the duel itself.
  if (t >= duration(trace) && trace.winner && (trace.ttk_s != null || trace.duration_s != null)) {
    state.winner = state.winner || trace.winner;
    state.ended = true;
  }
  return state;
}
function comparable(a, b) {
  if (!a || !b) return false;
  return ['seed', 'first', 'range_m', 'strategy', 'a', 'b'].every(key =>
    a[key] != null && b[key] != null && a[key] === b[key]);
}
module.exports = { duration, reconstruct, comparable };
