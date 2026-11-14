# RAGENT × OpenFire feature-branch overlay

This directory is a non-destructive addition to the existing [alana170/Ragent](https://github.com/alana170/Ragent) project. It does not replace your teammates' `simulator/`, `agents/`, or `dashboard/` code.

## Current status

- ✅ Parser/exporter for OpenFire's real GDScript `WeaponDB.WEAPONS` numeric stats
- ✅ Fast deterministic, seeded Python duel simulation with a player-model approximation
- ✅ Metrics: per-matchup win%, median TTK, first-shooter advantage, maximum matchup spread
- ✅ Designer policy for a neutral 40–60% peer matchup, not all weapon/range combinations
- ✅ Disclosed demo imbalance (overtuned SMG fire rate)
- ✅ Optional LLM candidate proposals with a constrained, fully functional deterministic search fallback
- ✅ Search/held-out verification with independent seeds; regression comparison
- ✅ Standalone HTML before/after report, JSON traces and Godot `.gd` patch generation
- ✅ Godot 4.6 headless stat-duel scene files (NOT tested against a local Godot executable)
- ✅ GitHub Actions workflow for PR analysis + comment when repo has correct permissions
- ✅ Local developer UI for proposed weapon-stat inputs, progress logs, and per-run HTML/JSON reports
- ✅ React developer dashboard with readable recommendations and matchup breakdowns
- ⚠️ OpenFire source is referenced by a pinned submodule installed on the user's machine, because this environment cannot clone external Git repos directly
- ⚠️ Full native 3D bot-vs-bot OpenFire navigation/multiplayer batch-runner is not implemented

## Apply to Ragent locally

1. Clone Ragent and check out `main`.
2. Unzip this overlay **into the repository root**, merging directories but never overwriting existing simulator modules.
3. Run `bash scripts/publish_branch.sh`. This creates `feat/openfire-balance-ci`, attaches pinned OpenFire as a submodule, runs tests, and makes a local commit.
4. Review the diff, then run `git push -u origin feat/openfire-balance-ci`.
5. Open a PR against `main`. The GitHub Actions PR hook posts the balance QA report.

Please read [docs/OPENFIRE.md](docs/OPENFIRE.md) for usage, assumptions and the Godot side.

## Run the developer dashboard

```bash
npm install
npm run build
python3 -m ragent_openfire.web
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Summary tiles use two decimal places; matchup tables and structured stat details use four. Full reports open separately instead of being embedded in the dashboard.
