# Person B — frontend integration handoff

BedFlow Chile is a fictional hospital-flow experiment, not a clinical management tool. The UI deliberately does not infer a bottleneck or promise an improvement from the ranking of fixture results.

## Scope and interfaces

All changes are under `frontend/`. `src/types/api.ts` and the shared source fixtures are unchanged. The four fixture copies in `src/mocks/` are byte-identical to `fixtures/`.

- `src/api/client.ts`: typed `simulate(SimulateRequest)` and `compare(CompareRequest)` adapter. Returns `{ data, fixture }`, where `data` retains the frozen response shape. Only the two agreed POST endpoints are used.
- `src/api/scenarios.ts`: canonical request construction; exact overrides, fixed simulation seed 42, comparison seeds 101–105. Initial occupied ward beds stay at 21.
- `src/pages/Simulate.tsx`: scenario controls, exact overridden values, canonical demo reset, request lifecycle, response-derived KPI cards.
- `src/components/Replay.tsx`: play/pause and keyboard-compatible scrubber, six response-driven snapshot counters, synchronized chart cursor, accessible snapshot table, synthetic patient milestones.
- `src/pages/Compare.tsx`: all four scenarios, reported means and 95% intervals, paired pp differences, capped waits, ED use, explicit uncertainty when a paired interval includes zero.
- `src/components/common.tsx`: null-safe formatting, simulated day/time conversion, fixture disclosure, loading/error messages.
- `src/main.tsx`, `src/styles.css`: responsive shell, navigation, policy-target disclaimer, focus indicators, reduced-motion styling.

## Startup

Node 22.18+ (validated locally with Node 24.11.1):

```sh
cd frontend
npm install
npm run dev
```

Development starts in clearly labeled fixture mode without an environment file. Fixture responses intentionally preserve the fixed baseline identity: changing a scenario does not pretend to compute a result. Comparison values are also explicitly illustrative.

For HTTP integration:

```sh
VITE_USE_MOCK=false API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

`VITE_USE_MOCK=false` is the exact switch; no component rewrite is needed. `API_PROXY_TARGET` is read by Vite's development server. It defaults to `http://127.0.0.1:8000`. Restart the development server after changing environment configuration. Same-origin proxying avoids browser CORS changes. Production hosting must reverse-proxy `/api` to C's API; Vite's development proxy is not a production server.

Production builds default to HTTP unless `VITE_USE_MOCK=true` is explicitly supplied. For submission, build explicitly with:

```sh
VITE_USE_MOCK=false npm run build
```

The response header `X-BedFlow-Mode` containing `mock`, `stub`, or `fixture` (case insensitive) also triggers fixture disclosure. The existing mock API must never be presented as computed analysis. No silent fixture fallback exists after HTTP failures.

## Scientific/UI decisions

- Counts and metrics come directly from responses; only display formatting and chart error-bar offsets are computed client-side.
- KPIs use `metrics`, not averages reconstructed from snapshots. A's issue #3 confirms exact event-integrated metrics and measurement-window-only snapshots.
- In treatment includes waiting in an ED bay for a physician. Boarding remains a separate count while retaining the bay. No physician-utilization chart is invented.
- Patient journeys may extend past the replay window into follow-up; journey waits are uncapped, distinct from capped aggregate waits.
- Missing admission percentages/waits display “Not available”, never zero.
- Selecting another scenario, resetting demo configuration, or starting/failing a run clears the previous result.
- MINSAL's ≥85% within 12h is labeled as a policy target/reference, not observed hospital performance.
- Comparison intervals are displayed as supplied by C. A paired interval containing zero is explicitly inconclusive. No real-world recommendation is generated.
- The main navigation resets a screen on leaving it, avoiding hidden charts or background replay timers.

## Validation on 2026-11-21 (America/Santiago)

The earlier sandbox blockers were rechecked, not treated as invalid credentials. Git index writes, GitHub authentication (`chimera-z`), fetch, npm registry access, and local servers work with sandbox escalation. The original staged frontend implementation was preserved. No non-frontend files or frozen TypeScript contract were edited.

Passed:

- `npm install` generated `package-lock.json`; a clean `npm ci` passed. Updated Vitest to patched 4.1.12; `npm audit` reports **0 vulnerabilities**.
- `npm test`: **10/10** core adapter and contract tests.
- `npm run test:ui`: **10/10** UI tests, including HTTP fixture disclosure, exact scenario override submission, unavailable null KPIs, simulation and comparison stale-result clearing, demo reset, replay scrub/play/pause/end cleanup, and paired uncertainty.
- `VITE_USE_MOCK=false npm run build`: semantic TypeScript check and production bundle pass. Vite reports a non-blocking ~745 kB uncompressed main chunk (~217 kB gzip); no build error.
- Desktop **1440×1000** and mobile **390×844** browser inspection: both screens, real charts, replay keyboard controls, scenario-result clearing, fixture disclosure, comparison intervals, horizontally scrollable comparison chart/table. No page-level horizontal overflow at mobile width after the tooltip containment fix.
- Stopping the real API after successful comparison and rerunning produces an error with **zero remaining charts/tables**. Local fixture mode and C's HTTP stub mode both visibly disclose fixtures.
- `npm run test:integration` (with HTTP-mode Vite on port 5174): all four simulations, five-seed comparison, zero-admission null metrics, and HTTP 422 for a comparison with no valid admission seeds pass through Vite's `/api` proxy. All captured responses identify `X-BedFlow-Mode: real-engine`.
- `git diff --check`, fixture byte integrity, and unchanged `src/types/api.ts` pass.

Browser-found fixes:

1. Vite 6 preserved dynamic JSON import attributes and served JavaScript, causing the browser to reject fixture imports despite passing Node tests. Static JSON imports now work in both environments.
2. C uses `stub-fixture-not-real`; the adapter now recognizes stub/fixture as well as mock mode headers.
3. Comparison axes encompass the supplied interval bounds (rounded outward to readable ticks), including a real 100.78% upper limit. Intervals are never clamped or recomputed; the UI labels the normal approximation and five-run uncertainty.
4. Resized hidden chart tooltips no longer overflow the mobile page. Comparison chart/table scroll locally and are keyboard focusable. Essential labels and controls have larger type.

## Real-engine evidence and H12 scope

**The real UI → HTTP API → SimPy engine → computed response → UI path passed locally**, using isolated, unmodified copies of these teammate revisions:

- API/experiments, PR #5: `8b9134d72a09784cc91b70f1f16397e4fa8cadd4` (`origin/persona-c`).
- Engine, PR #4: `8d4e1a381ccdfe658867d9d49fcb8e46df7dc086` (`origin/person-a/simulation-engine`).

These copies and their Python virtualenv were placed in ignored `frontend/.integration/`; they are not part of the frontend commit. No teammate implementation was rewritten. Python 3.15.0 was the available local interpreter; the project specifies Python 3.12, which remains the backend CI owner's environment.

The baseline seed-42 browser result was 79/104 admissions within 12h (75.96%), 536.73 min capped wait, 95.58% ED use, 94.63% ward occupancy, and 672 timeline snapshots. More physicians returned its own scenario identity and 537.84 min capped wait, not canned fixture metrics. The comparison returned all four rows and `[101,102,103,104,105]`; the physician paired interval was -0.57 to +0.18 pp and labeled inconclusive.

Evidence is in `frontend/evidence/`:

- `real-api-trace.json`: complete requests/responses, status and mode headers, source commits, capture time. Synthetic data only.
- `real-simulate-desktop.jpg`, `real-simulate-mobile.jpg`, `real-compare-desktop.jpg`, `real-compare-mobile.jpg`: actual real-engine browser screens.
- `fixture-simulate.jpg`, `fixture-compare.jpg`: development fixture smoke-test captures (before final type/spacing polish).
- `http-stub-disclosure-mobile.jpg`, `api-unavailable-mobile.jpg`: disclosure and failure evidence.

Reproduce against the integrated A/C source with:

```sh
# Backend environment with requirements installed
BEDFLOW_MODE=real uvicorn bedflow.api.app:app --app-dir backend --host 127.0.0.1 --port 8000
# Frontend, separate terminal
cd frontend
npm ci
VITE_USE_MOCK=false npm run dev -- --host 127.0.0.1 --port 5174
# Separate terminal, in frontend/
npm run test:integration
```

The integration script defaults to `http://127.0.0.1:5174`; set `BEDFLOW_TEST_ORIGIN` to change it. It intentionally fails on a stub response. Set `BEDFLOW_API_COMMIT` and `BEDFLOW_ENGINE_COMMIT` to the verified backend source revisions when capturing provenance; omitted revisions are marked `unverified`. It writes fresh synthetic trace evidence, so inspect that diff before committing a rerun.

## Integration decisions and remaining dependencies

- Retain the requested canonical five seeds 101–105. A suggested 20 for narrower uncertainty, but changing the demo protocol is a separate coordinated decision.
- C's null policy is implemented server-side: omit missing metrics per statistic; use matched non-null pairs for differences; a single valid seed produces a collapsed interval; zero valid seeds returns HTTP 422. The frontend preserves missing metrics and shows errors without stale output. The contract does not return effective sample counts, so the UI does not invent them.
- PR #4 merged into main during validation. PR #5 was still open at the last integration check. Local H12 evidence covers the exact combined revisions above; it does **not** claim the API is already merged or deployed on main. C must finish PR #5 and the integrated main revision should be smoke-tested again if those backend sources change.
- Production hosting still needs a same-origin `/api` reverse proxy. Production uses HTTP by default; build explicitly with `VITE_USE_MOCK=false` and start the backend with `BEDFLOW_MODE=real` to fail fast if the engine is missing.
- No frontend validation blocker remains. Bundle size is a non-blocking performance follow-up.
- Important decisions and validation results are posted on GitHub issue #3. The frontend is delivered through a PR from `personB/frontend` to `main`; the PR and Git history are the authoritative commit/merge record.
