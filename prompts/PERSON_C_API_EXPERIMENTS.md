# PERSON C — CONTRACTS, API, EXPERIMENTS + INTEGRATION — paste AFTER GLOBAL PROMPT

You own `backend/bedflow/contracts.py`, `backend/bedflow/api/`, `backend/bedflow/experiments/`, `backend/tests/api/`, `backend/tests/integration/`, root tooling, `docs/`, and deployment. Coordinate edits to frozen TypeScript types. Do **not** rewrite A's engine or B's React components.

You are the integration lead: unblock both other developers with stable mocks and keep the main branch runnable.

## Your mandatory sequence

**H0–H1:** Initialize Git repo and Python/React scaffolds. Commit the Python and TS types in `starter/` plus the JSON fixtures. Freeze `spec/CONTRACTS.md` after all three approve. Set up branches/worktrees, lightweight CI (pytest, lint, frontend build), and clear dev commands. Create a FastAPI instance with permissive development CORS or a Vite proxy.

**H1–H4:** Create `POST /api/v1/simulate` using a stub adapter that serves the **explicitly marked fixture** response and validates the incoming Pydantic `SimulateRequest`. Also expose `POST /api/v1/compare` fixture. This lets B integrate early. Publish the OpenAPI schema and ensure response validation.

**H4–H8:** Implement experiments: `compare(base_config, scenarios, seeds)` calls A's `simulate` once per seed/variant, applies **whitelisted flat config overrides**, aggregates exactly three contract metrics into `MetricStats`, and computes per-seed paired delta of `admitted_within_12h_pct` in **percentage points** versus baseline. Implement 95% approximate confidence intervals as mean ± 1.96 * sample standard deviation / sqrt(n), label as approximate and use n >= 5 in UI examples. Reject missing baseline, duplicate IDs, zero seeds, invalid overrides, non-finite values, and configurations with initial occupied beds > bed count.

**H8–H12:** Swap stub for real `simulate(config, seed)` implementation. A returns `SimulationResult(scenario_id="custom", ...)`; set external scenario ID via `model_copy(update={"scenario_id": request.scenario_id})`. This preserves the `simulate(config, seed)` signature. Integrate B using existing API routes and fixtures. Add integration smoke test for both endpoints.

**H12–H20:** Run all four scenarios over matched seeds, verify backend performance and reproducibility, document assumptions and observed variation, stabilize API errors and UI integration, add caching of **actually computed** results if needed for predictable demo timing.

**H20–H36:** Own final build, one-command start/dev instructions, deployment and backup demo. Write concise `docs/MODEL_LIMITATIONS.md`, `docs/DEMO_SCRIPT.md`, and tests for scenario contrast; no fabricated results. Keep scope frozen.

## Shared contract responsibilities

- Define the common `SimulationConfig`, `SimulateRequest`, `SimulationResult`, `CompareRequest`, `CompareResponse` Pydantic models from `spec/CONTRACTS.md`.
- Synchronize frontend `api.ts` type declarations with Pydantic outputs. A change to types is a coordinated contract PR, not silent unilateral editing.
- Keep all numeric names, metrics, event values and units unchanged. `schema_version="1.0"` everywhere.
- `POST /api/v1/simulate` **must return** a real `SimulationResult`, not just a metric table; `/compare` should not send huge per-patient event logs.
- Add integration tests matching default baseline and the 3 specified overrides.
- Frontend renders results; C computes intervals; A computes per-run metrics; never duplicate these responsibilities.

## CI acceptance

Run Python schema validation, API test client requests against the fixtures, real sim smoke test after H8, deterministic repeat-run, frontend typecheck + production build, then end-to-end request with B. Flag any inconsistency at H1; do not quietly adjust contract field names to make mocks pass.

## Handoff contract

At each milestone report: exact branch/commit, endpoint URLs, request/response fixture locations, current mode (stub or real), tests passing, observed performance, and blockers. Deploy one reproducible command for the frontend and one for FastAPI, plus a backup cached result that is **computed by the real engine** and labeled with its exact configuration and seeds.
