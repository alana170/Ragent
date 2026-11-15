# Demo HTTP API

The loopback server (`python -m ragent_openfire.web`) accepts JSON and keeps credentials server-side. An absent `profile` defaults to `valorant`. See [BACKEND_SETUP.md](BACKEND_SETUP.md) and [CONTENT_PROFILE.md](CONTENT_PROFILE.md) for setup and source/approximation details.

- `GET /api/config?profile=valorant` returns `profile`, `profiles`, `source`, `weapons`, `allowed_parameters`, `ranges`, `strategies`, and `default_matches`.
- `GET /api/content` returns the pinned artwork manifest. `GET /assets/vandal.png` and `/assets/spectre.png` serve only manifest-listed files.
- `POST /api/runs` starts one run; `409` indicates another is active. Example: `{"profile":"valorant","changes":{"spectre":{"damage":27}},"matches":24,"gemini_enabled":true}`. Response: `202 {"id":"<32 hex characters>","status":"running"}`. `gemini_enabled` defaults to true; false forces offline deterministic behavior.
- `GET /api/runs` lists saved and active runs. `GET /api/runs/<id>` returns status (`running`, `complete`, `failed`, or `interrupted`), progress `events`, input, profile/policy provenance and, when complete, `result`, `recommendation`, `explanation`, and report URLs. Saved completed runs survive restart; incomplete work becomes interrupted. `GET /runs/<id>/json` and `/runs/<id>/report` download the result and HTML.
- `GET /api/runs/<id>/replays` returns `scenario` (weapon IDs, range, strategy, seed and first shooter) and `traces.baseline`, `.proposal`, `.recommendation`, each containing `config_sha256`, complete `weapons`, and the simulator `trace` with initial, shot, reload, kill and terminal events. These are paired single examples, not aggregate evidence.

The `recommendation.candidates` array includes IDs, source (`gemini`, `heuristic`, or `comparator`), changes, rationale, eligibility, measured discovery metrics and any rejection or guardrail failures. Code selects and verifies the candidate. `candidate_accepted` and `verification.passed` are code decisions. `recommendation.model` and `explanation_model` report `status` as `live` or `fallback`, model, purpose, limits, latency when attempted, and sanitized failure reason. A live response is still validated; fallback never implies a successful model call. The explanation contains plain text, validated `evidence_ids`, and code-provided `facts`; render text safely. Original baseline, proposal and final recommendation are distinct, and `verification` contains final comparisons against both baseline and proposal.

Example compact completed response (metrics abbreviated):

```json
{"id":"0123456789abcdef0123456789abcdef","status":"complete","profile":"valorant","recommendation":{"candidate_accepted":false,"candidates":[{"id":"candidate-1","source":"comparator","changes":{},"eligible":true}],"model":{"status":"fallback","reason":"missing_credentials"}},"explanation":{"summary":"Review the code-determined verification result before playtesting.","evidence_ids":["baseline"],"facts":{"baseline":{}}},"report_url":"/runs/0123456789abcdef0123456789abcdef/report"}
```

Seed ranges in `result.seed_ranges` and final verification details are recorded for reproduction. Each run uses a fresh offset, with disjoint discovery, proposal holdout, final recommendation holdout, and illustrative replay seeds. No model response determines metrics, eligibility or the verdict.
