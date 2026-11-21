# Model limitations — BedFlow Chile (synthetic model)

BedFlow Chile is a **fictional, uncalibrated, synthetic** discrete-event model of one emergency department and its inpatient beds. It is **not validated for real hospital decisions** and makes no clinical claims.

## What the numbers mean
- **MINSAL 85% within 12 h is a policy target (reference only).** It is never a result of this model and is never our baseline.
- All base parameters (3 arrivals/h, 4 physicians, 8 ED bays, 24 ward beds with 21 initially occupied, 20% admission probability, 35 min mean physician service, 36 h mean length of stay, 120 min bed turnover) are **test inputs**, not Chilean hospital data.
- Results come only from simulated events. Hypothetical interventions (6 physicians, 30 min turnover, 28 ward beds) show what *this model* does under *these assumptions*.

## Structural simplifications
- One hospital, one patient class, FIFO queue, no triage priority, no diagnoses, deterioration, mortality or re-triage.
- Homogeneous Poisson arrivals (no daily/weekly pattern); Gamma physician service; lognormal inpatient stay (CV 0.7); exponential residual stay for initial occupants.
- The 12 h outcome window follows each indication; indications unresolved at 720 min count as failures, and arrivals continue during follow-up.

## Statistics
- Compare runs every scenario on the **same seeds** (common random numbers). Per-seed values are aggregated by `bedflow.experiments.compare`.
- 95% intervals are **approximate**: mean ± 1.96·s/√n with sample standard deviation (ddof=1). They are normal approximations and are unreliable for very small n; use n ≥ 5 (20 for benchmarks).
- Paired difference = per-seed (variant − baseline) of `admitted_within_12h_pct`, in **percentage points**, not relative change.
- Seeds with no eligible admissions have a null 12 h percentage; they are dropped for that metric (paired deltas use only seeds where both runs are non-null). If no valid seed remains the API returns HTTP 422.
- The cohort of hospitalization indications can differ slightly across policies even with identical arrivals; common random numbers reduce but do not remove variance.
- If an interval straddles zero, the model shows **no statistically clear effect**; that is a finding about the assumptions, not a failure.

## Sensitivity
Results depend strongly on the assumed arrival rate, length of stay, admission probability and initial ward occupancy. Calibration with local data (e.g. a pilot with real ED/ward timestamps) would be required before any operational use.
