# RAGENT × OpenFire — testable game-balance QA bridge

## Scope and source of truth

- Upstream engine: https://github.com/rokasjasonas/openfire
- Pinned upstream commit: `7259140487946532af8310723392cca34a4fb0bb` (MIT code, CC0 assets; preserve upstream LICENSE/CREDITS).
- OpenFire is a separate game used as a **development test bed**. It is NOT Riot software or VALORANT.
- The fast Python tests are a **weapon-stat duel approximation** (aim, movement, cadence, damage, reload, seeded rounds). They do **not** run OpenFire's 3D AI/pathfinding.
- `godot_bridge` adds a simple Godot headless stat-duel cross-check using OpenFire's `WeaponDB` singleton. It does **not** run full bot-vs-bot 3D matches.
- Run Riot-specific hypotheses (first-shot advantage, short-range vs long-range fairness, plausible weapon archetypes), but never claim a change improves player retention without human data.

## Bootstrapping from the existing Ragent repository

```bash
# Work in a separate branch; do not modify your teammates' branches.
git clone https://github.com/alana170/Ragent.git
cd Ragent
git switch -c feat/openfire-balance-ci
# Copy the contents of the supplied RAGENT_openfire_changes overlay into repo root.
bash scripts/bootstrap_openfire.sh
# The submodule is pinned to the upstream commit and retains its MIT license.
git add .gitmodules openfire ragent_openfire configs/openfire_balance_policy.json godot_bridge scripts docs tests .github
```

The shell script copies the Godot test scene into the **submodule working tree**, which you should not inadvertently commit to a third-party repo. The canonical copies live in `godot_bridge/` in Ragent. If you decide to customize the underlying OpenFire game permanently, fork it and point your submodule to that fork.

## Local Python commands (no dependencies beyond stdlib)

```bash
python3 -m unittest discover -s tests -p 'test_openfire_bridge.py' -v
python3 -m ragent_openfire.cli export \
  --source openfire/scripts/autoload/weapon_db.gd --output results/openfire_weapons.json
python3 -m ragent_openfire.cli simulate \
  --weapons results/openfire_weapons.json \
  --policy configs/openfire_balance_policy.json \
  --matches 40 --output results/baseline.json
python3 -m ragent_openfire.cli plant \
  --weapons results/openfire_weapons.json --output results/planted.json
python3 -m ragent_openfire.cli optimize \
  --weapons results/planted.json --policy configs/openfire_balance_policy.json \
  --output results/agent.json --html results/report.html \
  --patched results/verified_stats.json
python3 -m ragent_openfire.cli gd-patch \
  --source openfire/scripts/autoload/weapon_db.gd \
  --weapons results/verified_stats.json \
  --output results/patched_weapon_db.gd --diff results/weapon_db.diff
```

`results/report.html` is self-contained and opens in any browser. Use `results/weapon_db.diff` in your video to show an actual code change. No patch is silently applied upstream. The report includes real simulation results from the local code and keeps hypothetical player-retention claims out of the demo.

## Developer proposal UI

Build the React UI once, then start the local server:

```bash
npm install
npm run build
python3 -m ragent_openfire.web
```

Open `http://127.0.0.1:8765`, edit one or more policy-approved weapon stats, and run a before/after comparison. By default, the starting values come from `fixtures/openfire_weapons_snapshot.json`. To use weapon stats exported from the checked-out OpenFire source instead, export them first and pass the JSON path:

```bash
python3 -m ragent_openfire.cli export \
  --source openfire/scripts/autoload/weapon_db.gd \
  --output results/openfire_weapons.json
python3 -m ragent_openfire.web --weapons results/openfire_weapons.json
```

The React UI validates edits against `configs/openfire_balance_policy.json`, logs matchup and candidate-search progress while the run is executing, and checks both the developer's proposal and a bounded agent recommendation on independent held-out seeds. The final recommendation box shows the extra adjustment (if any), the resulting absolute stat values, and its own verification status. The agent uses a local heuristic candidate search in the UI; proposal data is not sent to an LLM. A per-run HTML report and JSON result are saved under `results/`. It binds to localhost only. A passing result means only that the configured synthetic-simulation guardrails passed; it is not a full-game or human-playtest result. Summary tiles round to two decimal places; detailed matchup values display four.

The report metrics are calculated as follows:

- Per-matchup win rate gives a draw half-credit and pairs both first-shooter assignments for each seed.
- Per-matchup TTK is the median elimination time among decisive duels; the headline mean TTK is the mean of those matchup medians.
- First-shooter advantage is the absolute distance of each matchup's first-shooter win rate from 50%, averaged across matchups.
- Maximum matchup spread is the largest difference between weapon win rates within any fixed distance and strategy.
- Configured neutral-matchup bands, first-shooter threshold, and off-target regression limit determine the guardrail status.

## Godot 4.6 headless stat-duel cross-check

```bash
# Optional: install Godot 4.6 and copy headless test files to OpenFire
cp godot_bridge/ragent_balance.gd godot_bridge/ragent_balance.tscn openfire/tests/
GODOT_BIN=godot # or absolute path to Godot 4.6 executable
"$GODOT_BIN" --headless --path openfire res://tests/ragent_balance.tscn -- \
  --config="$PWD/results/verified_stats.json" \
  --output="$PWD/results/godot_results.json"
```

This checks that the Godot runtime loads its own actual weapon catalog, accepts the candidate balance config and writes an auditable event log. The Python and Godot duel models are not numerically equivalent; don't claim statistical agreement until their assumptions are aligned.

## Metrics and acceptance criteria

- **Per-matchup win rate:** fraction of paired A-vs-B duels A wins (draws contribute half).
- **Time to kill:** median seconds from first engagement to elimination in each scenario, with nondecisive rounds excluded.
- **First-shooter advantage:** observed first-initiator win rate minus 50 percentage points, after pairing both starting orders for each seed.
- **Max matchup spread:** largest difference between winner probabilities within a fixed range/strategy context. This can be large by design for shotguns or snipers.
- **Design guardrail:** only explicitly neutral, peer-weapon matchups must be inside the `40–60%` designer-chosen band. Range-dependent counters are intentionally not forced to 50%.
- **Regressions:** compare unaffected/surrounding scenarios with the baseline and flag shifts above the configured guardrail. For better evaluation, add protected-matchup bounds and more seeds.
- **Held-out verification:** search uses seeds `0..N-1`; independent final verification uses a non-overlapping seed range.

## CI

The GitHub Actions workflow runs Python tests, exports actual OpenFire `WeaponDB` values, performs synthetic experiments, uploads HTML/JSON artifacts, and comments a short report on same-repo PRs. Editing an uncommitted file inside a submodule does not change the parent repository's diff: pin and commit a new submodule SHA if you update the upstream game. A full Godot 3D simulation job would be a future enhancement and is **not** claimed to run in this CI.

## Demo storyline

1. Show OpenFire playable FPS (upstream) and weapon source file.
2. Export real WeaponDB stats; seed a *disclosed, synthetic* imbalance in the SMG rate.
3. Show baseline matchup heatmap, TTK, initiative advantage and matchup spread.
4. Run RAGENT's heuristic or LLM proposer; explain its verified mode truthfully.
5. Show the targeted `weapon_db.diff`, replay event log and held-out verification.
6. State engineering value: fewer manual scenarios to write, more reproducible patch evidence. Do not extrapolate to actual Riot player retention.
