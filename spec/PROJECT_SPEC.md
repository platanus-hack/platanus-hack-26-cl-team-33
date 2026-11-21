# Canonical project specification: BedFlow Chile (v1.0)

## One-sentence product

An interactive **discrete-event hospital flow simulator** that lets users stress-test ED staffing, inpatient bed capacity and bed turnover to learn which operational bottleneck prevents timely admissions.

## Track and problem

Hackathon track: **Simulations**. Run a hypothetical hospital to answer **"What if we changed a policy?"**; do not manage real patients or read/control a hospital in real time.

Focus on Chile's 2026 MINSAL CG-SRA 58 *target* (at least 85% of eligible inpatient admissions within 12 hours after a hospitalization indication). This is a target, **not a measured achievement for our fictional hospital**. Do not claim clinical accuracy, actual saved lives or verified savings.

**Research question:** Which feasible operational changes reduce emergency-to-inpatient admission delays, and when does the binding constraint move between ED clinicians, ED bays, and ward beds?

## What is and is not being built

IN: one fictional Chilean emergency department; Poisson patient arrivals; physician service; 8 ED treatment bays; admission indications; 24 inpatient beds; background ward occupancy; length of stay; bed turnover; boarding in ED bays; event-driven engine; counterfactual scenarios; uncertainty over repeated runs; visualization.

OUT: medical diagnosis, individualized triage decisions, hidden disease progression, undertriage, re-triage, mortality, clinical advice, ambulance dispatch, multi-hospital routing, real-time hospital operations, LLM medical recommendations.

## Fixed MVP model

All incoming synthetic patients follow this flow:

1. **Arrival:** Exogenously generated arrivals join a FIFO ED bay queue.
2. **ED bay:** A patient acquires a treatment bay. The patient occupies it while waiting for a physician.
3. **Physician care:** A physician is requested; after a sampled treatment time the physician is released.
4. **Disposition:** A pre-generated Boolean determines whether the patient needs admission (not a medical classifier).
5. **Discharge:** Non-admitted patients leave and release their ED bay.
6. **Boarding:** Admitted patients have `ADMISSION_INDICATED` recorded at completion of physician service. They wait for a ward bed **while still holding the ED bay** (physician already released).
7. **Ward admission:** When a ready inpatient bed becomes available, the patient releases the ED bay and occupies the ward bed for a pre-generated length of stay.
8. **Discharge + turnover:** Following ward discharge, the bed is temporarily unavailable for bed-turnover time, then becomes ready again.

Initially occupied ward beds are represented by synthetic existing patients, each with a sampled **residual** stay. Never let beds spontaneously become free without a discharge/turnover event.

Use `simpy.Resource` for ED bays and physicians and a similarly capacity-enforced ward-bed model. Single queue class, no triage priority; this is an **operational** simulator, not a triage simulator.

## Canonical base config (fictional, uncalibrated)

```json
{
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
```

These numbers are test inputs, not verified Chilean hospital parameters. Use hours/minutes exactly as named. Arrivals continue during **follow-up** to avoid artificially emptying queues near the evaluation end.

Stochastic assumptions: nonhomogeneous not required for MVP. Homogeneous Poisson arrivals at constant hourly rate; physician duration Gamma(shape=3, scale=mean/3); inpatient LOS lognormal with **mean** `mean_inpatient_los_h` and coefficient of variation 0.7; synthetic initial residual stay exponential with mean `mean_inpatient_los_h`. Assign admission disposition and both service durations **before** simulation, using per-patient seeded RNG. Do not draw shared randomness in policy-dependent code paths.

## Exact scenarios

- `baseline`: config unchanged.
- `more_physicians`: `physicians: 6` (from 4).
- `faster_turnover`: `bed_turnover_min: 30` (from 120).
- `more_ward_beds`: `ward_beds: 28` (from 24); keep **the same initial_ward_occupied count**, representing newly available staffed beds.

No additional MVP policies. This four-scenario set is the same in the UI, HTTP, experiment runner and demo.

## Primary evaluation metric

`admitted_within_12h_pct` is **100 × (eligible hospitalization indications that reach a ward bed within 720 minutes) / (all eligible indications)**, where eligible indications occurred during `[warmup_h*60, (warmup_h+measurement_h)*60)`.

Count indications unresolved 720 min later as failures. Simulate through a **12-hour follow-up** after the measurement window so every counted indication has a full 12-hour outcome window. This makes the percentage estimable without silently dropping late patients.

Other metrics: capped waiting time (min(wait until ward bed, 720); 720 for not admitted within 12h), occupancy during evaluation period, largest boarding queue and ED arrivals during evaluation. Use names and definitions in `CONTRACTS.md`.

Note: the indication-time cohort can vary slightly across policies, even with the same exogenous patient arrivals. Document it; common-random-number comparisons still improve control but do not guarantee identical indication cohorts.

## Scientific integrity and demo rules

- Every outcome must come from event simulation, never from formula-based fabricated improvements.
- Document calibration limitations and sensitivity to assumed input values.
- Never label the target 85% as the fictional hospital's baseline result.
- Use data from Chilean public sources only as later calibration/anchoring, not as a required dependency for the 36h MVP.
- If comparisons are statistically uncertain, say so. Do not imply the model can prescribe real clinical operational changes.
- No new simulation or UI features once the final feature freeze begins.
