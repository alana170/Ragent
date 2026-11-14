# Three-minute demo

This is an illustrative 10 m Vandal–Spectre weapon duel, not observed VALORANT telemetry. The pinned profile uses body damage and documented assumptions; no agent abilities, armor or headshots are modeled. The demo preset is fixed before verification: select VALORANT, press **Load demo preset** (Spectre body damage 26 → 27), and leave the default 24 seeds. Each new run receives fresh seed ranges; do not tune the preset to a final holdout.

- **0:00–0:30 — Frame the question.** Select VALORANT, show the locally pinned artwork and source details, then load the preset. Explain that the developer is asking whether this proposed damage change merits further investigation, not asking the simulator to approve a live patch.
- **0:30–1:00 — Run and inspect.** Start the run and show progress. Gemini, when configured and available, supplies hypotheses for code to validate and simulate; otherwise the interface labels deterministic fallback. Candidate eligibility and the independent final check are determined by code. If a run takes longer, continue with the recorded run below.
- **1:00–2:00 — Read the evidence.** Show original baseline, developer proposal, candidates and final verification. Explain any rejection or no-improvement outcome as the measured result. The final comparison includes the original baseline; discovery and verification use different seeds. Read the explanation and its provider status, then open the HTML or JSON export.
- **2:00–3:00 — Replay and reopen.** Compare baseline and the selected version with the synchronized replay. Pause, scrub, and point out this is one paired seeded duel, not proof of an aggregate win rate. Select a saved run to reopen it; identify it as **recorded**. End with the limitations and a human decision about further playtesting.

## Offline recorded run

The included run `e8c18635e27c470d9b459df4ea520245` was recorded 2026-11-14 at approximately 22:48 UTC with Gemini explicitly disabled. It is deterministic fallback, not a recorded Gemini response. It used the preset above and the then-current frozen policy; the report and replay retain the actual seed and outcomes. At recording, both the proposal and final recommendation passed their configured checks. These are simulation guardrails, not proof of game balance.

Before starting the server, run `python scripts/install_recorded_demo.py`. This copies the included JSON/HTML artifacts into `results/` and adjusts their local paths; it refuses to overwrite an existing run. Start or restart the server, then select that ID in **Saved runs**. A new offline run also works using deterministic fallback, but receives fresh seeds and may reach a different verdict.
