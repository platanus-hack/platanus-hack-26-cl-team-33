# PERSON A — SIMULATION ENGINE — paste AFTER GLOBAL PROMPT

You own **only** `backend/bedflow/sim/` and `backend/tests/sim/`. Do not modify API, analytics, UI, or the shared `contracts.py` schema. C owns the frozen schema. Develop against the shared fixture and contract, without waiting for real UI.

## Deliverable

Implement exactly:

```python
# backend/bedflow/sim/engine.py
from bedflow.contracts import SimulationConfig, SimulationResult

def simulate(config: SimulationConfig, seed: int) -> SimulationResult:
    ...
```

Must return `SimulationResult` with schema_version, scenario_id (provided by the API wrapper or passed via an agreed additive field; see integration note below), seed, metrics, timeline and 5–10 interesting synthetic patient journeys. **Interface note:** `SimulationConfig` is ONLY model parameters, so use `scenario_id="custom"` inside the engine result; Person C's endpoint uses `model_copy(update={"scenario_id": request.scenario_id})` to supply the external scenario label. Do not add scenario_id to `SimulationConfig` or the function signature.

## Implementation sequence

**H1–H3:** Create pre-generated synthetic cohort: homogeneous Poisson arrivals through warmup+measurement+followup, fixed patient IDs, pre-generated admissions, physician service times, and inpatient LOS using policy-independent per-patient NumPy RNG streams. Model initial occupied ward beds with residual LOS and turnover. Ensure same seed produces identical cohort across policy variants.

**H3–H6:** SimPy patient process: arrival → ED bay request → physician request/service → physician release → disposition; non-admitted release ED bay; admitted mark indication and hold bay while waiting on a ward bed; when admitted, release ED bay. Bed remains occupied for LOS; upon discharge enters turnover, then becomes ready. Snapshot process every `snapshot_every_min`; emit all required milestone events. Return metrics and timeline. Include warm-up and evaluation-window logic from contract.

**H6–H12:** Add tests for capacity, deterministic outputs, correct denominator and 720-minute follow-up, boarding locks ED space, physician not locked during boarding, initial occupancy transitions, nonnegative counts, and stable seeded patients across scenarios. Integrate through C's wrapper.

**H12–H20:** Optimize if needed; add patient journey selection (e.g. one quickly admitted, one long boarder, one ED discharge) and expose events to UI via the frozen `patient_examples` field. Validate behavior at low vs high demand. Never hardcode results or simulate clinical deterioration.

## Required test cases

- Same seed/config → identical JSON-compatible result.
- Changing only bed turnover changes neither arrivals nor initial clinical attributes.
- With `ward_beds=1`, `initial_ward_occupied=1`, a boarded patient does not access bed before an actual turnover completion.
- Two ED spaces never host more than two patients; physician utilization never exceeds capacity.
- Every indicated admission in the measurement window has a full 12-hour observation, including those near its end.
- `ward_occupied + ward_turnover + ward_ready == ward_beds` at each snapshot.
- All times monotone per patient; no negative waits; inpatient bed cannot be double allocated.

## Handoff to C/B

Return the exact `SimulationResult` schema; no supplementary undocumented fields. Provide a reproducible command using `pytest`, a baseline output sample, and an explanation of which stochastic parameters are synthetic assumptions. All meaningful state for the UI must be represented in timeline/patient milestones. Do not ask B to infer resource occupancy from pictures.
