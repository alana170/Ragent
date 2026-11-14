# Simulator contract

`simulate_match(config: dict, seed: int, scenario: dict) -> dict` and
`run_experiments(config, scenarios, seeds, workers=1) -> list[dict]` are pure
with respect to their inputs. Results are JSON-serializable and replayable with
identical inputs. Experiment order is scenario input order, then seed input
order. Each pair is one match. An invalid match raises an exception identifying
its scenario and seed in the runner.

Configuration is a JSON object; see `configs/baseline.json`. Times are seconds,
positions and ranges are map units, speed is units/second, health and damage
are health points, probabilities are in [0,1], and angles are not modeled.
`rounds` is the number of independent rounds, `tick_seconds` is the fixed time
step, and `max_ticks` caps each round. A cap ends a round in defenders' favor.
Rectangular cover blocks movement and line of sight. Smoke is a circle blocking
sight through it. Sites and spawn points are 2D coordinates. Players cannot walk
through cover or the map boundary; player-player collision is omitted.

Scenarios contain `id`, optional `overrides` (recursive config merge), and
optional `loadouts` and `policies` mappings by team. Loadouts assign weapons in
player order; policies are `aggressive`, `hold`, or `flank`. Each player has all
three abilities. Dash multiplies movement speed for its duration; smoke blocks sight for its duration; healing is applied evenly over its duration while alive. A plant requires an attacker at a site and uninterrupted time;
a defuse requires a defender at the planted site and uninterrupted time.
Elimination ends a round immediately except that a planted objective must still
be defused or explode after all attackers die. A timeout favors defenders;
explosion favors attackers. Teams switch neither sides nor loadouts.

Results contain seed, scenario_id, winner (more rounds won; defenders win ties),
rounds, round_duration (mean completed round time), players (final-round states
with nonnegative health), events (chronological, with round and time), and
metrics. Rates are fractions of rounds won. Weapon and ability performance map
names to counts; weapon counts include shots, hits, damage and kills, ability
counts include uses and healing. Events record damage, ability uses, deaths and
objective transitions. `round_end` includes the reason and winner. Aggregate
exports calculate win rates across all completed rounds, not an average of
match winners. JSON output uses standard finite numbers only.

## Measured example

On the development environment, Python 3.14 with four spawned workers, the
baseline scenario took 0.92 seconds for 100 matches and 5.45 seconds for 1,000
matches (including process startup and JSON serialization to `/tmp`). These
are observations, not performance guarantees. With seeds 0–99 and 500 rounds
per scenario, the baseline attacker round win rate was 72.0%; changing only
the sniper statistics in the demo scenario yielded 97.4%. Both teams receive
the changed sniper; the observed advantage reflects the simulation's map and
policies, not a claim about a real game.
