# Demo UI integration

The demo keeps React, JavaScript, esbuild and custom CSS. From the repository root run `npm ci`, `npm run build`, then start the Python web server using the backend's setup instructions. The built `web/app.js` is served by that server. Run focused replay checks with `node --test frontend/tests/*.test.cjs`.

The frontend never substitutes fixture results. The API boundary is `frontend/api.js`; an older server without optional endpoints displays unavailable states. The backend worktree is authoritative for the contract and must be integrated with this branch before the complete demo can run.

## HTTP fields

- `GET /api/config?profile=<id>`: `profile`, `profiles`, `weapons`, `allowed_parameters` (path to `[min,max]`), `ranges`, `strategies`, `default_matches`, and `source` (source, version, retrieval time, damage context and assumptions). The initial call without a profile uses the server default.
- `GET /api/content`: `source`, `version`, `retrieved_at`, and `assets`, keyed by weapon ID with a same-origin `url`. The backend must serve its pinned assets. Missing manifests and images are explicitly labeled.
- `POST /api/runs`: `{changes, matches, profile}`; returns a run with `id`. `GET /api/runs` returns `{runs:[...]}` and `GET /api/runs/<id>` returns progress and completed data. Runs need `id`, `status`, `events`, `changes`, `before`, `after`, `summary`, `passed`, `verification`, `recommendation`, and report/download URLs. Interrupted and failed runs must retain their status and error.
- A recommendation supplies `candidate_accepted`, `changes`, `final_stats`, `summary`, `baseline_summary`, `verification`, `rationale`, `agent_mode`, and `candidates`. Candidate records supply `id`, `source`, `changes`, `rationale`, `eligible`, and any error, violation or regression lists. A false acceptance is shown as no verified recommendation.
- `explanation` contains plain-text `summary`, `tradeoffs`, `limitations`, and `evidence_ids`. `explanation_model` supplies `status`, `model`, and optional `reason`; it may be nested in `result` or `recommendation`. Only a recorded live/success status is labeled live.
- `replays` is `{scenario, traces}`. Scenario has `a`, `b`, `range_m`, `strategy`, `seed`, and `first`; each of `baseline`, `proposal`, and `recommendation` has `{trace, weapons, config_sha256}`. The adapter flattens this envelope. The engine trace must record initial, shot, reload, kill and terminal events with timestamps and relevant state; absent ammo or artwork remains explicitly unavailable. Matching scenario metadata is required for synchronized comparison. Replay examples are single seeded duels, not aggregate results.

## Integration checks and assumptions

The separate backend branch is in progress; field names above reflect its current implementation and may need adjustment in the adapter. The frontend expects `recommendation.summary` and `baseline_summary` in completed run responses, as the current backend worker provides. Confirm that source/version timestamps and asset URLs match the pinned profile, that saved-run list entries contain IDs, and that the explanation status accurately reflects the provider call. A final recommendation replay should only be offered when the recommendation passed verification. No portrait assets are required: participant markers are used if none are supplied. The replay does not create ability, objective, or tactical movement events.
