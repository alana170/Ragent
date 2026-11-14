# RAGENT Minimal Demo Completion Plan

Revised November 14, 2026, against main checkout `7dbcce5`. This plan extends the working application; [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) describes the full target. These are implementation tasks, not claims that Gemini or VALORANT integration already exists.

## 1. What we will demonstrate

A developer loads real weapon baseline values, proposes a stat change, watches RAGENT test it and bounded alternatives, sees held-out results, watches the corresponding before/after duel, and reads Gemini's explanation of which next step is supported by the evidence.

**Required additions:** real Gemini integration, a pinned VALORANT weapon profile with real artwork and supported stats, a polished React duel replay from the same simulator, and a reliable saved-run/demo flow. Keep the current React + JavaScript + esbuild + custom CSS and Python HTTP server. TypeScript/Vite/Tailwind/FastAPI migration belongs to the full plan; visual quality does not depend on that migration.

Planning estimate: two builders, approximately 8–12 elapsed working hours (16–24 person-hours), subject to the first integration checkpoint. Real-data mapping and model access can change that estimate. Work in `/home/sahas_u/projects/Ragent` on its existing branch; preserve `.env`, planning documents and other local work.

## 2. Keep what already works

| Reuse | Evidence and limits |
| --- | --- |
| React form, progress log, result cards, matchup table and downloads | Production bundle built successfully; appearance still needs browser review |
| `ragent_openfire/web.py` | HTTP submission/polling/report download passed a smoke check |
| Weapon-duel model, paired starting orders and existing metrics | Existing simulator and bridge tests pass |
| Bounded heuristic singles/pairs and held-out verification | Working foundation; not an adaptive optimizer |
| HTML/JSON reports and OpenFire exporter | Keep output compatibility and optional OpenFire profile |
| Existing test suite | 22 tests passed in the latest review |

Use the OpenFire-style duel engine as the demo's single computation path. Keep `simulator/`, `agents/`, the standalone tactical replay, Godot bridge and CI intact, but do not integrate all of them for this deadline. Existing tactical replay belongs to a different engine and cannot illustrate the dashboard's duel results.

## 3. Task 1: establish one reproducible demo profile

Add an explicit content/profile choice, initially OpenFire and a small VALORANT weapon profile. Extend the current configuration loader and `/api/config` instead of building a new API. Store profile ID, source manifest and policy with each run.

For the VALORANT profile, begin with two weapons such as Vandal and Spectre, one primary distance and a small set of strategies. Select a matchup appropriate to the chosen design question; the weapons are not required to be equally strong. Freeze the profile's target band, bounds and regression limits before the final run. Keep the existing OpenFire policy for its own profile; do not carry its SMG damage bounds into unrelated real weapon stats.

Download and pin a small content snapshot from [Valorant-API](https://valorant-api.com/) and/or Riot's [published catalog](https://developer.riotgames.com/docs/valorant#assets). Save weapon art and a few agent portraits locally, with source URLs, retrieval time, available version, hashes and attribution. Implement a fixed asset manifest served through a safe static route: the current server only serves `/app.js` and `/app.css`, so copying images alone is insufficient.

Normalize available fire rate, magazine, damage and reload fields after inspecting the actual API response. If using one scalar damage value, document its chosen body/range context and limit the demo to that context; do not silently apply it across every distance. Validate integer/finite/positive fields and supply explicitly labeled model assumptions for accuracy, reaction, spread, armor and movement. The current model has 100 HP and simplified hit/falloff behavior; disclose those limitations. Do not relabel the existing OpenFire fixture as real VALORANT stats.

Art may show agent identities, but the minimal duel model does not simulate their abilities. Use agent portraits as participant markers with that scope clear; ability mechanics, smoke and plant/defuse are full-plan work. Real map art can provide context, but avoid suggesting a duel lane tests real navigation or collision geometry.

**Exit:** the existing form runs with the new profile, shows real weapon pictures and source metadata, and produces valid measurements. The pinned snapshot works without network access.

## 4. Task 2: connect Gemini to the actual dashboard workflow

Add one `ragent_openfire/gemini_client.py` adapter using the [Google GenAI SDK](https://ai.google.dev/gemini-api/docs/quickstart) and [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output). Configure a smoke-tested model and server-side `GEMINI_API_KEY`; explicitly load `.env` if supported and never return its contents. Pin the tested SDK version. No key is needed to read existing saved reports.

There are two required uses:

1. **Suggest bounded candidate adjustments.** After the discovery baseline is measured, give Gemini the submitted changes, source/profile, allowlisted parameters, bounds and discovery metrics. Request at most four small patches with short rationales. Validate each with the existing patch checks; reject unknown paths, booleans, non-finite values, out-of-bounds values, invalid integers and duplicates. Combine valid suggestions with the existing heuristic pool under one total candidate/simulation budget; retain deterministic fallback coverage. Code evaluates and selects candidates.
2. **Explain the measured result.** After verification, pass structured facts for original baseline, developer proposal, selected candidate and guardrail results. Ask for a short recommendation, tradeoffs and limitations with evidence IDs. Validate referenced IDs and populate numerical facts from code. The model cannot turn a failed result into a pass.

Wire these calls through `evaluate_proposal()` and the React result payload. The current UI path explicitly calls `optimize(..., allow_llm=False)` and strips the candidate list when assembling the response. Replacing `_llm_candidates()` alone would leave the real demo unchanged. Introduce an explicit Gemini-enabled mode; default to deterministic fallback when unavailable, and label the mode in the page and exported report. Keep the CLI working.

Use discovery results only for suggestions; do not expose already-computed proposal holdout metrics to candidate generation. Reserve a distinct verification seed range for the final recommendation rather than recycling a holdout used to inspect the developer proposal. Freeze the candidate before verification and do not auto-retry search based on holdout failures. Treat repeated interactive tuning as new runs needing fresh holdout seeds.

Target two model calls per run, one for proposals and one for the explanation, with bounded request time, output length and retry count. Timeout, missing credentials, malformed JSON, model failure or quota exhaustion falls back to current heuristic search and a deterministic explanation. Render generated text as plain text or sanitized Markdown. Record model ID/settings, call purpose, validated response, latency and failure status without secrets.

**Exit:** one real Gemini request produces a candidate that is actually simulated, and a grounded explanation appears in React and the report. A model-failure run also completes. No placeholder or recorded response is labeled live Gemini.

## 5. Task 3: add a visually strong, truthful game view

Extend `frontend/src.jsx` with a small reusable Canvas replay component and targeted CSS. Preserve the current forms and reports. Use a dark stage, crisp weapon silhouettes, participant portraits, health/ammo panels, range marker, firing tracers, damage feedback, reload indication and elimination state. Match the surrounding interface with a restrained palette, readable spacing and clear baseline/proposal/recommendation labels.

Generate replay traces using `ragent_openfire.simulation.duel(..., include_events=True)` for the exact chosen profile, patch, seed, strategy, distance and starting order. The UI currently calls `run_suite(..., trace_one=False)`; add an explicit replay-generation step after evaluation and save only the selected illustrative traces to keep results small. Store all inputs and the candidate/config hash. A replay is one seed example, not proof of the aggregate win rate.

Keep original baseline, developer proposal and final recommendation distinct. Provide a selector and synchronized baseline-versus-selected comparison. For each comparison use the same seed and starting order and preserve each trace's actual end time/outcome. Prefer a predefined sample seed, not a cherry-picked impressive result.

The duel engine already records shots, target health and distance-derived positions. Add initial-state, reload and terminal events where missing; display only movement implied by those traces. Do not manufacture tactical flanks, smoke or objective actions that were never simulated. Play/pause, restart, scrub and speed controls must reconstruct correct state at any timestamp, including reloads and after elimination. Respect reduced motion and keep a readable result when animation is disabled.

Serve saved traces through the existing server and render them in the same React page. Full map navigation, 3D models and connecting the separate tactical simulator are deferred.

**Exit:** changing a weapon affects both the measured duel and its matching replay; the before/after game view is polished enough to show without switching to a separate technical page.

## 6. Task 4: make the recommendation and run recoverable

Make small correctness and persistence changes before calling the demo finished:

- Keep candidate IDs, patches, source (`gemini` or `heuristic`), rationales, measured metrics, rejection reasons and attempt count in saved results and a compact React candidate table. Existing heuristic rationale text must not be displayed as Gemini prose.
- Separate eligible candidates from best-effort inspection. Current optimization sorts every finite-scored attempt; add an eligibility gate so static/training failures cannot become a passing recommendation. Keep held-out checks as the final independent gate. Include an unchanged comparator and allow no verified improvement.
- Present original baseline → developer proposal → recommended final values explicitly. The recommendation currently starts from the proposed configuration; verify final edits against the original baseline too, so it cannot hide regressions caused by the original proposal. Report both comparisons.
- Persist original run inputs, profile/version, constraints, search and verification seed ranges, timings, progress, attempts, final verdict, explanation and replay references alongside existing HTML/JSON outputs. Use atomic writes. Sanitized exports contain no keys.
- Add a small saved-run list/read path so refresh or server restart can reopen completed artifacts. Keep the one-active-run guard and stop polling completed/failed runs. Mark interrupted work rather than pretending it completed.
- Catch invalid top-level request types, simulation failure, missing image/source files and model failure with a clear UI state. Keep the server's static-file access restricted to the intended asset directory/manifest.

**Exit:** a completed run reopens after restart, its numbers agree across React/HTML/JSON, failures remain legible, and a failed patch is never labeled verified.

## 7. Task 5: finish, verify and rehearse

Keep the 22 existing tests passing. Add focused tests for the Gemini validation/fallback boundary, profile mapping, source preservation, seed partitioning, eligibility, combined-versus-original regression checks, saved-run reload and replay time-to-state reconstruction. Update output-format tests intentionally when adding Gemini metadata; do not depend on live model calls in routine tests.

Run `npm ci`, `npm run build` and the full pytest suite in a supported environment. Do a browser walkthrough of config → submission → live progress → results → replay → explanation → download → reopen. Check 1440×900 and 1280×720, asset loading, keyboard controls, reduced motion and browser errors. Test no verified candidate, missing key, Gemini timeout and server restart. Record measured runtime rather than promising a latency before profiling.

Update setup instructions with Python dependencies, the actual server/build commands, environment variable names, content snapshot generation, model/fallback labels and a one-click demo preset. Do not initialize Godot/OpenFire or migrate the whole build system just to launch this demo.

Prepare a genuine successful run and a rejected/no-improvement run using predeclared validation criteria. Freeze demo presets before final verification rather than tuning on holdout outcomes. Save HTML/JSON/replays and record a short walkthrough. Offline mode can reopen a previously recorded successful Gemini run with its timestamp/model clearly shown; it cannot make fresh model calls. A new offline run uses the deterministic fallback.

## 8. Execution order and finish line

| Order | Approximate elapsed hours | Integration checkpoint |
| --- | --- | --- |
| 1 | 0–2 | Confirm model access, pin the two-weapon profile/art, freeze payload fields and demo policy |
| 2 | 2–5 | Backend: Gemini provider, eligibility and seed boundaries. Frontend: artwork, candidate/explanation panels and replay layout |
| 3 | 5–8 | Join live model suggestions to measured runs, add matching traces, persist and reopen completed reports |
| 4 | 8–12 | Browser verification, targeted failure tests, presentation cleanup, recording and rehearsal |

These are two team workstreams, not a requirement to launch coding subagents. Profile mapping and schemas are shared dependencies; agree on them before implementing UI/API changes independently.

The minimal demo is finished only when real Gemini integration has been exercised, the real weapon profile is sourced and labeled correctly, the React page and game view look intentional, final recommendations pass the code's guardrails, and the exact run/replay can be reopened. The presenter can complete the story in about three minutes without entering JSON or showing implementation details.

If time is tight, cut natural-language proposal parsing, additional weapons, decorative agent/ability art, extra animation effects, additional presets and deployment. Preserve actual Gemini suggestions/explanation, two real weapon inputs/images, the matching basic animated duel, held-out checks, candidate inspection and saved artifacts. Keep this plan's current-tooling exception explicit; it does not replace the full stack target in the vision.

## 9. Explicitly deferred to the full plan

TypeScript/Vite/Tailwind/FastAPI migration; general submitted-only versus variant exploration controls; adaptive scheduling and an equal-budget grid benchmark; ability balance and tactical objectives; unseen-strategy verification; full audit browsing; larger search spaces; real map collision/navigation; live Riot telemetry; auth; deployment; and native 3D gameplay.

This demo tests a narrower claim: **given a developer's weapon change, can RAGENT use Gemini-assisted hypotheses and reproducible simulation to explain what passed, what failed, and what to inspect next?** It does not claim live-game balance, human playtest savings or player retention improvements.
