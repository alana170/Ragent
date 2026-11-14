const test = require('node:test');
const assert = require('node:assert/strict');
const { duration, reconstruct, comparable } = require('../replay-state.cjs');
const trace = { a: 'vandal', b: 'spectre', seed: 7, first: 'a', range_m: 15, strategy: 'defensive', winner: 'a', ttk_s: 2,
  initial_state: { a: { hp: 100, ammo: 2, mag_size: 2 }, b: { hp: 100 } }, events: [
    { time_s: .5, type: 'shot', attacker: 'a', damage: 40, target_hp: 60 },
    { time_s: 1, type: 'reload_start', actor: 'a' },
    { time_s: 1.5, type: 'reload_end', actor: 'a', ammo: 2 },
    { time_s: 2, type: 'shot', attacker: 'a', damage: 60, target_hp: 0 },
    { time_s: 2, type: 'kill', winner: 'a' },
  ] };
test('reconstructs shots, reload, and elimination when seeking in either direction', () => {
  assert.equal(reconstruct(trace, .7).b.hp, 60);
  assert.equal(reconstruct(trace, .7).a.ammo, 1);
  assert.equal(reconstruct(trace, 1.2).a.reloading, true);
  assert.equal(reconstruct(trace, 1.6).a.ammo, 2);
  assert.equal(reconstruct(trace, 2).b.eliminated, true);
  assert.equal(reconstruct(trace, 2).winner, 'a');
  assert.equal(reconstruct(trace, 0).b.hp, 100);
});
test('unknown ammo stays unknown; duration and comparison use recorded metadata', () => {
  const other = { ...trace, initial_state: {}, events: [{ time_s: 3, type: 'shot', attacker: 'b', damage: 0 }] };
  assert.equal(reconstruct(other, 3).b.ammo, null);
  assert.equal(duration(other), 3);
  assert.equal(comparable(trace, { ...trace }), true);
  assert.equal(comparable(trace, { ...trace, seed: 8 }), false);
  assert.equal(comparable(trace, { ...trace, first: undefined }), false);
});
test('handles recorded initial and timed reload events', () => {
  const recorded = { ...trace, events: [
    { type: 'initial', time_s: 0, hp: { a: 100, b: 100 }, ammo: { a: 1, b: 3 } },
    { type: 'shot', time_s: .2, attacker: 'a', ammo: 0, target_hp: 75, damage: 25 },
    { type: 'reload', time_s: .4, actor: 'a', complete_s: 1.4, ammo: 1 },
    { type: 'terminal', time_s: 2, winner: 'draw' },
  ] };
  assert.equal(reconstruct(recorded, .5).a.reloading, true);
  assert.equal(reconstruct(recorded, .5).a.ammo, 0);
  assert.equal(reconstruct(recorded, 1.5).a.reloading, false);
  assert.equal(reconstruct(recorded, 1.5).a.ammo, 1);
  assert.equal(reconstruct(recorded, 2).winner, 'draw');
});
