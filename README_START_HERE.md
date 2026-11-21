# BedFlow Chile — three-person parallel build kit

**This kit is ONLY for BedFlow Chile: an emergency-department-to-inpatient-bed flow simulator.** No hidden diagnoses, triage-agent grading, re-triage research, patient deterioration or mortality modeling.

## First 15 minutes

1. All three read `spec/PROJECT_SPEC.md` and `spec/CONTRACTS.md`.
2. Person C creates the Git repository and owns the shared contracts. Copy `starter/backend/bedflow/contracts.py` and `starter/frontend/src/types/api.ts` into the application repo as the first commit. Keep the fixture JSON under `frontend/src/mocks/` (or point the mock adapter to this kit).
3. Person A receives `prompts/GLOBAL_PROMPT.md` + `prompts/PERSON_A_SIMULATION.md`.
4. Person B receives `prompts/GLOBAL_PROMPT.md` + `prompts/PERSON_B_FRONTEND.md`.
5. Person C receives `prompts/GLOBAL_PROMPT.md` + `prompts/PERSON_C_API_EXPERIMENTS.md`.
6. Work in distinct worktrees/branches, merge small commits, and follow `spec/EXECUTION_AND_ACCEPTANCE.md`.

## Non-overlapping ownership

- **A Simulation:** `backend/bedflow/sim/`, `backend/tests/sim/`.
- **B Frontend:** `frontend/` except shared `frontend/src/types/api.ts` contract changes, which C coordinates.
- **C API/Experiments/Integration:** `backend/bedflow/contracts.py`, `backend/bedflow/api/`, `backend/bedflow/experiments/`, `backend/tests/api/`, `backend/tests/integration/`, `docs/`, `.github/`, root tooling.

Shared files are frozen after hour 1. Change them only through a small PR approved by all three.

## Canonical integration surface

- Python: `simulate(config: SimulationConfig, seed: int) -> SimulationResult` from `backend/bedflow/sim/engine.py`.
- HTTP: `POST /api/v1/simulate` and `POST /api/v1/compare`.
- One config schema, in **minutes** for event times, **hours** for stay/horizon config, and explicitly labeled percentages for metrics.
- Frontend builds on `fixtures/simulate_response.json` and `fixtures/compare_response.json` before a real backend exists.
- All metric values and timeline data come from the real SimPy engine when connected. Fixtures are synthetic layout test data only.

## Go/no-go checkpoints

- **H1:** shared schemas frozen, request and response fixtures agreed.
- **H6:** A has runnable engine smoke test, B has mock-driven dashboard, C has mock-serving endpoints.
- **H12:** UI → HTTP → real engine → metrics → UI works end to end.
- **H20:** baseline + 3 interventions + comparison UI and correctness tests.
- **H28:** experiments, uncertainty, UX and backup-demo stabilization.
- **H36:** live demo + cached **real computed** results + documented assumptions, no unfinished must-have features.

The target is H20 MVP, not 36 hours of new feature development.
