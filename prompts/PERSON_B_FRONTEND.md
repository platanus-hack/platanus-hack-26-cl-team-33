# PERSON B — FRONTEND + USER EXPERIENCE — paste AFTER GLOBAL PROMPT

You own **only** `frontend/`. The TypeScript API contract in `frontend/src/types/api.ts` is frozen; C coordinates any contract change. Work with the JSON response fixtures from hour 1, without waiting on the engine.

## Product to implement

A polished, credible web application titled **BedFlow Chile — Hospital Flow Simulation Lab**. Judges need to understand the scientific model, change a parameter, run a real experiment, and see why the bottleneck changes. Build React/Vite/TypeScript + Tailwind + Recharts (avoid adding unnecessary frontend libraries).

### Page 1 — Simulate

- Header: simulated fictional hospital, synthetic assumptions disclaimer, note that MINSAL's ≥85% within 12h figure is a **policy target**.
- Controls: select baseline, more physicians, faster turnover, or more ward beds; show exact overridden values. Editable input controls for admission probability and arrival rate are optional, but if added must update the request `config` and cause a new run.
- Primary action: **Run simulation** sends `POST /api/v1/simulate` request with agreed config/seed.
- KPI cards (real response): admission-within-12h %, average capped wait, ED bay utilization %, ward occupancy %.
- Playback: an animated timeline driven by actual `timeline` snapshots, with a scrubber/play-pause and labels for ED waiting, in treatment, boarding, ward occupied, turnover, ready.
- A synchronized time-series chart for queues/boarding and hospital capacity. No client-side random animations.
- Optional patient journey panel rendering `patient_examples[].milestones` with time labels; all synthetic.

### Page 2 — Compare

- One click uses `POST /api/v1/compare` with exact four scenarios and matched seed list.
- Bar chart of `summary.admitted_within_12h_pct.mean` with 95% intervals.
- Show `paired_delta_12h_pp` vs baseline as percentage points, with intervals and a warning if they straddle zero.
- Compare `mean_wait_to_bed_capped_12h_min` and `avg_ed_bay_utilization_pct`; never invent conclusions when the interval is inconclusive.
- Make accessible: labels, keyboard support, responsive mobile handling, loading and error states.

## Build order

**H1–H4:** Implement static shell and strongly typed API adapter with `useMock=true`, using `/fixtures/simulate_response.json` and `/fixtures/compare_response.json`. Build complete UI with real fixture rendering. Do not store derived metric values in JSX.

**H4–H8:** Complete experiment form, KPI cards, synchronized replay, charts, and compare screen. Support proper waiting/loading/error states.

**H8–H12:** Switch to real API by changing adapter configuration only; verify against `POST /api/v1/simulate`, no component rewrite. Support CORS/proxy configuration and null metrics.

**H12–H20:** Polish, improve accessibility, add optional patient journey, test base vs changed scenario, verify that every graph is response-driven. Add a one-click `Demo configuration` preset using only contracted fields, not canned results.

## Interface constraints

- Treat all event times as **simulated minutes** and convert to days/hours only for display.
- Treat percentages as **0–100** and paired deltas as **percentage points**, never percent relative changes.
- Do not display the 85% target as measured hospital performance.
- `timeline.ed_treatment + timeline.ed_boarding` is ED bay use. These counts are disjoint.
- If API returns an error, don't leave stale charts labeled as current. Mark synthetic fixture/demo mode clearly during development and turn it off for the real submission.
- No triage, diagnosis, patient mortality, routing, or clinical intervention widgets.

## Deliver to integration

`npm install && npm run dev` starts the UI. Provide the adapter location, exact environment variable to switch mock/real, screenshot or screen recording of both pages, and one successful real API request trace at H12.
