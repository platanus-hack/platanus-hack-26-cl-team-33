# BedFlow v1.0 — frozen interface, units, and visualization contract

**Status:** Freeze at kickoff H1. This file and its Python/TypeScript counterparts are the only source of truth for cross-team fields. Changes need approval from all three people and a fixture/schema update in the same PR.

## Ownership and dependency direction

```
frontend (B) ──HTTP JSON──> backend/bedflow/api (C)
                                        │
                                        ▼
                          backend/bedflow/sim (A)
                                        │
                                        ▼
                           SimulationResult (shared schema, C)
                                        │
                             experiments (C) -> summary JSON
```

`sim` may import the shared contracts, but must not import the API, experiment logic, or frontend. `frontend` never re-computes statistics. `api` does not re-implement patient-flow physics.

## Python interface (A implements, C calls)

```python
# backend/bedflow/sim/engine.py
from bedflow.contracts import SimulationConfig, SimulationResult

def simulate(config: SimulationConfig, seed: int) -> SimulationResult:
    """One complete reproducible simulated run, no file or network side effects."""
```

One call per seed/policy. No global RNG, no global state, no CLI stdout parsing. A returns metrics, sampled timeline and example patient journeys. C validates/serializes with shared Pydantic schemas.

## HTTP endpoints (C owns; B consumes)

### `POST /api/v1/simulate`

Request:

```json
{
  "scenario_id": "baseline",
  "seed": 42,
  "config": {
    "arrival_rate_per_hour": 3.0,
    "physicians": 4,
    "ed_spaces": 8,
    "ward_beds": 24,
    "initial_ward_occupied": 21,
    "admission_probability": 0.20,
    "mean_physician_service_min": 35.0,
    "mean_inpatient_los_h": 36.0,
    "bed_turnover_min": 120.0,
    "warmup_h": 72,
    "measurement_h": 168,
    "followup_h": 12,
    "snapshot_every_min": 15
  }
}
```

Response (the sample numbers are **mock values only**):

```json
{
  "schema_version": "1.0",
  "scenario_id": "baseline",
  "seed": 42,
  "metrics": {
    "eligible_admissions": 96,
    "admitted_within_12h_count": 78,
    "admitted_within_12h_pct": 81.25,
    "mean_wait_to_bed_capped_12h_min": 310.0,
    "p90_wait_to_bed_capped_12h_min": 720.0,
    "avg_ed_bay_utilization_pct": 75.0,
    "avg_ward_occupancy_pct": 90.0,
    "max_ed_boarding": 5,
    "ed_arrivals_measured": 500
  },
  "timeline": [
    {"minute": 4320, "ed_waiting": 3, "ed_treatment": 4, "ed_boarding": 2, "ward_occupied": 22, "ward_turnover": 1, "ward_ready": 1}
  ],
  "patient_examples": [
    {"patient_id": 123, "admission_wait_min": 180.0,
      "milestones": [
        {"minute": 4325.0, "type": "ED_ARRIVAL"},
        {"minute": 4350.0, "type": "ED_BAY_ENTER"},
        {"minute": 4352.0, "type": "PHYSICIAN_START"},
        {"minute": 4370.0, "type": "PHYSICIAN_END"},
        {"minute": 4370.0, "type": "ADMISSION_INDICATED"},
        {"minute": 4550.0, "type": "WARD_ADMITTED"}
      ]}
  ]
}
```

`admitted_within_12h_pct` may be null if `eligible_admissions == 0`. Every percent field has **0–100** units, not 0–1. `minute` is simulated minutes from t=0. Patient IDs are synthetic integers. `admission_wait_min` is null for patients not indicated for admission or not yet admitted. `timeline` snapshots are sorted by minute.

Allowed patient milestone types:
`ED_ARRIVAL`, `ED_BAY_ENTER`, `PHYSICIAN_START`, `PHYSICIAN_END`, `ADMISSION_INDICATED`, `WARD_ADMITTED`, `ED_DISCHARGED`, `WARD_DISCHARGED`, `BED_READY`.

Full internal event records may include `patient_id`, `minute`, `type` and optional detail. Only **sampled** journeys are transmitted to the UI to keep payloads bounded. C is free to persist full JSONL logs locally without changing the HTTP response.

### `POST /api/v1/compare`

Request:

```json
{
  "base_config": {"arrival_rate_per_hour": 3.0, "physicians": 4, "ed_spaces": 8, "ward_beds": 24, "initial_ward_occupied": 21, "admission_probability": 0.20, "mean_physician_service_min": 35.0, "mean_inpatient_los_h": 36.0, "bed_turnover_min": 120.0, "warmup_h": 72, "measurement_h": 168, "followup_h": 12, "snapshot_every_min": 15},
  "seeds": [101, 102, 103, 104, 105],
  "scenarios": [
    {"scenario_id": "baseline", "label": "Baseline", "overrides": {}},
    {"scenario_id": "more_physicians", "label": "More physicians", "overrides": {"physicians": 6}},
    {"scenario_id": "faster_turnover", "label": "Faster bed turnover", "overrides": {"bed_turnover_min": 30.0}},
    {"scenario_id": "more_ward_beds", "label": "More staffed ward beds", "overrides": {"ward_beds": 28}}
  ]
}
```

Response:

```json
{
  "schema_version": "1.0",
  "seeds": [101, 102, 103, 104, 105],
  "results": [
    {"scenario_id": "baseline", "label": "Baseline", "summary": {
      "admitted_within_12h_pct": {"mean": 81.25, "ci95_low": 79.0, "ci95_high": 83.5},
      "mean_wait_to_bed_capped_12h_min": {"mean": 310, "ci95_low": 290, "ci95_high": 330},
      "avg_ed_bay_utilization_pct": {"mean": 75, "ci95_low": 73, "ci95_high": 77}
    }, "paired_delta_12h_pp": null},
    {"scenario_id": "more_physicians", "label": "More physicians", "summary": {
      "admitted_within_12h_pct": {"mean": 81.5, "ci95_low": 79.1, "ci95_high": 83.9},
      "mean_wait_to_bed_capped_12h_min": {"mean": 308, "ci95_low": 285, "ci95_high": 331},
      "avg_ed_bay_utilization_pct": {"mean": 74, "ci95_low": 72, "ci95_high": 76}
    }, "paired_delta_12h_pp": {"mean": 0.25, "ci95_low": -1.0, "ci95_high": 1.5}}
  ]
}
```

All numbers here are mock UI fixture numbers, not validated expected effects. Each `summary` contains **exactly these three statistics** for MVP; additional output fields require versioned contract change. Baseline is required and identified by `scenario_id == "baseline"`. C computes scenario metrics per seed and paired differences in percentage points (`pp`), not percentage relative change. For scenarios with no admissions under some seeds, define the summary handling explicitly; for the supplied default config this should be rare.

## Canonical metrics definitions

- `eligible_admissions`: Count `ADMISSION_INDICATED` events in measurement window.
- `admitted_within_12h_count`: Number of above with `WARD_ADMITTED` within 720 minutes of indication (including during follow-up).
- `admitted_within_12h_pct`: `100 * count / eligible_admissions`; null if denominator 0.
- `mean_wait_to_bed_capped_12h_min`: Mean of `min(actual wait,720)` among eligible indications, treating patients without admission by 12h as 720.
- `p90_wait_to_bed_capped_12h_min`: P90 of the same capped distribution.
- `avg_ed_bay_utilization_pct`: Time average of `100 * (ed_treatment + ed_boarding)/ed_spaces` over the **measurement window** (not follow-up). If using 15-min snapshots, explicitly label as a sampled approximation; for an exact figure, integrate events.
- `avg_ward_occupancy_pct`: Time average of `100 * ward_occupied/ward_beds` over measurement window; **turnover beds are not counted as occupied**.
- `max_ed_boarding`: Maximum `ed_boarding` observed over the measurement window (sampled if using snapshots).
- `ed_arrivals_measured`: ED arrivals in measurement window.

Snapshot invariants: `ed_treatment + ed_boarding <= ed_spaces`, `ward_occupied + ward_turnover + ward_ready == ward_beds`, all counts nonnegative. A patient boarding is **not** in `ed_treatment` and still holds an ED bay. A patient's physician is released at `PHYSICIAN_END` even if the patient is boarding.

## Modeling consistency

- Initial ward occupancy count must be `<= ward_beds`.
- Use *the same* arrival process and patient attributes for identical `(seed, base_config arrivals+clinical)` across variants. Fixed per-patient seeded random streams; no policy-dependent RNG draw order.
- Since `more_ward_beds` changes only ward-bed count, do not regenerate the patients, change initial occupied count, or alter clinical durations for that variant.
- Arrivals continue through the 12-hour follow-up, while denominators and occupancy outcomes apply only to the specified measurement window.
- Main endpoint can return a complete `timeline` (15-minute snapshots), plus only 5–10 selected `patient_examples`. B must animate from snapshots, not invent evolving values.

## UI behavior that follows the contract

**Page 1 — Simulate:** scenario picker, adjustable assumption inputs, Run button, KPI cards (12h admission %, average capped wait, ED bay utilization, ward occupancy); synchronized replay slider for `timeline`; stacked occupancy and boarding chart; patient-example event timeline. Every value comes from `/simulate` response.

**Page 2 — Compare:** four fixed policies, Run comparison, bar chart of average 12h admission percent with 95% CI, paired difference chart/table, capped waiting-time comparison and concise warnings about model assumptions. Every number comes from `/compare` response.

UI labels: "Synthetic model", "Hypothetical intervention", "MINSAL 85% target (reference only)", "Not validated for real hospital decisions". Do not show **85%** as observed occupancy or baseline success.

## Error handling

Invalid inputs: HTTP 422 with FastAPI's validation error. Engine failure: HTTP 500 and logged exception; UI shows user-friendly error. Long comparisons show loading progress **without faking results**. Timeout or failure must not display stale metrics as if fresh.
