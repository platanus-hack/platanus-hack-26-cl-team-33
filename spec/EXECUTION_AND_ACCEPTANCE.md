# Execution schedule, integration gates, and acceptance tests

## Ownership map

| Owner | Exclusive work | Consumes | Produces |
| --- | --- | --- | --- |
| A: Simulation | `backend/bedflow/sim/`, `backend/tests/sim/` | Frozen `SimulationConfig`, `SimulationResult` | `simulate(config,seed)` |
| B: UI | `frontend/` (TS contract changes coordinated by C) | Fixture and HTTP JSON | Fully functioning React UI, replay + comparison |
| C: API/Analysis | `contracts.py`, API, experiments, integration, docs, CI | `simulate()`, API fixtures | Two versioned endpoints, intervals, deployment |

## Hour-by-hour checkpoints

| Time | A | B | C | Shared gate |
| --- | --- | --- | --- | --- |
| H0–H1 | Review spec/contract | Review spec/contract, scaffold UI | Initialize repo, Python/TS schema and fixtures | CONTRACT FREEZE, one example request and response load |
| H1–H4 | Cohort generation, initial ward occupancy | Dashboard layout driven by mock JSON | Mock-serving valid `/simulate`, `/compare` endpoints | UI can demonstrate both pages **without** engine |
| H4–H6 | Working patient flow with boarding | Controls, timeline scrubber, KPIs | Scenario overrides + experiment runner | Engine smoke, UI mock, API validation independent |
| H6–H8 | Full evaluation windows and metrics | Compare plots with fixture intervals | CI and stats tests | Every component has unit tests |
| H8–H12 | Corrected deterministic engine | Replace mock adapter with real API | Wire real engine, integration tests | UI → API → SIMPY → real outputs → UI |
| H12–H20 | Physics tests + performance | UX polish, event-driven replay | 4 scenario batch + paired comparisons | Full MVP, no mocked production values |
| H20–H28 | Sensitivity tests if time | Accessibility and mobile + demo animations | Repeated trials, performance, caching if needed | Reliable repeated demo and evidence |
| H28–H36 | Fix correctness issues | Freeze UI, rehearse | Final deploy, backup, docs | Clean startup and 3-minute judge pitch |

## Hard cuts (if late)

1. Remove patient-example inspector and fancy animation transitions; keep timeline charts.
2. Remove custom parameter editing; preserve four exact scenarios.
3. Reduce comparison from 20 to 5 matched seeds in live demo, while showing a precomputed (real engine) 20-seed benchmark with metadata if desired.
4. Simplify extra statistics; **never remove** admission-within-12h or resource conservation.
5. Never add a second hospital, predictive ML, diagnoses, or undertriage features.

## Must-pass tests before demo

**Simulation physics:** ED bay occupancy cannot exceed capacity; physicians cannot exceed capacity; ward ready + turnover + occupied = total; boarding occupies ED bay but not physician; initial ward occupants generate discharge/turnover; admissions only occur after `ADMISSION_INDICATED`; no negative waiting intervals.

**Evaluation:** No indication is included outside `[warmup_end, measurement_end)`; every included indication has 720 simulated minutes follow-up; unresolved at 720 min is counted as a 12h target failure, not deleted; followup arrivals are still generated to avoid a false improvement.

**Randomness:** Same `(seed, config)` reproduces identical outputs; only changing bed turnover/physicians/ward count does not change arrival times or patient-level clinical-duration draws.

**Integration:** Simulate API accepts canonical fixture and returns all typed metrics/timeline; UI shows returned numbers, not constants; comparison shows correct paired **percentage-point** deltas; any edit to Pydantic schema triggers TypeScript type and fixture validation.

**User trust:** Explicit "synthetic" labeling; clear separation between Chile's 85% policy target and model output; no real-world prediction or clinical decision claims; compare uncertainty displayed; failures never show stale results as new.

## Demo script (3 minutes)

- 0:00–0:25: Chile's 12-hour admission target and ED boarding context.
- 0:25–1:00: Show simulated ED and boarding/occupancy timeline for baseline.
- 1:00–1:40: Change to more physicians and run; explain measured effect, including if it doesn't help admission delay.
- 1:40–2:20: Compare faster bed turnover and more staffed beds on same patient seeds; discuss tradeoffs and uncertainty.
- 2:20–2:50: Show paired interval comparison and explain how the bottleneck moves (only if supported by computed results).
- 2:50–3:00: Clarify simulation assumptions and how pilot calibration could make the method operationally useful.

**Never prescript a numerical discovery.** If the engine finds no statistically clear difference, explain what that teaches about the assumptions/limits.
