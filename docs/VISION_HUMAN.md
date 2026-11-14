# RAGENT: Human Overview

## In one sentence

RAGENT helps VALORANT developers test balance ideas with simulation agents before internal playtesting, so the team can reach a strong shortlist faster and with clear evidence.

## The problem

Overall stats can hide specific unfair matchups or interactions. Teams also need to test how proposed changes work on their own and in combination. That early exploration takes time, and a change that improves one case can create a problem elsewhere.

## How RAGENT works

1. A developer enters one or more proposed changes.
2. The developer chooses whether agents should test only those ideas and combinations, or also combine changes and tune values within set bounds.
3. A bounded search policy uses each round's measured results to choose what to test next. Gemini may suggest hypotheses or interactions; code validates candidates and the simulator measures outcomes.
4. Promising candidates are checked on held-out scenarios for regressions.
5. Code ranks eligible candidates using the agreed measures. Gemini drafts the recommendation and rationale from the recorded evidence.
6. A full-run audit log records what the agents considered and tested, why they chose those combinations, what happened, and how that affected rankings. The team decides what is ready for internal human playtesting.

RAGENT informs the decision; it does not approve or ship a patch.

Gameplay agents test each patch with varied strategies. A separate search policy chooses the patch combinations and values to evaluate. Gemini helps develop hypotheses and explain results; it does not score or rank candidates.

## Hackathon decisions

- **Audience:** VALORANT game developers and balance designers.
- **Focus:** Evaluate developer-proposed balance changes before internal playtesting.
- **Demo test bed:** A simplified VALORANT-like simulator with a small mix of agent ability and weapon tuning.
- **Data:** Synthetic scenarios make the full demo work without Riot API access.
- **Optional API use:** If access and an appropriate use case are available, Riot API data may provide aggregate signals about what to investigate. API access is not required for the simulation, and live issue detection is a separate future process.
- **Agent freedom:** Developers choose whether agents only test submitted ideas or also combine changes and tune their values within configured bounds.
- **Iterative search:** The search policy adapts candidate selection using measured results. Start with exhaustive or grid search for a small space; consider Bayesian optimization only if numeric tuning is costly and it improves results per simulation budget.
- **Gemini's role:** Gemini helps develop testable hypotheses and writes the evidence-grounded report. It does not calculate scores or control candidate rankings.
- **Grounded recommendations:** Code validates candidates and calculates metrics and rankings; Gemini explains the results and helps developers justify a playtest recommendation.
- **Gemini data:** Use synthetic demo data with the free tier; check current quotas and data-use terms before sending any other data.
- **Constraints:** Baseline game rules and developer-configured run constraints apply. Candidates that fail hard constraints are not ranked as viable recommendations.
- **Human control:** Developers review the evidence and choose candidates for playtesting.

## What the team sees

The dashboard and report should make each run understandable and reproducible. The audit log covers the whole run: proposed changes, candidate and combination selection, reasons for prioritizing tests, scenarios and seeds, simulation logs, constraint failures, matchup results, held-out checks, and the reasoning behind rankings. Gemini's report should be grounded in recorded simulator results and show uncertainty or missing coverage rather than overstate what the simulation proves. Use synthetic data with the Gemini free tier and check current model quotas and data-use terms.

## How we’ll judge the demo

The main goal is faster, less costly iteration. Track:

- Time from submitting a run to receiving a ranked report.
- Number of candidates and combinations explored, alongside run time.
- Simulation effort per candidate that passes constraints and verification.
- Balance results and held-out stability.
- Whether developers find the evidence useful for selecting playtest candidates.

Claim time or cost savings only if there is a credible manual baseline for comparison.

## Not part of the hackathon

Live or scheduled balance-issue detection, reliance on Riot API access, a full VALORANT simulation, integration with internal development or CI systems, production permissions and ownership workflows, training an RL policy, and automatic patch approval or release.

## Detailed reference

See [the detailed vision and requirements](VISION.md) for the full workflow, requirements, metrics, API considerations, and longer-term direction.
