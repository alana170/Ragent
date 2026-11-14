# RAGENT Product Vision

## Executive summary

RAGENT is an agentic balance-testing workbench for VALORANT developers. It helps a game team evaluate balance ideas before internal human playtesting by simulating proposed changes, testing useful combinations, checking candidates against game rules, and presenting ranked recommendations with reproducible evidence.

The primary promise is a faster, less costly balancing process. RAGENT automates much of the early exploration so internal testers can spend their time on a smaller, better-informed set of candidate changes. It supports human judgment: developers choose what to test, review the evidence, and decide what proceeds to playtesting. RAGENT does not silently change the live game or ship a patch.

The hackathon version demonstrates this workflow in a simplified VALORANT-like test bed with a small mix of agent ability and weapon changes. It uses synthetic scenarios so the demo is fully usable without Riot API access. If access and an approved use case are available, Riot API data may optionally contribute aggregate signals about what balance questions are worth investigating. API access is not a prerequisite for simulation.

## Accepted demo stack and presentation requirements

The website uses **React, TypeScript, Vite and Tailwind CSS**, backed by **Python and FastAPI**. Gemini remains responsible for interpreting proposals and explaining evidence. Python owns simulation, metrics, constraints, search and verification. Local JSON/JSONL artifacts support reproducible hackathon runs.

Visual quality is a core requirement, including the game view. Build an animated tactical replay with real VALORANT agent portraits, ability icons, weapon images and supported map artwork, plus movement, shots, smoke, health, objective state and synchronized before/after playback. The interface retains RAGENT's own identity and source attribution.

Use a pinned snapshot of real game content and available weapon statistics as baseline inputs. Riot's published content catalog is the preferred official asset source; the unofficial Valorant-API can supply additional artwork and static data with recorded provenance. Record source versions, retrieval dates, units, missing values and explicit simulator approximations. Ability numbers absent from these sources need a documented source rather than invented precision. Review source freshness during ingestion instead of assuming every endpoint reflects the latest patch.

Real assets and real baseline values do not make generated match outcomes observed VALORANT data. Encounters, strategies, patch predictions and replays are simulated and labeled accordingly. Actual match telemetry is a separate optional integration subject to access requirements; the complete demo runs offline from the pinned content snapshot. Full 3D VALORANT recreation remains outside the hackathon scope.

## The problem

Balance decisions are difficult because overall statistics can hide narrow but important problems. An ability or weapon may appear healthy on average while creating a lopsided matchup in a particular map context, role, composition, strategy, or side. A change that improves one case can also create regressions elsewhere.

Teams need to explore many ideas and interactions before they can confidently select a few candidates for internal playtesting. Doing that exploration manually can consume developer and tester time. RAGENT aims to automate the repeatable early investigation, make the tested space visible, and give the team concrete evidence for the next decision.

## Vision

Before a balance idea reaches internal playtesting, a developer can give it to RAGENT and receive a clear account of:

- What changes and combinations were tested.
- Which scenarios, matchups, strategies, and seeds were used.
- Which candidates passed the game's hard constraints.
- How the candidates performed on the selected balance measures.
- Whether the results held up on scenarios that were not used during exploration.
- Which candidates the system recommends for human review, and why.

The team should be able to use the report to choose the next candidates for internal playtesting without having to trust an opaque agent or infer what the simulation did.

## Intended users

The primary users are VALORANT game developers and balance designers who already have balance ideas or questions and want to investigate them before internal playtesting. They may bring a specific proposed change, several alternative ideas, or a set of changes they want to evaluate together.

The immediate product is for a development team workflow, not a player-facing stats site. The hackathon prototype does not need to model Riot's internal organization, permissions, or approval structure.

## Product principles

1. **Human-directed:** Developers provide the initial ideas and choose how much freedom agents have. People decide what to playtest and release.
2. **Evidence before recommendation:** Every ranking should be supported by recorded scenarios, outcomes, constraints, and reasoning.
3. **Reproducible by default:** A result should be traceable to the change set, simulator configuration, scenario, seed, and rule set used.
4. **Explore interactions:** Evaluate individual changes and combinations, since balance effects can depend on how changes interact.
5. **Respect game rules:** Hard constraints are applied before candidates are ranked as recommendations.
6. **Graceful without live data:** Synthetic input and scenarios must support the full core workflow. External data can add signal but cannot block a run.
7. **Optimize for useful iteration:** Measure whether RAGENT helps teams reach an informed shortlist faster and with less simulation effort.

## Core product workflow

### Agent responsibilities

- **Gameplay agents** use different strategies inside the simulator to test how a patch performs across playstyles and scenarios. Their job is to make the evaluation varied; they do not choose patch values.
- **The search policy** selects which submitted changes, combinations, and numeric values to simulate next. It adapts based on measured outcomes, constraints, and the evaluation budget.
- **Gemini** helps interpret developer ideas, suggest hypotheses for the search to validate, and explain the final evidence. It does not calculate metrics or determine candidate rankings.

### 1. Start a balance run

The developer creates a run and supplies proposed balance changes. For the hackathon, examples include adjustments to agent abilities and weapon parameters. A run may contain one idea or several alternatives.

The developer selects the exploration mode:

- **Evaluate submitted ideas:** Test each supplied change and relevant combinations, using developer-specified values.
- **Explore related variants:** Combine submitted changes and tune their values within developer-configured bounds.

### 2. Set constraints and evaluation criteria

RAGENT applies baseline, rule-based game constraints and allows the developer to configure additional constraints for the run. Constraints define which candidates are invalid and which tradeoffs or balance measures matter. Candidates that violate hard constraints are excluded from the eligible ranked set, with the failed rules shown in the report.

The hackathon should expose a small, understandable set of controls rather than attempt to encode every possible production rule. Longer term, teams may need locked core rules as well as configurable run-level rules.

### 3. Simulate candidate changes

Agents run the selected changes in a simplified game environment across relevant scenarios, matchups, and seeds. The search space includes both combinations of submitted changes and numeric tuning of their values within developer-set bounds. The search should adapt across rounds: after each simulation batch, use the observed results to choose which candidates to test next, prioritizing promise, uncertainty, information value, and evaluation cost rather than blindly enumerating every possible combination.

For the hackathon, use a bounded search policy to choose candidates from the developer's proposed changes and value ranges. For a small search space, start with exhaustive or grid search; this is easy to audit and gives a useful baseline. If numeric tuning becomes expensive, evaluate a constrained, cost-aware Bayesian optimization approach. Do not add Bayesian optimization unless it improves candidate quality per simulation budget for this simulator. The search policy uses results from each round to decide what to evaluate next. Use lower-cost evaluations to screen candidates where practical, then spend more effort on stronger candidates before held-out verification.

The optimization objective follows an understandable order: first reject candidates that violate hard constraints; then prefer candidates that move the selected balance measures toward their target ranges; among candidates with strong, robust held-out results, prefer the smallest, most targeted patch. When metrics conflict, show the tradeoff instead of hiding it in an unexplained score.

The simulator records what it ran and the result of each run. The run audit trail covers the full search process: generated candidates, combinations selected for testing and why, configuration and seeds, simulation outcomes, constraint checks and rejections, verification, and ranking decisions. This includes failed or rejected candidates, not only the final recommendation, so developers can understand the breadth and limits of the search and reproduce the results.

### 4. Verify promising candidates

Promising candidates are retested against held-out scenarios or seeds that were not used to select them. This helps check whether a candidate's apparent improvement generalizes and whether it creates regressions outside the examples that revealed the original issue.

### 5. Review results and choose playtest candidates

The dashboard presents the run history and a ranked report. Code determines candidate eligibility and ranking from measured results, hard constraints, target ranges, patch size, and held-out robustness. Gemini drafts the report and recommendation rationale from those structured results: what improved, what tradeoffs remain, why a leading candidate is promising, and what evidence or limitations developers should consider. Developers review the evidence and choose which candidates, if any, are good enough to take to internal human playtesting. RAGENT does not make that approval decision on their behalf.

## Hackathon MVP

### Gemini's role and guardrails

Gemini helps interpret developer proposals, suggest hypotheses or interactions worth investigating, and draft the final explanation and recommendation for developers. It is not the optimizer's source of truth. The search policy chooses the next candidates; the simulator computes metrics; code enforces rules and determines the eligible ranking; Gemini explains the evidence, tradeoffs, and limitations in readable language. Any Gemini-suggested hypothesis must be converted to a bounded candidate and validated before it is simulated. Every suggestion and generated report is recorded in the run audit trail.

The optimizer adapts from measured results; Gemini is not trained or updating its model weights during a run. Training an RL policy is not required for the hackathon. Keep the search policy measurable and compare it with a simple baseline before adding more complex optimization.

The Gemini API offers free access to selected models with usage limits, and Google's pricing documentation says free-tier content may be used to improve its products. Use synthetic demo inputs, check the current [pricing and data-use terms](https://ai.google.dev/gemini-api/docs/pricing) and [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), and do not send confidential or player-identifying data through the free tier.

### In scope

- A simplified VALORANT-like simulator covering a small mix of agent abilities and weapon tuning.
- Synthetic game scenarios and data sufficient to demonstrate the complete balance-testing workflow.
- Developer-submitted balance proposals.
- A developer choice between evaluating submitted ideas only and allowing agents to explore related variations.
- An iterative search agent that can combine submitted changes and tune their numeric values within developer-configured bounds.
- An adaptive search policy that uses each simulation round to choose subsequent candidates, informed by observed results, uncertainty, and evaluation cost.
- Gemini API integration to interpret proposals, suggest testable hypotheses, and generate the evidence-grounded final report and recommendation explanation.
- Programmatic validation of every candidate and deterministic calculation of simulation metrics, constraint outcomes, and candidate rankings.
- Testing individual changes and combinations of changes.
- An explicit optimization order: enforce hard constraints, move selected measures toward target ranges, then prefer smaller patches that remain robust on held-out scenarios.
- Baseline rule-based constraints plus developer-configurable run constraints.
- Hard-constraint filtering before recommendations are ranked.
- Relevant scenario variation and held-out verification for promising candidates.
- A dashboard that shows the runs, changes, combinations, simulation activity, results, rankings, and recommendation reasoning.
- A report that explains what was tested, what passed or failed constraints, why candidates ranked as they did, and what evidence supports taking them to playtesting.
- A complete per-run audit trail of agent actions and decisions, including why combinations were selected, how candidates were changed, what was simulated, and how results affected filtering and ranking.
- A record of Gemini model/configuration, structured requests and responses, proposal validation, and report generation, so the LLM's contribution is reviewable.
- Run records detailed enough to reproduce results, including changes, scenario, seed, and constraints.
- Basic efficiency measurements such as run duration and number of combinations explored.
- A simple-search baseline, such as exhaustive or grid search for a small space. Test Bayesian optimization only if the numeric search is large or costly; keep it only if it improves candidate quality per simulation budget.
- Optional Riot API-derived aggregate signals if access and an appropriate use case can be established; synthetic data remains the fallback and the core simulator remains independent.

### Out of scope for the hackathon

- Automatically detecting balance issues from live game data or running scheduled detection jobs. This is a separate product process that may later feed questions into RAGENT.
- Depending on a Riot API key, Riot data, or external services for the demo to function.
- Sending confidential or player-identifying data to the Gemini free tier. Use synthetic demo data and review current model data-use terms and quotas before connecting other data.
- Simulating the full VALORANT game or accurately reproducing every mechanic.
- Integrating with Riot's internal development, telemetry, source-control, or CI systems.
- Production-grade organization roles, permissions, and change-ownership workflows.
- Automatically approving, merging, deploying, or shipping balance changes.
- Claiming time or cost savings without a credible comparison baseline.

## Success measures

The product's top-level outcome is faster and less costly balance iteration. The demo should show evidence for that outcome while also showing that the recommendations are useful.

### Efficiency measures

- **Time to ranked report:** Elapsed time from submitting a run to receiving its report.
- **Exploration throughput:** Number of candidates and combinations evaluated per run, alongside run duration.
- **Simulation effort per viable candidate:** Compute or simulation effort needed to produce a candidate that passes hard constraints and verification.
- **Comparison with current process:** Where a team can provide a manual baseline, compare the time and effort required to reach a similar shortlist. Without a baseline, report measured run data rather than claiming savings.

### Candidate quality measures

- **Balance movement:** Change in selected balance measures, such as matchup win-rate spread or role/agent performance distribution.
- **Constraint pass rate:** The share of explored candidates that satisfy the hard rules, plus a record of why candidates fail.
- **Held-out stability:** Whether promising candidates retain their results on unseen scenarios or seeds and avoid measured regressions.
- **Review usefulness:** Whether developers find the report and its evidence sufficient to select candidates for internal playtesting. This can be evaluated through feedback during the demo or pilot.

Specific numeric targets should be set after the simulator and baseline are defined. A single aggregate win rate is not sufficient to establish balance or recommendation quality.

## Dashboard and report requirements

The dashboard is the primary product surface for understanding and reviewing a run. It should make the search process legible, not just display a final score.

At minimum, a run view should include:

- The developer's initial proposal and selected exploration mode.
- The constraints and evaluation measures applied.
- Every candidate change and combination that was tested.
- The search progression, including combinations considered or selected and the agent's reason for prioritizing them.
- Simulation status and logs, including failures and constraint rejections.
- Results broken down by relevant scenarios or matchups.
- A clear comparison of the baseline against candidates.
- Held-out verification results and observed regressions.
- A ranked shortlist with concise reasoning and evidence for each recommendation.
- Reproduction details: change set, scenario, seed, simulator configuration, and constraint set.
- Run duration and exploration counts to support efficiency evaluation.

The audit trail should cover the complete run from input to final ranking. It should distinguish recorded simulation facts from agent-generated explanations and retain enough detail to reproduce the tested results.

Reports should distinguish simulated evidence from agent-generated interpretation. The explanation should identify the evidence behind each conclusion and call out uncertainty or missing coverage rather than present a confident recommendation without support.

## Riot API and data direction

Riot API access is an optional avenue for providing balance signals, such as aggregate observations that help identify what questions the team may want to investigate. It is not the simulation engine and should not be assumed to expose a way to run hypothetical patches through VALORANT.

The official [VALORANT API documentation](https://developer.riotgames.com/docs/valorant) lists endpoints such as match history, ranked leaderboards, content, and platform status. Riot's [API FAQ](https://developer.riotgames.com/docs/faqs) states that personal API keys are not offered for VALORANT; access and approval requirements should be checked during an API feasibility spike. The product should proceed with synthetic scenarios if access is unavailable, delayed, or unsuitable for the use case.

Any use of player-specific information must follow Riot's current policies, including player opt-in requirements where applicable. The hackathon should avoid depending on player-linked data and should prefer synthetic or appropriately aggregated inputs.

Automated monitoring that detects potential balance issues from live or aggregate signals is a separate process from the core patch-evaluation workflow. In a longer-term product, that detection process could create a balance question or suggested run for a developer to review.

## Longer-term product direction

If the hackathon demonstrates value, RAGENT could grow into a team tool used throughout the balancing cycle. Possible future directions include:

- More faithful game simulation and broader scenario coverage.
- Larger candidate searches and more robust held-out evaluation.
- Integration with internal tools and approved game data sources.
- Repeatable runs in a development or CI workflow.
- Access controls and audit history, prioritized for production use.
- A rule model with locked core game constraints and configurable team or run-level constraints.
- Cost-aware Bayesian optimization or other adaptive search methods if later evaluations show they outperform simpler search for the team's actual parameter space.
- Clear production responsibilities: developers configure run rules, designated owners manage core rules, and a team lead reviews candidates for playtesting.
- A separate signal-detection process that can surface potential balance issues and start a developer-reviewed evaluation.

These are future considerations, not requirements for the hackathon MVP.

## Guiding question

Can RAGENT test a developer's balance ideas and useful combinations, find candidates that satisfy the game's constraints, and explain with reproducible evidence which ones are worth taking to internal playtesting—while reducing the time and effort needed to reach that shortlist?

## Origin

The initial product direction was summarized from the [DEVHACKS 2026 vision document](https://docs.google.com/document/d/1BTsGb_O_dktjcG-RDQK0amGYr1RCybcmIqazagC4s4Y/edit?tab=t.xqiraxah7ci), RAGENT tab, then refined through product discovery.
